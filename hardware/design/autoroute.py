"""Route the board's signal and power nets with Freerouting, and save the result.

Run as:  python -m hardware.design.autoroute /path/to/freerouting-cli

This is a design-time tool, not part of regenerating the board. It:
  1. builds the placed but unrouted board (no ground pour),
  2. exports it for the router,
  3. runs Freerouting,
  4. reads the routed tracks and vias back, sets each track to its net class
     width, and writes hardware/design/routes.json.

Ground is routed like any other net, so every ground pad has a drawn
connection; gen_pcb then adds the ground pours on both layers over the top.
(Leaving ground to the pours alone stranded three pads on scraps of pour.)

gen_pcb then replays routes.json, so the committed board does not depend on the
router being available or giving the same answer twice.

Freerouting 2.5.0 command-line build:
https://github.com/freerouting/freerouting/releases/tag/v2.5.0
"""
import json
import pathlib
import re
import subprocess
import sys
import tempfile

import pcbnew

from hardware.design import gen_pcb, layout

ROUTES = pathlib.Path(__file__).with_name("routes.json")
UNROUTED_NETS = ()   # nets to hide from the router; none at present


def _drop_nets(dsn_text: str, names) -> str:
    """Remove nets from a Specctra design so the router treats their pads as plain
    obstacles."""
    for name in names:
        quoted = rf'"?{re.escape(name)}"?'
        dsn_text, n = re.subn(rf'\(net {quoted}\s*\(pins[^)]*\)\s*\)', "", dsn_text)
        if n != 1:
            raise RuntimeError(f"expected exactly one (net {name} ...) in the DSN, found {n}")

        def strip_from_class(match):
            return re.sub(rf'(?<![\w+\-]){quoted}(?![\w+\-])', "", match.group(0), count=1)

        dsn_text = re.sub(r'\(class [^()]*\(', strip_from_class, dsn_text)
    return dsn_text


def _extract(board) -> dict:
    ox, oy = layout.ORIGIN
    rel = lambda p: [round(pcbnew.ToMM(p.x) - ox, 4), round(pcbnew.ToMM(p.y) - oy, 4)]  # noqa: E731
    tracks, vias = [], []
    for t in board.GetTracks():
        if t.IsLocked():
            continue   # hand-routed wiring from layout.FIXED_TRACKS, not the router's
        if t.GetClass() == "PCB_VIA":
            x, y = rel(t.GetPosition())
            vias.append({"net": t.GetNetname(), "x": x, "y": y})
        elif t.GetClass() == "PCB_TRACK":
            # the router's optimiser necks some segments down; hold every track at its
            # net class width and let KiCad's DRC judge the clearances
            power = t.GetNetname() in {gen_pcb.net_name(n) for n in layout.POWER_NETS}
            tracks.append({"net": t.GetNetname(), "layer": pcbnew.LayerName(t.GetLayer()),
                           "width": layout.TRACK_POWER if power else layout.TRACK_SIGNAL,
                           "points": [rel(t.GetStart()), rel(t.GetEnd())]})
    # The router sometimes leaves a via with nothing on the far side. Keep a via
    # only if a bottom-layer track or pad meets it (ground vias join the pour).
    gnd = gen_pcb.net_name("GND")
    bottom_points = [p for t in tracks if t["layer"] == "B.Cu" for p in t["points"]]
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.IsOnLayer(pcbnew.B_Cu):
                bottom_points.append(rel(pad.GetPosition()))

    def lands(v):
        return v["net"] == gnd or any(abs(v["x"] - x) < 0.02 and abs(v["y"] - y) < 0.02 for x, y in bottom_points)

    vias = [v for v in vias if lands(v)]
    key = lambda d: json.dumps(d, sort_keys=True)  # noqa: E731
    return {"tracks": sorted(tracks, key=key), "vias": sorted(vias, key=key)}


def main(router: str, passes: int = 40) -> None:
    board = gen_pcb.build(routed=False)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        dsn, ses = tmp / "dongle.dsn", tmp / "dongle.ses"
        if not pcbnew.ExportSpecctraDSN(board, str(dsn)):
            raise RuntimeError("KiCad could not export the board for the router")
        dsn.write_text(_drop_nets(dsn.read_text(), UNROUTED_NETS))
        subprocess.run([router, "-de", str(dsn), "-do", str(ses), "-mp", str(passes)], check=True)
        if not ses.exists():
            raise RuntimeError("the router produced no session file")
        if not pcbnew.ImportSpecctraSES(board, str(ses)):
            raise RuntimeError("KiCad could not read the router's result")
    routes = _extract(board)
    routes["stitch"] = []
    ROUTES.write_text(json.dumps(routes, indent=1) + "\n")
    print(f"wrote {ROUTES.name}: {len(routes['tracks'])} track segments, {len(routes['vias'])} vias")

    # Now that the tracks are fixed, build the board with its pours and choose the
    # ground stitching vias. A fresh interpreter, so layout re-reads routes.json.
    subprocess.run([sys.executable, "-W", "ignore", "-m", "hardware.design.gen_pcb"], check=True)
    found = subprocess.run([sys.executable, "-W", "ignore", "-m", "hardware.design.stitch"],
                           check=True, capture_output=True, text=True).stdout
    routes["stitch"] = sorted([float(v) for v in line.split()] for line in found.splitlines()
                              if line and not line.startswith("#"))
    ROUTES.write_text(json.dumps(routes, indent=1) + "\n")
    subprocess.run([sys.executable, "-W", "ignore", "-m", "hardware.design.gen_pcb"], check=True)
    print(f"added {len(routes['stitch'])} ground stitching vias")


if __name__ == "__main__":
    main(sys.argv[1], *(int(a) for a in sys.argv[2:3]))
