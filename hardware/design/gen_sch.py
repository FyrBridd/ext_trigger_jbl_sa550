"""Generate the KiCad schematic from circuit.py.

Run as:  python -m hardware.design.gen_sch

The sheet is drawn the conventional way: signal flow left to right, parts
joined by wires, ground and 3.3 V shown with power symbols. Each signal net
carries its name once, on a wire.

The drawing below is hand-placed: every part and wire has a position on a
2.54 mm grid (positions are written in grid units, column then row). The
drawing does not decide what is connected to what. circuit.py does, and the
tests compare KiCad's own netlist of this sheet with circuit.py, so a wire in
the wrong place fails a test, it does not change the board.
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

G = 2.54   # schematic grid, mm

# Nets drawn with power symbols; every other net is drawn as wires with one label.
POWER_SYMBOLS = {"GND": "power:GND", "+3V3": "power:+3V3"}

# Pin positions inside each symbol (mm, x right, y up), from KiCad's libraries.
# Two-pin symbols only: these are the ones whose rotation is chosen here.
_TWO_PIN = {
    "Device:R": {"1": (0, 3.81), "2": (0, -3.81)},
    "Device:C": {"1": (0, 3.81), "2": (0, -3.81)},
    "Device:D_Schottky": {"1": (-3.81, 0), "2": (3.81, 0)},
    "Device:D_TVS": {"1": (-3.81, 0), "2": (3.81, 0)},
    "Device:LED": {"1": (-3.81, 0), "2": (3.81, 0)},
}


def symbol_uuid(ref: str) -> str:
    """The schematic symbol's UUID for a reference; the board links footprints by it."""
    return str(uuid.uuid5(_UUID_NAMESPACE, ref))


