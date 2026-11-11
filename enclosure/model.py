"""The two half-shells, built from params.py.

lower() holds the board: it has the board pocket, the trench for the wire runs, the pocket
for the programming cable's pins, and the pilot holes the screws cut their thread in.
Both are a half cylinder with things cut out of it, in the shell's frame (see params.py).
"""
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
    return _cut_all(_half_cylinder(upper=False), tools)
