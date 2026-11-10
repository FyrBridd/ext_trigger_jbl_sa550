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
    # programming footprint: the 3.3 V and UPDI pads face the regulator, the ground
    # pad faces the controller (the other way round, 3.3 V cannot get out)
    "J3": (21.4, 6.6, 90),
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
    "TP6": (25.5, 5.7, 0), "TP8": (29.6, 3.6, 0), "TP7": (29.6, 9.4, 0),
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

# --- copper ---------------------------------------------------------------------
import json as _json
import pathlib as _pathlib

TRACK_SIGNAL = 0.25
TRACK_POWER = 0.4
CLEARANCE = 0.2
ROUTING_CLEARANCE = 0.26   # what the autorouter is asked to keep, leaving margin for its neck-downs being widened back
VIA_DIAMETER, VIA_DRILL = 0.6, 0.3
POWER_NETS = ["TRIG_IN", "TRIG_R", "VIN", "+3V3", "GND"]

# Ground is routed as tracks like every other net, then covered by a filled pour
# on both layers.
GND_ZONE_INSET = 0.5          # pour edge to board edge
TAG_CONNECT_PAD_CLEARANCE = 0.55   # Tag-Connect asks for 0.51 mm from each contact pad

# Hand-routed connections around the programming footprint. The autorouter cannot
# find a way out for all three pads through the Tag-Connect keep-outs, so these
# are drawn by hand, locked, and given to the router as existing wiring.
#   3.3 V: out to the left, down, and along to the regulator's output capacitor.
#   UPDI:  out to the left and up to a via clear of the footprint, across on the
#          underside (through its test pad) to a via under the controller, then
#          up to the controller's pin.
#   GND:   out to the right to a via between the footprint and the controller;
#          the controller's own ground pin joins the same via.
FIXED_TRACKS: list[tuple[str, str, float, list[tuple[float, float]]]] = [
    ("+3V3", "F.Cu", TRACK_POWER, [(20.77, 7.87), (19.3, 7.87), (19.3, 10.2), (15.65, 10.2), (15.65, 8.5)]),
    ("UPDI", "F.Cu", TRACK_SIGNAL, [(20.77, 6.6), (19.3, 6.6), (19.3, 2.0)]),
    ("UPDI", "B.Cu", TRACK_SIGNAL, [(19.3, 2.0), (25.5, 2.0), (25.5, 5.7), (26.83, 5.7)]),
    ("UPDI", "F.Cu", TRACK_SIGNAL, [(26.83, 5.7), (26.83, 4.03)]),
    ("GND", "F.Cu", TRACK_POWER, [(22.03, 6.6), (23.8, 6.6)]),
    ("GND", "F.Cu", TRACK_POWER, [(24.3, 4.03), (24.3, 6.1), (23.8, 6.6)]),
]
FIXED_VIAS: list[tuple[str, float, float]] = [("UPDI", 19.3, 2.0), ("UPDI", 26.83, 5.7), ("GND", 23.8, 6.6)]

# Signal and power routing produced by the autorouter (see autoroute.py) and saved
# in routes.json, so the board can be regenerated without running the router.
# TRACKS: (net, layer, width, [(x, y), ...]);  VIAS: (net, x, y)
_ROUTES = _pathlib.Path(__file__).with_name("routes.json")
_saved = _json.loads(_ROUTES.read_text()) if _ROUTES.exists() else {"tracks": [], "vias": []}
ROUTED_TRACKS: list = [(t["net"], t["layer"], t["width"], [tuple(p) for p in t["points"]]) for t in _saved["tracks"]]
ROUTED_VIAS: list = [(v["net"], v["x"], v["y"]) for v in _saved["vias"]]

# Vias stitching the top and bottom ground pours together. They are chosen by
# stitch.py after routing (they must dodge the routed tracks) and saved alongside
# the routes.
GND_TRACKS: list[tuple[str, str, float, list[tuple[float, float]]]] = []
GND_VIAS: list[tuple[str, float, float]] = [("GND", x, y) for x, y in _saved.get("stitch", [])]
STITCH_X_RANGE = (6.5, LENGTH - 6.5)   # keep stitching vias out from under the wire runs

TRACKS = FIXED_TRACKS + ROUTED_TRACKS + GND_TRACKS
VIAS = FIXED_VIAS + ROUTED_VIAS + GND_VIAS
