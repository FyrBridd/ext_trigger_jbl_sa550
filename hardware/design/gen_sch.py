"""Generate the KiCad schematic from circuit.py.

Run as:  python -m hardware.design.gen_sch

Every pin gets a short wire stub ending in a net label; nets are joined by
name, not by long drawn wires. Two-pin parts lie horizontally so that each
reads as a row: "NET - part - NET". That makes the sheet a labelled parts
list that is easy to check against circuit.py, and keeps the generator
simple enough to trust. KiCad's own netlist export is compared with
circuit.py by the tests.
"""
import json
import pathlib
import uuid

import kicad_sch_api as ksa

from hardware.design import circuit as c
from hardware.design import kicad

PROJECT_DIR = pathlib.Path(__file__).resolve().parents[1] / "dongle"
NAME = "dongle"
_UUID_NAMESPACE = uuid.UUID("6f0f3c0e-5b1d-4a57-9c38-2f1d6a1b7e10")

G = 2.54     # schematic grid, mm
STUB = 2     # wire stub length, grid units


def symbol_uuid(ref: str) -> str:
    """The schematic symbol's UUID for a reference; the board links footprints by it."""
    return str(uuid.uuid5(_UUID_NAMESPACE, ref))


def _at(col: float, row: float) -> tuple[float, float]:
    return (round(col * G, 4), round(row * G, 4))


