"""Suggest ground stitching vias: places where the top and bottom ground pours
overlap with room for a via, spread along the board, at least one per separate
piece of the top pour.

Run as:  python -m hardware.design.stitch

A design-time helper, called by autoroute.py, which saves the result in
routes.json. Run on its own it just prints the positions.
"""
import math

import pcbnew

from hardware.design import gen_pcb, layout

VIA_ROOM = 0.3 + 0.15   # via radius plus margin, mm: the whole disc must sit in both pours
SPACING = 5.0           # aim for a via about this often along each piece of pour, mm
STEP = 0.25             # search grid, mm


def _disc_inside(poly, outline_index, x, y, radius) -> bool:
    points = [(x, y)] + [(x + radius * math.cos(a), y + radius * math.sin(a))
                         for a in (i * math.pi / 6 for i in range(12))]
    return all(poly.Contains(pcbnew.VECTOR2I(pcbnew.FromMM(px), pcbnew.FromMM(py)), outline_index)
               for px, py in points)


def suggest() -> list[tuple[float, float]]:
    board = pcbnew.LoadBoard(str(gen_pcb.PCB_PATH))
    ox, oy = layout.ORIGIN
    fills = {}
    for zone in board.Zones():
        if not zone.GetIsRuleArea():
            for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
                if zone.IsOnLayer(layer):
                    fills[layer] = zone.GetFilledPolysList(layer)
    top, bottom = fills[pcbnew.F_Cu], fills[pcbnew.B_Cu]

    # stay off every pad (no via-in-pad), out from behind the programming footprint,
    # and a hole's width away from every existing via
    blocked = [fp.GetBoundingBox(False) for fp in board.GetFootprints() if fp.GetReference() == "J3"]
    for box in blocked:
        box.Inflate(pcbnew.FromMM(0.5))   # the whole via must stay outside, not just its centre
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            box = t.GetBoundingBox()
            box.Inflate(pcbnew.FromMM(0.9))
            blocked.append(box)
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            box = pad.GetBoundingBox()
            box.Inflate(pcbnew.FromMM(0.45))
            blocked.append(box)

    lo, hi = (ox + v for v in layout.STITCH_X_RANGE)

    def free(x, y):
        p = pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
        return lo <= x <= hi and not any(b.Contains(p) for b in blocked)

    chosen = []
    for i in range(top.OutlineCount()):
        box = top.Outline(i).BBox()
        x0, x1 = pcbnew.ToMM(box.GetLeft()), pcbnew.ToMM(box.GetRight())
        y0, y1 = pcbnew.ToMM(box.GetTop()), pcbnew.ToMM(box.GetBottom())
        candidates = []
        x = x0
        while x <= x1:
            y = y0
            while y <= y1:
                if free(x, y) and _disc_inside(top, i, x, y, VIA_ROOM) and _disc_inside(bottom, -1, x, y, VIA_ROOM):
                    depth = max(r for r in (VIA_ROOM, 0.7, 1.0, 1.4) if _disc_inside(top, i, x, y, r))
                    candidates.append((depth, x, y))
                y += STEP
            x += STEP
        if not candidates:
            print(f"# top pour piece {i}: no room for a via")
            continue
        candidates.sort(reverse=True)
        mine = []
        for _, x, y in candidates:
            if all(math.hypot(x - cx, y - cy) >= SPACING for cx, cy in mine):
                mine.append((x, y))
        chosen += mine
        print(f"# top pour piece {i}: {len(mine)} via(s)")
    return [(round(x - ox, 2), round(y - oy, 2)) for x, y in chosen]


if __name__ == "__main__":
    for x, y in sorted(suggest()):
        print(x, y)


# --- ground pads the pour cannot reach ---------------------------------------------

def _seg_dist(ax, ay, bx, by, px, py) -> float:
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _rect_dist(box, px, py) -> float:
    dx = max(box[0] - px, 0, px - box[2])
    dy = max(box[1] - py, 0, py - box[3])
    return math.hypot(dx, dy)


