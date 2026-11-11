import math

import pytest

from enclosure import keepouts as k, model, params as p


@pytest.fixture(scope="module")
def lower():
    return model.lower()


def test_one_valid_solid_below_the_split(lower):
    assert lower.solids().size() == 1 and lower.val().isValid()
    b = lower.val().BoundingBox()
    assert math.isclose(b.xmin, p.X_MIN) and math.isclose(b.xmax, p.X_MAX)
    assert math.isclose(b.zmax, 0, abs_tol=1e-6) and math.isclose(b.zmin, -p.OD / 2, abs_tol=1e-3)
    assert math.isclose(b.ylen, p.OD, abs_tol=1e-3)


def test_board_drops_in_and_rests_on_both_ledges(lower):
    assert k.overlap(lower, k.board()) == 0.0
    for side in (+1, -1):          # a sliver just under each long edge of the board must be plastic
        sliver = k.box(x=(1, 44), y=sorted((side * 5.4, side * 6.4)), z=(-1.35, -1.16))
        assert math.isclose(k.overlap(lower, sliver), k.volume(sliver), rel_tol=1e-6)


def test_board_has_room_all_round(lower):
    grown = k.box(x=(-0.29, 45.29), y=(-6.79, 6.79), z=(p.Z_BOARD_BOTTOM + 0.01, 0))
    assert k.overlap(lower, grown) == 0.0


def test_board_cannot_slide_endways(lower):
    for x in ((-1.3, -0.4), (45.4, 46.3)):   # plastic beyond each end of the board, at its edges
        for side in (+1, -1):
            stop = k.box(x=x, y=sorted((side * 5.9, side * 6.4)), z=(-1.1, -0.1))
            assert k.overlap(lower, stop) > 0.5 * k.volume(stop)


def test_parts_and_wires_have_clearance(lower):
    assert k.overlap(lower, k.underside(0.3)) == 0.0
    assert k.overlap(lower, k.parts(0.3)) == 0.0


def test_programming_pins_have_a_pocket(lower):
    assert k.overlap(lower, k.programming_pins()) == 0.0
    # and the pocket is only under the footprint: the same pins 6 mm along the board hit the floor
    for shift in (-6, 6):
        assert k.overlap(lower, k.programming_pins().translate((shift, 0, 0))) > 0.0


def test_wire_chambers_are_open(lower):
    for collar in (p.TRIGGER_COLLAR, p.AMP_COLLAR):
        assert k.overlap(lower, k.wire_room(collar)) == 0.0


def test_each_collar_matches_its_cable(lower):
    assert k.overlap(lower, k.cable(p.TRIGGER_COLLAR, 3.7)) > 0.0     # ribs bite a 3.7 mm cable
    assert k.overlap(lower, k.cable(p.AMP_COLLAR, 4.8)) > 0.0
    assert k.overlap(lower, k.cable(p.AMP_COLLAR, 3.7)) == 0.0        # the thin cable is loose in the fat collar


def test_collar_ribs_bite_but_the_cable_passes(lower):
    for collar in (p.TRIGGER_COLLAR, p.AMP_COLLAR):
        assert k.overlap(lower, k.cable(collar, collar.rib_d - 0.02)) == 0.0     # inside the ribs: free
        bite = k.overlap(lower, k.cable(collar, collar.cable.jacket_dia))
        ring = math.pi / 4 * (collar.cable.jacket_dia ** 2 - collar.rib_d ** 2) * p.RIB_W * len(p.RIB_AT) / 2
        assert math.isclose(bite, ring, rel_tol=0.02)                             # two half-rings, nothing else


def test_screw_holes(lower):
    for xy in p.SCREW_XY:
        assert k.overlap(lower, k.screw(xy, p.PILOT_D - 0.05, -p.PILOT_DEPTH + 0.05, 0)) == 0.0
        assert k.overlap(lower, k.screw(xy, p.PILOT_D + 0.4, -p.PILOT_DEPTH + 0.05, 0)) > 0.0   # not oversize
        assert k.overlap(lower, k.screw(xy, p.PILOT_D - 0.05, -p.PILOT_DEPTH - 1.0, -p.PILOT_DEPTH - 0.1)) > 0.0  # blind