# Sheet is A4 landscape: 116 x 82 grid units; the title block takes the bottom right.
# Group titles: (column, row) of the text centre.
_GROUPS = {
    "Trigger input and 3.3 V supply": (18, 7),
    "Controller and status LED": (48, 7),
    "RS232 driver": (78, 7),
    "Connectors and test pads": (104, 7),
}
# ref: (column, row, rotation). Two-pin parts are rotated to lie horizontally.
_PLACE = {
    # supply, top to bottom in the order current flows
    "J1": (20, 15, 0), "R1": (18, 23, 90), "D2": (18, 30, 0), "D1": (18, 37, 0),
    "C1": (18, 44, 90), "U1": (18, 53, 0), "C2": (18, 63, 90),
    # controller
    "U2": (44, 24, 0), "C3": (48, 42, 90), "R3": (48, 49, 90), "R2": (48, 56, 90), "D3": (48, 63, 0),
    # RS232 driver
    "U3": (78, 24, 0), "C4": (78, 42, 90), "C5": (78, 47, 90), "C6": (78, 52, 90),
    "C7": (78, 57, 90), "C8": (78, 62, 90),
    # connectors and test pads
    "J3": (106, 17, 0), "J2": (106, 31, 0),
    **{f"TP{i}": (96 + 11 * ((i - 1) // 4), 40 + 5 * ((i - 1) % 4), 0) for i in range(1, 9)},
}
_FLAGS = {"#FLG01": ("GND", (10, 72)), "#FLG02": ("VIN", (24, 72))}

# Where each part's text goes, as (dx, dy, justify) in mm from the part's position.
_TWO_PIN_TEXT = {"Reference": (0, -2.4, None), "Value": (0, 3.0, None), "LCSC": (0, 5.0, None)}
_TEXT = {
    "U1": {"Reference": (-5.08, -6.2, "left"), "Value": (0, -6.2, "left"), "LCSC": (3.0, 6.2, "left")},
    "U2": {"Reference": (-12.7, -14.2, "left"), "Value": (2.0, -14.2, "left"), "LCSC": (2.0, 14.2, "left")},
    "U3": {"Reference": (-15.24, -27.0, "left"), "Value": (3.0, -27.0, "left"), "LCSC": (3.0, 27.0, "left")},
    "J1": {"Reference": (-2.0, -4.6, "left"), "Value": (3.0, -4.6, "left")},
    "J2": {"Reference": (-2.0, -5.9, "left"), "Value": (3.0, -5.9, "left")},
    "J3": {"Reference": (-2.0, -9.7, "left"), "Value": (3.0, -9.7, "left")},
    **{f"TP{i}": {"Reference": (-2.5, -0.5, "right"), "Value": (-2.5, -2.6, "right")} for i in range(1, 9)},
}


def _pin_xy(comp, pin_number) -> tuple[float, float]:
    """Sheet position of a pin's connection point.

    Worked out here, not with the library's get_component_pin_position: for a
    rotated symbol that function turns the wrong way and swaps a two-pin part's
    pins (caught by the netlist test). KiCad rotates symbols anticlockwise on
    the sheet; symbol coordinates have y up, the sheet has y down.
    """
    pin = next(p for p in comp.pins if p.number == pin_number)
    vx, vy = pin.position.x, -pin.position.y
    for _ in range(int(comp.rotation // 90) % 4):
        vx, vy = vy, -vx
    return (round(comp.position.x + vx, 4), round(comp.position.y + vy, 4))


def _outward(comp, pin_number):
    """Unit grid vector pointing away from the symbol body at a pin, or None if the
    pin sits on the symbol's origin (test points, power flags)."""
    x, y = _pin_xy(comp, pin_number)
    dx, dy = x - comp.position.x, y - comp.position.y
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return None
    pin = next(p for p in comp.pins if p.number == pin_number)
    horizontal = pin.rotation in (0.0, 180.0)
    if comp.rotation in (90.0, 270.0):
        horizontal = not horizontal
    if horizontal:
        return (1 if dx > 0 else -1, 0)
    return (0, 1 if dy > 0 else -1)


_LABEL_ROTATION = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}


def _connect(sch, ref, pin_number, net):
    """Give one pin a wire stub ending in a net label."""
    comp = sch.components.get(ref)
    here = _pin_xy(comp, pin_number)
    out = _outward(comp, pin_number)
    if out is None:
        out = (1, 0)   # test points and power flags: take the stub off to the right
    end = (round(here[0] + out[0] * STUB * G, 4), round(here[1] + out[1] * STUB * G, 4))
    sch.add_wire(here, end)
    sch.add_label(net, position=end, rotation=_LABEL_ROTATION[out])


def build() -> ksa.Schematic:
    sch = ksa.create_schematic(NAME)
    sch.set_paper_size("A4")
    sch.set_title_block(title="WiiM trigger to JBL SA550 RS232 dongle", rev="r1",
                        company="Generated from hardware/design/circuit.py - do not edit by hand")

    for title, (col, row) in _GROUPS.items():
        sch.add_text(title, position=_at(col, row), size=2.0, bold=True)
    sch.add_text("Pins with the same net label are connected. X marks a pin left unconnected on purpose.",
                 position=_at(36, 76), size=1.5)

    for ref, part in c.PARTS.items():
        col, row, rotation = _PLACE[ref]
        extra = {"LCSC": part.lcsc} if part.lcsc else {}
        comp = sch.components.add(part.symbol, reference=ref, value=part.value, position=_at(col, row),
                                  rotation=rotation, footprint=part.footprint,
                                  component_uuid=symbol_uuid(ref), **extra)
        comp.in_bom = part.assemble   # wire pads, test pads and the programming footprint are not parts

    # PWR_FLAG tells KiCad's rule check that a net is driven: GND and VIN come in
    # through a connector and a diode, which KiCad does not count as power sources.
    for ref, (net, place) in _FLAGS.items():
        sch.components.add("power:PWR_FLAG", reference=ref, value="PWR_FLAG", position=_at(*place),
                           component_uuid=symbol_uuid(ref))
        _connect(sch, ref, "1", net)

    for net, pins in c.NETS.items():
        for ref, pin in pins:
            _connect(sch, ref, pin, net)

    for ref, pin in c.NO_CONNECT:
        sch.no_connects.add(_pin_xy(sch.components.get(ref), pin))

    return sch


def _set_text(prop, x, y, angle, justify):
    """Move one of a symbol's text fields and set how it is justified."""
    for i, item in enumerate(prop):
        if isinstance(item, list) and item[0] == "at":
            prop[i] = ["at", f"{x:g}", f"{y:g}", f"{angle:g}"]
        if isinstance(item, list) and item[0] == "effects":
            item[:] = [e for e in item if not (isinstance(e, list) and e[0] == "justify")]
            if justify:
                item.append(["justify", justify])


def tidy(path) -> None:
    """Fix up what the schematic library cannot express: which way labels are
    justified, and where each part's reference, value and LCSC number are drawn.
    Works on the parsed file, so no KiCad syntax is typed by hand. Connectivity
    is untouched; the tests re-check it through KiCad afterwards."""
    tree = kicad.parse_sexpr(pathlib.Path(path).read_text())
    for node in tree:
        if not isinstance(node, list):
            continue
        if node[0] == "label":
            at = next(x for x in node if isinstance(x, list) and x[0] == "at")
            if float(at[3]) in (180.0, 270.0):   # pointing left or down: text ends at the wire
                effects = next(x for x in node if isinstance(x, list) and x[0] == "effects")
                effects[:] = [e for e in effects if not (isinstance(e, list) and e[0] == "justify")]
                effects.append(["justify", "right", "bottom"])
        if node[0] == "symbol":
            props = {x[1]: x for x in node if isinstance(x, list) and x[0] == "property"}
            ref = str(props["Reference"][2])
            at = next(x for x in node if isinstance(x, list) and x[0] == "at")
            x0, y0, rotation = float(at[1]), float(at[2]), float(at[3])
            two_pin = ref[0] in "RCD"
            wanted = _TWO_PIN_TEXT if two_pin else _TEXT.get(ref, {})
            for name, (dx, dy, justify) in wanted.items():
                if name in props:
                    # KiCad draws a field at (its own angle + the symbol's), so a field
                    # on a part turned 90 degrees needs 90 to read horizontally.
                    _set_text(props[name], x0 + dx, y0 + dy, rotation % 180, justify)
    pathlib.Path(path).write_text(kicad.dump_sexpr(tree) + "\n")


def write_project_files() -> None:
    PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    pro = PROJECT_DIR / f"{NAME}.kicad_pro"
    if not pro.exists():
        pro.write_text(json.dumps({"meta": {"filename": pro.name, "version": 3}}, indent=2) + "\n")
    (PROJECT_DIR / "fp-lib-table").write_text(
        '(fp_lib_table\n  (version 7)\n'
        '  (lib (name "dongle")(type "KiCad")(uri "${KIPRJMOD}/../lib/dongle.pretty")(options "")'
        '(descr "Project footprints, generated by hardware/design/gen_footprints.py"))\n)\n')


def main() -> None:
    write_project_files()
    sch = build()
    out = PROJECT_DIR / f"{NAME}.kicad_sch"
    sch.save(str(out))
    tidy(out)


if __name__ == "__main__":
    main()
