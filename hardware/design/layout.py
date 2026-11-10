"""Board layout data: outline, part placements, silkscreen text, tracks and vias.

Units are millimetres. The origin is the board's top-left corner; x runs along
the length (trigger end at x = 0, amplifier end at x = LENGTH), y across the
width. Rotations are KiCad's (degrees, anticlockwise seen from the top).
"""

LENGTH = 45.0
WIDTH = 13.0
OUTLINE = (WIDTH, LENGTH)
ORIGIN = (100.0, 100.0)   # where the board's top-left corner sits on the KiCad sheet

_MID = WIDTH / 2

# ref: (x, y, rotation)
PLACEMENTS: dict[str, tuple[float, float, float]] = {
    # trigger end: wire pads, strain-relief holes toward the board end
    "J1": (4.85, _MID - 1.27, 0),
    # supply
    "R1": (7.6, 3.4, 90),
    "D1": (11.2, 2.9, 180),
    "C1": (11.7, 5.6, 180),
    "D2": (9.6, 10.5, 0),
    "U1": (16.6, 4.3, 0),
    "C2": (16.6, 8.5, 0),
    # programming footprint: UPDI pad faces the controller
    "J3": (21.2, 6.6, 270),
    # controller, LED above it, decoupling and pull-up below it
    "U2": (26.2, 6.5, 90),
    "R2": (24.93, 1.8, 0),
    "D3": (27.98, 1.8, 180),
    "C3": (24.93, 11.2, 0),
    "R3": (27.98, 11.2, 180),
    # RS232 driver with its capacitors around it
    "C5": (30.12, 6.0, 90),
    "U3": (34.08, 6.5, 270),
    "C7": (32.73, 1.8, 0),
    "C4": (35.78, 1.8, 180),
    "C8": (36.6, 11.2, 180),
    "C6": (37.9, 6.5, 270),
    # amplifier end
    "J2": (LENGTH - 4.85, _MID + 2.54, 180),
    # test pads, on the underside (see BOTTOM)
    "TP1": (12.0, 3.6, 0), "TP3": (12.0, 9.4, 0), "TP2": (15.0, 9.4, 0),
    "TP6": (25.0, 6.5, 0), "TP8": (29.6, 3.6, 0), "TP7": (29.6, 9.4, 0),
    "TP4": (32.6, 3.6, 0), "TP5": (32.6, 9.4, 0),
}

# Parts on the underside. Only the test pads: they are bare copper, not fitted by
# the assembler, and there is no room for them among the parts on top.
BOTTOM = {f"TP{i}" for i in range(1, 9)}

# Silkscreen text: (text, x, y, side). JLCPCB's minimum is 1 mm high, 0.15 mm stroke.
# Top: one letter beside each wire pad, in the gap between the pad and its
# strain-relief hole. Bottom: the full legend, test pad names and the board name.
_J1_X, _J2_X = 4.85, LENGTH - 4.85
SILK: list[tuple[str, float, float, str]] = [
    ("+", _J1_X - 1.55, _MID - 1.27, "top"), ("G", _J1_X - 1.55, _MID + 1.27, "top"),
    ("G", _J2_X + 1.55, _MID - 2.54, "top"), ("R", _J2_X + 1.55, _MID, "top"),
    ("T", _J2_X + 1.55, _MID + 2.54, "top"),
    ("+12V", 8.6, _MID - 1.27, "bottom"), ("GND", 8.6, _MID + 1.27, "bottom"),
    ("5 GND", 36.6, _MID - 2.54, "bottom"), ("3 RX", 36.6, _MID, "bottom"),
    ("2 TX", 36.6, _MID + 2.54, "bottom"),
    ("WIIM-JBL r1", 19.5, 1.9, "bottom"),
]
# Test pad names go beside each pad on the bottom: (dx, dy) from the pad centre.
TEST_PAD_LABEL_OFFSET = (0.0, 1.6)

# Tracks and vias are filled in by the routing step.
# TRACKS: (net, layer, width, [(x, y), ...]);  VIAS: (net, x, y)
TRACKS: list[tuple[str, str, float, list[tuple[float, float]]]] = []
VIAS: list[tuple[str, float, float]] = []
