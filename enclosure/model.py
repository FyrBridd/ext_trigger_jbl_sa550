"""The two half-shells, built from params.py.

lower() holds the board: it has the board pocket, the trench for the wire runs, the pocket
for the programming cable's pins, and the pilot holes the screws cut their thread in.
upper() is the lid: it has the cavity over the parts, two rails that stop the board lifting,
the screws' clearance holes and counterbores, and the LED hole.
Both are a half cylinder with things cut out of it, in the shell's frame (see params.py).
"""
import math

import cadquery as cq

from enclosure import keepouts as k, params as p

_OVER = 1.0   # cutting tools reach this far past the surface they open through, so no skin is left


def _half_cylinder(upper: bool) -> cq.Workplane:
    whole = k.rod_x(p.X_MIN, p.X_MAX, p.OD)
    side = (0, p.OD) if upper else (-p.OD, 0)
    return whole.intersect(k.box((p.X_MIN - _OVER, p.X_MAX + _OVER), (-p.OD, p.OD), side))


def _cable_way(collar: p.Collar) -> list[cq.Workplane]:
    """What is cut away for one cable: the wire chamber, and the collar's bore between and
    beside its ribs. The ribs are left standing, bored only to their own smaller diameter."""
    lo, hi = sorted((collar.x_outer, collar.x_inner))
    if collar.x_outer < collar.x_inner:
        lo -= _OVER                  # open through the shell's end
    else:
        hi += _OVER
    cuts = [k.rod_x(*k.chamber_span(collar), 2 * p.CHAMBER_R), k.rod_x(lo, hi, collar.rib_d)]
    edges = [lo, *(x for span in collar.rib_spans() for x in span), hi]
    cuts += [k.rod_x(a, b, collar.bore_d) for a, b in zip(edges[0::2], edges[1::2])]
    return cuts


def _cut_all(body: cq.Workplane, tools) -> cq.Workplane:
    for tool in tools:
        body = body.cut(tool)
    return body.clean()


def lower() -> cq.Workplane:
    pocket_x = (-p.GAP, p.BOARD_L + p.GAP)
    xs = [x for x, _ in p.J3_HOLES_XY]
    ys = [y for _, y in p.J3_HOLES_XY]
    m = p.PIN_POCKET_MARGIN
    tools = [
        # the board pocket, and under it the trench for the wire runs: the step between them is the ledge
        k.box(pocket_x, (-p.POCKET_HALF_W, p.POCKET_HALF_W), (p.Z_BOARD_BOTTOM, _OVER)),
        k.box(pocket_x, (-p.TRENCH_HALF_W, p.TRENCH_HALF_W), (p.Z_TRENCH, _OVER)),
        # room for the programming cable's alignment pins, which come through the board
        k.box((min(xs) - m, max(xs) + m), (min(ys) - m, max(ys) + m), (p.PIN_POCKET_Z, _OVER)),
    ]
    for collar in p.COLLARS:
        tools += _cable_way(collar)
    tools += [k.rod_z(xy, p.PILOT_D, -p.PILOT_DEPTH, _OVER) for xy in p.SCREW_XY]
    tools += [k.rod_z(xy, p.PILOT_RELIEF_D, -p.PILOT_RELIEF_DEPTH, _OVER) for xy in p.SCREW_XY]
    return _cut_all(_half_cylinder(upper=False), tools)


def upper() -> cq.Workplane:
    pocket_x = (-p.GAP, p.BOARD_L + p.GAP)
    wide = (-p.POCKET_HALF_W, p.POCKET_HALF_W)
    above_rails = (p.Z_RAIL, p.Z_CEILING)
    out = p.OD                     # anything cut up to here opens through the round outside
    tools = [
        # the cavity over the board: full width up to the rails' underside...
        k.box(pocket_x, wide, (-_OVER, p.Z_RAIL)),
        # ...then only between the rails...
        k.box(pocket_x, (-p.RAIL_INNER_Y, p.RAIL_INNER_Y), above_rails),
        # ...except at each end of the board, where the wires cross and the rails stop short
        k.box((-p.GAP, p.RAIL_END), wide, above_rails),
        k.box((p.BOARD_L - p.RAIL_END, p.BOARD_L + p.GAP), wide, above_rails),
        k.rod_z(p.LED_XY, p.LED_HOLE_D, 0, out),
    ]
    for collar in p.COLLARS:
        tools += _cable_way(collar)
    # A counterbore through the round outside leaves a wall beside the head that tapers to a
    # feather edge. Above the height where it would be thinner than the minimum, open that side.
    thin_from = math.sqrt((p.OD / 2) ** 2 - (p.SCREW_Y + p.CBORE_D / 2 + p.HEAD_WALL_MIN) ** 2)
    for x, y in p.SCREW_XY:
        outward = sorted((y, math.copysign(out, y)))
        tools += [
            k.rod_z((x, y), p.CLEAR_D, -_OVER, out),
            k.rod_z((x, y), p.CBORE_D, p.SEAT_Z, out),
            k.box((x - p.CBORE_D / 2, x + p.CBORE_D / 2), outward, (thin_from, out)),
        ]
    return _cut_all(_half_cylinder(upper=True), tools)