def rescue(pads: list[tuple[str, str]], reach: float = 3.0) -> None:
    """For ground pads stranded on a scrap of top pour, print the nearest place a via
    to the bottom pour fits, and the short track that reaches it."""
    board = pcbnew.LoadBoard(str(gen_pcb.PCB_PATH))
    mm = pcbnew.ToMM
    gnd = gen_pcb.net_name("GND")
    r_via, clr, half = layout.VIA_DIAMETER / 2, layout.CLEARANCE + 0.03, layout.TRACK_POWER / 2
    segs, discs, rects, gnd_rects, holes = [], [], [], [], []
    for t in board.GetTracks():
        if t.GetNetname() == gnd:
            continue
        if t.GetClass() == "PCB_VIA":
            discs.append((mm(t.GetPosition().x), mm(t.GetPosition().y), r_via))
        else:
            segs.append((mm(t.GetStart().x), mm(t.GetStart().y), mm(t.GetEnd().x), mm(t.GetEnd().y), mm(t.GetWidth()) / 2))
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            b = pad.GetBoundingBox()
            box = (mm(b.GetLeft()), mm(b.GetTop()), mm(b.GetRight()), mm(b.GetBottom()))
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                holes.append(box)
            elif pad.GetNetname() == gnd:
                gnd_rects.append(box)
            else:
                rects.append(box)   # a via goes through both layers, so pads on either side count
    j3 = board.FindFootprintByReference("J3").GetBoundingBox(False)
    j3 = (mm(j3.GetLeft()), mm(j3.GetTop()), mm(j3.GetRight()), mm(j3.GetBottom()))
    ox, oy = layout.ORIGIN

    def copper_gap(x, y):   # distance from a point to the nearest copper of another net
        d = [_seg_dist(ax, ay, bx, by, x, y) - w for ax, ay, bx, by, w in segs]
        d += [math.hypot(x - cx, y - cy) - r for cx, cy, r in discs]
        d += [_rect_dist(b, x, y) for b in rects]
        d += [_rect_dist(b, x, y) - 0.1 for b in holes]
        return min(d)

    def via_ok(x, y):
        return (copper_gap(x, y) >= r_via + clr and _rect_dist(j3, x, y) > r_via
                and all(_rect_dist(b, x, y) >= r_via + 0.1 for b in gnd_rects)
                and layout.ORIGIN[0] + 0.9 <= x <= layout.ORIGIN[0] + layout.LENGTH - 0.9
                and layout.ORIGIN[1] + 0.9 <= y <= layout.ORIGIN[1] + layout.WIDTH - 0.9)

    def track_ok(x0, y0, x1, y1):
        n = max(2, int(math.hypot(x1 - x0, y1 - y0) / 0.05))
        return all(copper_gap(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n) >= half + clr for i in range(n + 1))

    for ref, number in pads:
        pad = next(p for p in board.FindFootprintByReference(ref).Pads() if p.GetNumber() == number)
        px, py = mm(pad.GetPosition().x), mm(pad.GetPosition().y)
        best = None
        steps = int(reach / 0.05)
        for i in range(-steps, steps + 1):
            for j in range(-steps, steps + 1):
                x, y = px + i * 0.05, py + j * 0.05
                d = math.hypot(x - px, y - py)
                if d <= reach and (best is None or d < best[0]) and via_ok(x, y) and track_ok(px, py, x, y):
                    best = (d, x, y)
        if best is None:
            print(f"# {ref}.{number}: nothing within {reach} mm")
        else:
            _, x, y = best
            print(f'    ("GND", "F.Cu", TRACK_POWER, [({px - ox:.2f}, {py - oy:.2f}), ({x - ox:.2f}, {y - oy:.2f})]),'
                  f'   # {ref}.{number} -> via ("GND", {x - ox:.2f}, {y - oy:.2f})')
