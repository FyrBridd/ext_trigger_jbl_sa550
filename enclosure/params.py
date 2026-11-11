"""Every dimension of the enclosure, in millimetres, with where it comes from.

One frame for everything in enclosure/:

- x runs along the shell: 0 at the board's trigger-end edge, BOARD_L at its amp-end edge.
- y runs across: 0 on the board's centreline. Looking down on the top of the board with
  the trigger end on the left, +y is away from you (the board's upper edge in board.pdf).
- z is up: 0 on the plane where the two halves meet, which is also the cylinder's axis.

hardware/design/layout.py measures y downward from the board's upper edge, so a layout
point (x, y) is the shell point (x, WIDTH/2 - y).

Sizes that belong to the board or the cables are read from hardware/design, not retyped.
This module must not import pcbnew: KiCad and CadQuery each bring their own OpenCascade.
"""
import math
import pathlib
from dataclasses import dataclass

from hardware.design import cables, layout
from hardware.design.kicad import parse_sexpr

_FOOTPRINTS = pathlib.Path(__file__).resolve().parents[1] / "hardware" / "lib" / "dongle.pretty"

# --- the shell ----------------------------------------------------------------------
OD = 20.0                 # outside diameter: the least that leaves more than 1.5 mm of plastic round
                          # every screw bore over its whole depth, with the print 0.3 mm small

# --- the board ----------------------------------------------------------------------
BOARD_L = layout.LENGTH
BOARD_W = layout.WIDTH
BOARD_T = 1.6             # the thickness ordered from JLCPCB (docs/hardware-review.md, section 6)
GAP = 0.3                 # room round the board's edges and ends
Z_BOARD_BOTTOM = -1.15
Z_BOARD_TOP = round(Z_BOARD_BOTTOM + BOARD_T, 3)

# --- room round the board -----------------------------------------------------------
PART_H = 1.75             # tallest fitted part, the SOIC-8 (docs/hardware-review.md, section 5)
PART_EDGE = 1.0           # no fitted part is nearer a board edge than this (hardware/tests/test_board.py)
TOP_ROOM = 2.5            # cavity above the board
UNDER_ROOM = 1.8          # trench below the board, for the wire runs
WIRE_RUN_H = 1.2          # how far a wire run may hang below the board
WIRE_ZONE_L = 7.0         # the wires stay within this distance of each end of the board...
WIRE_ZONE_HALF_W = 4.5    # ...and this far either side of the centreline
LEDGE_W = 1.6             # each long edge of the board pocket is a ledge this wide
POCKET_HALF_W = BOARD_W / 2 + GAP
TRENCH_HALF_W = round(POCKET_HALF_W - LEDGE_W, 3)
Z_CEILING = round(Z_BOARD_TOP + TOP_ROOM, 3)
Z_TRENCH = round(Z_BOARD_BOTTOM - UNDER_ROOM, 3)
RAIL_GAP = 0.3            # the upper half's hold-down rails stop this far above the board
RAIL_INNER_Y = 5.9        # rails occupy |y| from here to the pocket's side
RAIL_END = 1.0            # rails stop this far inside each end of the board
Z_RAIL = round(Z_BOARD_TOP + RAIL_GAP, 3)

# --- the ends -----------------------------------------------------------------------
CHAMBER_L = 6.0           # length of the wire chamber between each collar and the board
CHAMBER_R = 5.5           # its radius
WIRE_ROOM_R = 5.0         # the wires need a clear space of this radius in each chamber
COLLAR_L = 7.6            # length of each cable collar: a screw's counterbore with 1.2 mm of wall each side
X_MIN = round(-(GAP + CHAMBER_L + COLLAR_L), 3)
X_MAX = round(BOARD_L + GAP + CHAMBER_L + COLLAR_L, 3)
BORE_CLEARANCE = 0.3      # collar bore diameter = cable jacket + this
RIB_BITE = 0.7            # rib inner diameter = cable jacket - this
RIB_W = 1.0               # each rib is a ring this wide
RIB_AT = (1.5, 4.5)       # rib centres, measured from the shell's end

# --- screws: thread-forming, for plastics (docs/enclosure.md names the part) ----------
SCREW_THREAD = 2.2
SCREW_LEN = 8.0
SCREW_HEAD_D = 4.2        # largest head allowed for (the named screw's is 3.9)
SCREW_HEAD_H = 1.7        # (the named screw's is 1.5)
DRIVER_BLADE_D = 4.5      # round blade of a PZ1 screwdriver, which has to enter the counterbore
PILOT_D = 1.8             # in the lower half; the supplier's figure for nylon is 0.75 x thread = 1.65,
                          # and JLC3DP's holes come out small