def _transform(px: float, py: float, rotation: float, mirror: bool) -> tuple[float, float]:
    """A point in symbol coordinates (y up) as an offset on the sheet (y down).
    KiCad mirrors first, then rotates anticlockwise."""
    vx, vy = (-px if mirror else px), -py
    for _ in range(int(rotation // 90) % 4):
        vx, vy = vy, -vx
    return vx, vy


class Sheet:
    """Builds the drawing. Positions are in grid units (column, row)."""

    def __init__(self):
        self.sch = ksa.create_schematic(NAME)
        self.parts = {}          # ref -> (component, mirror)
        self.segments = []       # ((x1, y1), (x2, y2)) in grid units
        self.text_at = {}        # ref -> {field: (x mm, y mm, justify or None)}
        self.mirrored = set()
        self.symbol_pins = set()  # where power symbols and flags attach (grid units)
        self.unnamed = set()      # power symbols drawn without their net name (no room for it)
        self._power_count = 0

    # --- parts -----------------------------------------------------------------

    def place(self, ref, col, row, rotation=0, mirror=False, text=None):
        part = c.PARTS[ref]
        extra = {"LCSC": part.lcsc} if part.lcsc else {}
        comp = self.sch.components.add(part.symbol, reference=ref, value=part.value,
                                       position=(col * G, row * G), rotation=rotation,
                                       footprint=part.footprint, component_uuid=symbol_uuid(ref), **extra)
        comp.in_bom = part.assemble   # wire pads, test pads and the programming footprint are not parts
        self.parts[ref] = (comp, mirror)
        if mirror:
            self.mirrored.add(ref)
        if text:
            self.text_at[ref] = {name: (col * G + dx, row * G + dy, justify) for name, (dx, dy, justify) in text.items()}
        return comp

    def pin(self, ref, number) -> tuple[float, float]:
        """Where a pin's connection point is, in grid units."""
        comp, mirror = self.parts[ref]
        pin = next(p for p in comp.pins if p.number == number)
        dx, dy = _transform(pin.position.x, pin.position.y, comp.rotation, mirror)
        return (round((comp.position.x + dx) / G, 3), round((comp.position.y + dy) / G, 3))

    def two_pin(self, ref, col, row, first, direction):
        """A two-pin part centred at (col, row), turned so that going from pin `first`
        to the other pin is `direction` ("right" or "down")."""
        pins = _TWO_PIN[c.PARTS[ref].symbol]
        other = "2" if first == "1" else "1"
        want = (1, 0) if direction == "right" else (0, 1)
        for rotation in (0, 90, 180, 270):
            ax, ay = _transform(*pins[first], rotation, False)
            bx, by = _transform(*pins[other], rotation, False)
            dx, dy = bx - ax, by - ay
            if (dx > 0, dy > 0) == (want[0] > 0, want[1] > 0) and abs(dx * want[1]) < 1e-6 and abs(dy * want[0]) < 1e-6:
                break
        if direction == "right":
            text = {"Reference": (0, -2.4, None), "Value": (0, 3.0, None), "LCSC": (0, 4.9, None)}
        else:
            text = {"Reference": (2.2, -1.6, "left"), "Value": (2.2, 0.3, "left"), "LCSC": (2.2, 2.2, "left")}
        self.place(ref, col, row, rotation, text=text)
        return self.pin(ref, first), self.pin(ref, other)

    def test_pad(self, ref, col, row, side="up"):
        """A test pad with its connection point at (col, row) and its circle above
        it ("up") or to the right ("right")."""
        if side == "up":
            self.place(ref, col, row, 0, text={"Reference": (1.6, -2.6, "left"), "Value": (1.6, -0.9, "left")})
        else:
            self.place(ref, col, row, 270, text={"Reference": (3.6, -0.2, "left"), "Value": (8.4, -0.2, "left")})

    def _power(self, net, col, row, named=True):
        self._power_count += 1
        ref = f"#PWR{self._power_count:02d}"
        if not named:
            self.unnamed.add(ref)
        self.sch.components.add(POWER_SYMBOLS[net], reference=ref, value=net,
                                position=(col * G, row * G), component_uuid=symbol_uuid(ref))
        self.symbol_pins.add((col, row))

    def gnd(self, col, row, named=True):
        self._power("GND", col, row, named)

    def vcc(self, col, row):
        self._power("+3V3", col, row)

    def flag(self, ref, col, row):
        """PWR_FLAG: tells KiCad's rule check that this net has a source."""
        self.sch.components.add("power:PWR_FLAG", reference=ref, value="PWR_FLAG",
                                position=(col * G, row * G), component_uuid=symbol_uuid(ref))
        self.symbol_pins.add((col, row))

    # --- wires -----------------------------------------------------------------

    def wire(self, *points):
        """A wire through the given points; each leg must be horizontal or vertical."""
        for a, b in zip(points, points[1:]):
            if abs(a[0] - b[0]) > 1e-6 and abs(a[1] - b[1]) > 1e-6:
                raise ValueError(f"wire leg {a} -> {b} is neither horizontal nor vertical")
            if a != b:
                self.segments.append((a, b))

    def label(self, net, col, row):
        self.sch.add_label(net, position=(col * G, row * G), rotation=0)

    def note(self, text, col, row, size=1.27, bold=False):
        self.sch.add_text(text, position=(col * G, row * G), size=size, bold=bold)

    def no_connect(self, ref, number):
        x, y = self.pin(ref, number)
        self.sch.no_connects.add((x * G, y * G))

    def finish(self):
        """Break wires wherever another wire ends or a pin sits on them, so that
        every meeting point is a wire end, then draw them with junction dots."""
        pin_points = set(self.symbol_pins)
        for ref, (comp, _) in self.parts.items():
            pin_points |= {self.pin(ref, p.number) for p in comp.pins}
        nodes = pin_points | {p for seg in self.segments for p in seg}

        def inside(p, a, b):
            (x, y), (x1, y1), (x2, y2) = p, a, b
            if abs(x1 - x2) < 1e-6:
                return abs(x - x1) < 1e-6 and min(y1, y2) + 1e-6 < y < max(y1, y2) - 1e-6
            return abs(y - y1) < 1e-6 and min(x1, x2) + 1e-6 < x < max(x1, x2) - 1e-6

        pieces = set()
        for a, b in self.segments:
            cuts = sorted([p for p in nodes if inside(p, a, b)] + [a, b])
            for p, q in zip(cuts, cuts[1:]):
                pieces.add((p, q))
        degree = {}
        for a, b in pieces:
            self.sch.add_wire((a[0] * G, a[1] * G), (b[0] * G, b[1] * G))
            for p in (a, b):
                degree[p] = degree.get(p, 0) + 1
        for p in pin_points:                 # a pin on a wire counts as one more connection
            if p in degree:
                degree[p] += 1
        for p, n in degree.items():
            if n >= 3:
                self.sch.junctions.add((p[0] * G, p[1] * G))


def _draw(s: Sheet) -> None:
    ic_text = {
        "U1": {"Reference": (-5.08, -6.6, "left"), "Value": (0.0, -6.6, "left"), "LCSC": (3.0, 5.6, "left")},
        "U2": {"Reference": (-12.7, -14.4, "left"), "Value": (2.0, -14.4, "left"), "LCSC": (2.0, 14.4, "left")},
        "U3": {"Reference": (-15.24, -29.6, "left"), "Value": (3.0, -29.6, "left"), "LCSC": (3.0, 29.6, "left")},
    }
    P = s.pin

    # ---- Trigger input and 3.3 V supply: current flows left to right along row 30 ----
    s.note("TRIGGER INPUT AND 3.3 V SUPPLY", 10, 21, size=2.0, bold=True)
    s.note("J1: the two wires from the WiiM trigger plug.", 10, 23.5)
    s.note("Pad 1 = +12 V (plug tip), pad 2 = ground (sleeve).", 10, 24.7)
    s.place("J1", 14, 30, mirror=True, text={"Reference": (-1.5, -3.6, None), "Value": (-1.5, 5.6, None)})
    r1_in, r1_out = s.two_pin("R1", 24, 30, "1", "right")
    s.wire(P("J1", "1"), r1_in)
    s.label("TRIG_IN", 17, 30)
    d1_a, d1_k = s.two_pin("D1", 38, 30, "2", "right")        # anode in, cathode out
    s.wire(r1_out, d1_a)
    s.label("TRIG_R", 26, 30)
    d2_top, d2_bottom = s.two_pin("D2", 31, 35, "1", "down")  # surge clamp to ground
    s.wire((31, 30), d2_top)
    s.wire(d2_bottom, (31, 38))
    s.gnd(31, 38)
    s.place("U1", 60, 31, text=ic_text["U1"])
    s.wire(d1_k, P("U1", "2"))
    s.test_pad("TP1", 43, 30)
    c1_top, c1_bottom = s.two_pin("C1", 47, 35, "1", "down")
    s.wire((47, 30), c1_top)
    s.wire(c1_bottom, (47, 38))
    s.gnd(47, 38)
    s.flag("#FLG02", 51, 30)
    s.label("VIN", 52, 30)
    s.wire(P("U1", "1"), (60, 38))
    s.gnd(60, 38)
    s.wire(P("U1", "3"), (74, 30), (74, 28))
    s.vcc(74, 28)
    s.test_pad("TP2", 66, 30)
    c2_top, c2_bottom = s.two_pin("C2", 70, 35, "1", "down")
    s.wire((70, 30), c2_top)
    s.wire(c2_bottom, (70, 38))
    s.gnd(70, 38)
    d4_k, d4_a = s.two_pin("D4", 21, 35, "1", "down")         # cathode to the return wire
    s.wire(P("J1", "2"), (21, 31), d4_k)
    s.label("TRIG_RTN", 16.5, 31)
    s.wire(d4_a, (21, 38))
    s.gnd(21, 38)
    s.note("D1 and D4 block if the two trigger wires are swapped.", 10, 25.9)
    # ground reference: its test pad, and the flag KiCad's rule check wants
    s.wire((16, 44), (24, 44))
    s.flag("#FLG01", 16, 44)
    s.test_pad("TP3", 24, 44)
    s.wire((20, 44), (20, 46))
    s.gnd(20, 46)

    # ---- Controller, status LED and programming pads ----
    s.note("CONTROLLER, STATUS LED AND PROGRAMMING PADS", 84, 36, size=2.0, bold=True)
    s.note("J3: Tag-Connect TC2030-MCP-NL footprint. No part is fitted.", 84, 38.5)
    s.note("Pads 1, 5 and 6 are left unconnected on purpose.", 84, 39.7)
    s.place("U2", 96, 60, text=ic_text["U2"])
    s.wire(P("U2", "1"), (96, 52))
    s.vcc(96, 52)
    s.wire(P("U2", "8"), (96, 68))
    s.gnd(96, 68)
    c3_top, c3_bottom = s.two_pin("C3", 84, 59.5, "1", "down")   # supply decoupling for U2
    s.wire(c3_top, (84, 57))
    s.vcc(84, 57)
    s.wire(c3_bottom, (84, 62))
    s.gnd(84, 62)
    s.note("C3: decoupling for U2", 72, 56)

    s.place("J3", 100, 44, mirror=True, text={"Reference": (-1.5, -9.0, None), "Value": (-1.5, 10.6, None)})
    s.wire(P("J3", "4"), (106, 45), (106, 57), P("U2", "6"))
    s.label("UPDI", 102.5, 45)
    s.test_pad("TP6", 106, 51, side="right")
    s.wire(P("J3", "2"), (108, 43), (108, 41))
    s.vcc(108, 41)
    s.wire(P("J3", "3"), (111, 44), (111, 46))
    s.gnd(111, 46)

    s.wire(P("U2", "4"), (108, 58))
    s.label("DBG", 102.5, 58)
    s.test_pad("TP7", 108, 58, side="right")
    s.wire(P("U2", "5"), (114, 59))
    s.label("SPARE", 102.5, 59)
    s.test_pad("TP8", 114, 59, side="right")

    r2_in, r2_out = s.two_pin("R2", 126, 60, "1", "right")
    s.wire(P("U2", "7"), r2_in)
    s.label("LED_DRV", 102.5, 60)
    d3_a, d3_k = s.two_pin("D3", 133, 60, "2", "right")       # anode from the resistor
    s.wire(r2_out, d3_a)
    s.label("LED_A", 127.8, 60)
    s.wire(d3_k, (138, 60), (138, 62))
    s.gnd(138, 62)

    # ---- RS232 driver ----
    s.note("RS232 DRIVER", 110, 67.5, size=2.0, bold=True)
    s.place("U3", 130, 80, text=ic_text["U3"])
    s.wire(P("U3", "16"), (130, 66))
    s.vcc(130, 66)
    s.wire(P("U3", "15"), (130, 94))
    s.gnd(130, 94)
    c8_top, c8_bottom = s.two_pin("C8", 146, 62.5, "1", "down")  # supply decoupling for U3
    s.wire(c8_top, (146, 60))
    s.vcc(146, 60)
    s.wire(c8_bottom, (146, 65))
    s.gnd(146, 65)
    s.note("C8: decoupling for U3", 149, 59.2)

    # logic side: controller to driver
    s.wire(P("U2", "2"), (104, 61), (104, 81), P("U3", "11"))
    s.label("UART_TX", 115, 81)
    s.test_pad("TP4", 108, 81)
    r3_top, r3_bottom = s.two_pin("R3", 112, 77.5, "1", "down")  # holds the line idle while U2 is in reset
    s.wire(r3_top, (112, 75))
    s.vcc(112, 75)
    s.wire(r3_bottom, (112, 81))
    s.wire(P("U2", "3"), (103, 62), (103, 85), P("U3", "12"))
    s.label("UART_RX", 115, 85)
    s.test_pad("TP5", 108, 85)
    s.wire(P("U3", "10"), (119, 83))                             # unused driver input tied off
    s.gnd(119, 83, named=False)

    # charge pump capacitors
    c4_top, c4_bottom = s.two_pin("C4", 118, 72.5, "1", "down")
    s.text_at["C4"] = {"Reference": (118 * G - 2.2, 72.5 * G - 1.6, "right"),
                       "Value": (118 * G - 2.2, 72.5 * G + 0.3, "right"),
                       "LCSC": (118 * G - 2.2, 72.5 * G + 2.2, "right")}
    s.wire(c4_top, P("U3", "1"))
    s.label("C1P", 118.5, 71)
    s.wire(c4_bottom, P("U3", "3"))
    s.label("C1M", 118.5, 74)
    c5_top, c5_bottom = s.two_pin("C5", 142, 72.5, "1", "down")
    s.wire(P("U3", "4"), c5_top)
    s.label("C2P", 138.5, 71)
    s.wire(P("U3", "5"), c5_bottom)
    s.label("C2M", 138.5, 74)
    c6_in, c6_out = s.two_pin("C6", 145.5, 76, "1", "right")
    s.wire(P("U3", "2"), c6_in)
    s.label("VPOS", 138.5, 76)
    s.wire(c6_out, (149, 76))
    s.gnd(149, 76)
    c7_in, c7_out = s.two_pin("C7", 145.5, 79, "2", "right")
    s.wire(P("U3", "6"), c7_in)
    s.label("VNEG", 138.5, 79)
    s.wire(c7_out, (149, 79))
    s.gnd(149, 79, named=False)
    s.text_at["C6"] = {"Reference": (145.5 * G, 76 * G - 2.2, None)}       # no room for three lines each:
    s.text_at["C7"] = {"Reference": (145.5 * G, 79 * G - 2.2, None)}       # both are 100n 50V, C14663
    s.note("C6, C7:", 151.5, 77.0)
    s.note("100n 50V", 151.5, 78.2)
    s.note("C14663", 151.5, 79.4)

    # RS232 side: driver to the amp
    s.place("J2", 156, 84, text={"Reference": (1.5, -6.2, None), "Value": (1.5, 6.2, None)})
    s.wire(P("U3", "14"), (151, 81), (151, 83), P("J2", "1"))
    s.label("RS232_TX", 139, 81)
    s.wire(P("U3", "13"), (148, 85), (148, 84), P("J2", "2"))
    s.label("RS232_RX", 139, 85)
    s.wire(P("J2", "3"), (152, 85), (152, 88))
    s.gnd(152, 88)
    s.note("J2: the three wires to the amp's DB9 plug.", 138, 91.5)
    s.note("Pad 1 = dongle output, to DB9 pin 2.", 138, 92.7)
    s.note("Pad 2 = dongle input, from DB9 pin 3.", 138, 93.9)
    s.note("Pad 3 = ground, DB9 pin 5.", 138, 95.1)

    for ref, number in c.NO_CONNECT:
        s.no_connect(ref, number)

    s.note("Wires that cross without a dot are not connected.   X marks a pin left unconnected on purpose.   "
           "TP1 to TP8 are bare test pads on the underside of the board.", 10, 108)


def build() -> Sheet:
    s = Sheet()
    s.sch.set_paper_size("A3")
    s.sch.set_title_block(title="WiiM trigger to JBL SA550 RS232 dongle", rev="r1",
                          company="Generated from hardware/design/circuit.py - do not edit by hand")
    _draw(s)
    s.finish()
    return s


def pin_positions() -> dict[str, dict[str, tuple[float, float]]]:
    """ref -> pin number -> (x, y) in mm, for every placed part (used by the tests)."""
    s = build()
    return {ref: {p.number: tuple(v * G for v in s.pin(ref, p.number)) for p in comp.pins}
            for ref, (comp, _) in s.parts.items()}


# --- finishing touches the library cannot express -----------------------------------

def _set_text(prop, x, y, angle, justify):
    """Move one of a symbol's text fields and set how it is justified."""
    for i, item in enumerate(prop):
        if isinstance(item, list) and item[0] == "at":
            prop[i] = ["at", f"{x:g}", f"{y:g}", f"{angle:g}"]
        if isinstance(item, list) and item[0] == "effects":
            item[:] = [e for e in item if not (isinstance(e, list) and e[0] == "justify")]
            if justify:
                item.append(["justify", justify])


def tidy(path, sheet: Sheet) -> None:
    """Mirror the connectors that face right, place each part's reference, value
    and LCSC number, and left-justify the notes. Works on the parsed file, so no
    KiCad syntax is typed by hand. Connectivity is checked through KiCad
    afterwards by the tests."""
    tree = kicad.parse_sexpr(pathlib.Path(path).read_text())
    for node in tree:
        if not isinstance(node, list):
            continue
        if node[0] == "text":
            effects = next(x for x in node if isinstance(x, list) and x[0] == "effects")
            effects[:] = [e for e in effects if not (isinstance(e, list) and e[0] == "justify")]
            effects.append(["justify", "left", "bottom"])
        if node[0] == "symbol":
            props = {x[1]: x for x in node if isinstance(x, list) and x[0] == "property"}
            ref = str(props["Reference"][2])
            at_index = next(i for i, x in enumerate(node) if isinstance(x, list) and x[0] == "at")
            rotation = float(node[at_index][3])
            if ref in sheet.mirrored:
                node.insert(at_index + 1, ["mirror", "y"])
            for name, (x, y, justify) in sheet.text_at.get(ref, {}).items():
                if name in props:
                    # KiCad draws a field at (its own angle + the symbol's), so a field
                    # on a part turned 90 degrees needs 90 to read horizontally.
                    _set_text(props[name], x, y, rotation % 180, justify)
            if ref in ("C6", "C7"):   # their value and part number are in a note beside them
                for name in ("Value", "LCSC"):
                    props[name].append(["hide", "yes"])
            if ref in sheet.unnamed:
                props["Value"].append(["hide", "yes"])
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
    sheet = build()
    out = PROJECT_DIR / f"{NAME}.kicad_sch"
    sheet.sch.save(str(out))
    tidy(out, sheet)


if __name__ == "__main__":
    main()
