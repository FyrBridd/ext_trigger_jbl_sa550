"""Solids for the things the shell must fit round, in the shell's frame (see params.py).

The tests intersect these with the two half-shells: no overlap means it fits, a required
overlap means the shell grips or supports there. Every function returns a Workplane holding
exactly one shape (a solid, or a compound of several), so .val() is the whole thing.
"""
import cadquery as cq

from enclosure import params as p

TOUCHING = 1e-6          # an intersection smaller than this (mm^3) is two faces touching
BEYOND_END = 2.0         # a cable is drawn this far out of the shell's end
WIRE_ROOM_MARGIN = 0.5   # the wire-room rod is this much smaller in radius than the chamber
WIRE_ROOM_END = 0.2      # and stops this far short of each end of it
SIGHTLINE_TOP = 12.0     # a line of sight from the LED runs up to here, well outside the shell


def _one(shapes) -> cq.Workplane:
    shapes = [s.val() if isinstance(s, cq.Workplane) else s for s in shapes]
    whole = shapes[0] if len(shapes) == 1 else cq.Compound.makeCompound(shapes)
    return cq.Workplane("XY").newObject([whole])


def box(x, y, z) -> cq.Workplane:
    """An axis-aligned box between the given (low, high) limits on each axis."""
    (x1, x2), (y1, y2), (z1, z2) = x, y, z
    return cq.Workplane("XY").box(x2 - x1, y2 - y1, z2 - z1, centered=False).translate((x1, y1, z1))


def rod_x(x1: float, x2: float, diameter: float, y: float = 0.0, z: float = 0.0) -> cq.Workplane:
    """A round rod along the shell, from x1 to x2."""
    return cq.Workplane("YZ").circle(diameter / 2).extrude(x2 - x1).translate((x1, y, z))


def rod_z(xy, diameter: float, z1: float, z2: float) -> cq.Workplane:
    """A round rod standing upright at xy, from z1 to z2."""
    return cq.Workplane("XY").circle(diameter / 2).extrude(z2 - z1).translate((xy[0], xy[1], z1))


def board() -> cq.Workplane:
    """The bare board."""
    return box((0, p.BOARD_L), (-p.BOARD_W / 2, p.BOARD_W / 2), (p.Z_BOARD_BOTTOM, p.Z_BOARD_TOP))


def parts(clearance: float = 0.0) -> cq.Workplane:
    """Where fitted parts may be: the board less its edge margin, up to the tallest part.
    Grown by `clearance` on every side except downward."""
    c = clearance
    half = p.BOARD_W / 2 - p.PART_EDGE
    return box(
        (p.PART_EDGE - c, p.BOARD_L - p.PART_EDGE + c),
        (-half - c, half + c),
        (p.Z_BOARD_TOP, p.Z_BOARD_TOP + p.PART_H + c),
    )


def underside(clearance: float = 0.0) -> cq.Workplane:
    """Where the wires run under the board, between each strain-relief hole and its pad.
    Grown by `clearance` on every side except upward."""
    c = clearance
    y = (-p.WIRE_ZONE_HALF_W - c, p.WIRE_ZONE_HALF_W + c)
    z = (p.Z_BOARD_BOTTOM - p.WIRE_RUN_H - c, p.Z_BOARD_BOTTOM)
    return _one([
        box((-c, p.WIRE_ZONE_L + c), y, z),
        box((p.BOARD_L - p.WIRE_ZONE_L - c, p.BOARD_L + c), y, z),
    ])


def _outward(collar: p.Collar) -> int:
    return 1 if collar.x_outer > collar.x_inner else -1


def cable(collar: p.Collar, diameter: float | None = None) -> cq.Workplane:
    """The cable lying in a collar: a rod on the axis, of the jacket's diameter unless one
    is given, from the collar's inner end to a little beyond the shell's end."""
    d = collar.cable.jacket_dia if diameter is None else diameter
    ends = sorted((collar.x_inner, collar.x_outer + _outward(collar) * BEYOND_END))
    return rod_x(ends[0], ends[1], d)


def chamber_span(collar: p.Collar) -> tuple[float, float]:
    """The x range of the wire chamber between a collar and the board pocket."""
    pocket_end = -p.GAP if _outward(collar) < 0 else p.BOARD_L + p.GAP
    return tuple(sorted((collar.x_inner, pocket_end)))


def wire_room(collar: p.Collar) -> cq.Workplane:
    """Space the wires need between the cable's end and the board: most of the chamber."""
    x1, x2 = chamber_span(collar)
    return rod_x(x1 + WIRE_ROOM_END, x2 - WIRE_ROOM_END, 2 * (p.CHAMBER_R - WIRE_ROOM_MARGIN))


def programming_pins() -> cq.Workplane:
    """The Tag-Connect cable's three alignment pins, pushed through the board."""
    return _one([
        rod_z(xy, p.PIN_D, p.Z_BOARD_BOTTOM - p.PIN_BELOW, p.Z_BOARD_TOP) for xy in p.J3_HOLES_XY
    ])


def led_sightline(diameter: float) -> cq.Workplane:
    """A straight line of sight up from the LED."""
    return rod_z(p.LED_XY, diameter, p.Z_BOARD_TOP, SIGHTLINE_TOP)


def screw(xy, diameter: float, z_from: float, z_to: float) -> cq.Workplane:
    """A rod on one screw's axis."""
    return rod_z(xy, diameter, z_from, z_to)


def _shape(thing) -> cq.Shape:
    return thing.val() if isinstance(thing, cq.Workplane) else thing


def volume(shape) -> float:
    return _shape(shape).Volume()


def overlap(a, b) -> float:
    """Volume of the intersection in mm^3; exactly 0.0 when the two do not meet or only touch."""
    v = _shape(a).intersect(_shape(b)).Volume()
    return v if v > TOUCHING else 0.0