PILOT_DEPTH = 5.5
PILOT_RELIEF_D = 2.4      # the mouth of each pilot hole is opened to just over the thread's diameter,
PILOT_RELIEF_DEPTH = 0.6  # so plastic raised by the thread cannot hold the halves apart
CLEAR_D = 2.6             # through the upper half
CBORE_D = 5.2             # counterbore for the head and the driver's blade
SEAT_Z = 3.0              # the head sits on a seat at this height
SCREW_Y = 5.1
SCREW_XY = tuple(
    (round(x, 3), y)
    for x in (X_MIN + COLLAR_L / 2, X_MAX - COLLAR_L / 2)   # the middle of each collar
    for y in (SCREW_Y, -SCREW_Y)
)

# --- openings -----------------------------------------------------------------------
LED_HOLE_D = 2.0
PIN_POCKET_Z = -4.0       # floor of the pocket under the programming footprint
PIN_POCKET_MARGIN = 1.0   # the pocket reaches this far beyond the three alignment holes
PIN_D = 1.2               # allowance for a Tag-Connect alignment pin (the holes are 0.99 mm)
PIN_BELOW = 2.2           # how far the pins are allowed to come out under the board (1.6 mm by the drawing)


def board_to_shell(x: float, y: float) -> tuple[float, float]:
    """A point in layout.py's frame (y down from the board's upper edge), in the shell's frame."""
    return (round(x, 3), round(BOARD_W / 2 - y, 3))


def _footprint_pads(name: str):
    """(number, kind, x, y) of every pad in one of the project's footprints, in its own frame."""
    tree = parse_sexpr((_FOOTPRINTS / f"{name}.kicad_mod").read_text())
    for node in tree:
        if isinstance(node, list) and node and node[0] == "pad":
            at = next(child for child in node if isinstance(child, list) and child[0] == "at")
            yield str(node[1]), node[2], float(at[1]), float(at[2])


def _placed(ref: str, fx: float, fy: float) -> tuple[float, float]:
    """A footprint point of a placed part, in the shell's frame, to 0.01 mm.
    KiCad turns a part anticlockwise seen from the top, with y pointing down."""
    px, py, degrees = layout.PLACEMENTS[ref]
    turn = math.radians(degrees)
    x = px + fx * math.cos(turn) + fy * math.sin(turn)
    y = py - fx * math.sin(turn) + fy * math.cos(turn)
    sx, sy = board_to_shell(x, y)
    return (round(sx, 2), round(sy, 2))


LED_XY = board_to_shell(*layout.PLACEMENTS["D3"][:2])

# the programming footprint's three unplated alignment holes
J3_HOLES_XY = tuple(
    _placed("J3", x, y) for _, kind, x, y in _footprint_pads("TC2030-MCP-NL") if kind == "np_thru_hole"
)

# the five plated pads the cable wires are soldered into
WIRE_PADS_XY = tuple(
    _placed(ref, x, y)
    for ref, footprint in (("J1", "WirePads_1x02_Strain"), ("J2", "WirePads_1x03_Strain"))
    for _, kind, x, y in _footprint_pads(footprint)
    if kind == "thru_hole"
)


@dataclass(frozen=True)
class Collar:
    """The part of the shell that clamps one cable's outer jacket."""
    x_outer: float        # at the shell's end
    x_inner: float        # where it opens into the wire chamber
    cable: cables.Cable

    @property
    def bore_d(self) -> float:
        return round(self.cable.jacket_dia + BORE_CLEARANCE, 3)

    @property
    def rib_d(self) -> float:
        return round(self.cable.jacket_dia - RIB_BITE, 3)

    def rib_spans(self) -> list[tuple[float, float]]:
        """The x range of each rib, lowest x first."""
        inward = 1 if self.x_inner > self.x_outer else -1
        centres = sorted(self.x_outer + inward * at for at in RIB_AT)
        return [(c - RIB_W / 2, c + RIB_W / 2) for c in centres]


TRIGGER_COLLAR = Collar(x_outer=X_MIN, x_inner=round(X_MIN + COLLAR_L, 3), cable=cables.TRIGGER)
AMP_COLLAR = Collar(x_outer=X_MAX, x_inner=round(X_MAX - COLLAR_L, 3), cable=cables.SERIAL)
COLLARS = (TRIGGER_COLLAR, AMP_COLLAR)
