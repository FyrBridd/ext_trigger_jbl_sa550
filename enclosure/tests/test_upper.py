import math

import pytest

from enclosure import keepouts as k, model, params as p


@pytest.fixture(scope="module")
def upper():
    return model.upper()


@pytest.fixture(scope="module")
def lower():
    return model.lower()


def test_one_valid_solid_above_the_split(upper):
    assert upper.solids().size() == 1 and upper.val().isValid()
    b = upper.val().BoundingBox()
    assert math.isclose(b.xmin, p.X_MIN, abs_tol=1e-6) and math.isclose(b.xmax, p.X_MAX, abs_tol=1e-6)
    assert math.isclose(b.zmin, 0, abs_tol=1e-6) and math.isclose(b.zmax, p.OD / 2, abs_tol=1e-3)


def test_halves_meet_without_overlapping(upper, lower):
    assert k.overlap(upper, lower) == 0.0
    both = upper.val().BoundingBox().add(lower.val().BoundingBox())
    assert math.isclose(both.ylen, p.OD, abs_tol=1e-3) and math.isclose(both.zlen, p.OD, abs_tol=1e-3)


def test_board_and_parts_fit_under_the_lid(upper):
    assert k.overlap(upper, k.board()) == 0.0
    assert k.overlap(upper, k.parts(0.3)) == 0.0


def test_rails_hold_the_board_down_without_touching_it(upper):
    for side in (+1, -1):
        rail = k.box(x=(2, 43), y=sorted((side * 6.0, side * 6.7)), z=(0.8, 2.9))
        assert math.isclose(k.overlap(upper, rail), k.volume(rail), rel_tol=1e-6)      # the rail is there
        gap = k.box(x=(2, 43), y=sorted((side * 6.0, side * 6.7)), z=(0.46, 0.74))
        assert k.overlap(upper, gap) == 0.0                                           # 0.3 mm above the board


def test_wires_can_cross_the_ends_of_the_board(upper):
    # the rails stop short of each end, so the full width is open over the wire pads' strain-relief holes
    for x in ((-0.29, 0.99), (44.01, 45.29)):
        assert k.overlap(upper, k.box(x=x, y=(-6.79, 6.79), z=(0.46, p.Z_CEILING - 0.01))) == 0.0


def test_led_hole_is_over_the_led(upper):
    # D3 on the board: 27.98 mm from the trigger end, 1.8 mm from the upper edge, so 4.7 mm above the
    # centreline. Written out here, not read from params, so a mirrored model cannot agree with itself.
    def sight(diameter, y=4.7):
        return k.rod_z((27.98, y), diameter, 0.45, 12)
    assert k.overlap(upper, sight(p.LED_HOLE_D - 0.05)) == 0.0               # clear line of sight
    assert k.overlap(upper, sight(p.LED_HOLE_D + 0.6)) > 0.0                 # and no bigger than meant
    assert k.overlap(upper, sight(p.LED_HOLE_D - 0.05, y=-4.7)) > 0.0        # not mirrored


def test_upper_collars_and_chambers(upper):
    for collar in (p.TRIGGER_COLLAR, p.AMP_COLLAR):
        assert k.overlap(upper, k.wire_room(collar)) == 0.0
        assert k.overlap(upper, k.cable(collar, collar.rib_d - 0.02)) == 0.0
        assert k.overlap(upper, k.cable(collar)) > 0.0
    assert k.overlap(upper, k.cable(p.AMP_COLLAR, 3.7)) == 0.0               # the fat collar is at the amp end


def test_ribs_of_the_two_halves_make_whole_rings(upper, lower):
    for collar in (p.TRIGGER_COLLAR, p.AMP_COLLAR):
        ring = math.pi / 4 * (collar.cable.jacket_dia ** 2 - collar.rib_d ** 2) * p.RIB_W * len(p.RIB_AT)
        in_cable = k.cable(collar)
        assert math.isclose(k.overlap(upper, in_cable) + k.overlap(lower, in_cable), ring, rel_tol=0.02)
        for lo, hi in collar.rib_spans():          # and each half's ribs are at the same place along the cable
            slice_ = k.rod_x(lo + 0.01, hi - 0.01, collar.cable.jacket_dia)
            assert k.overlap(upper, slice_) > 0.0 and k.overlap(lower, slice_) > 0.0


def test_screws_pass_and_their_heads_are_sunk(upper):
    above = p.OD / 2 + 1
    for xy in p.SCREW_XY:
        assert k.overlap(upper, k.screw(xy, p.CLEAR_D - 0.05, 0, above)) == 0.0
        assert k.overlap(upper, k.screw(xy, p.CLEAR_D + 0.4, 0, p.SEAT_Z - 0.1)) > 0.0            # not oversize
        assert k.overlap(upper, k.screw(xy, p.SCREW_HEAD_D, p.SEAT_Z, above)) == 0.0              # head goes in
        assert k.overlap(upper, k.screw(xy, p.SCREW_HEAD_D, p.SEAT_Z - 1.0, p.SEAT_Z - 0.1)) > 0.0   # and has a seat
        top = math.sqrt((p.OD / 2) ** 2 - (abs(xy[1]) + p.SCREW_HEAD_D / 2) ** 2)
        assert p.SEAT_Z + p.SCREW_HEAD_H <= top                                                    # nothing sticks out


def test_no_thin_wall_beside_the_screw_heads(upper):
    # A counterbore through a round surface leaves a wall beside the head that tapers to nothing.
    # It is cut off where it would be thinner than JLC3DP's minimum, and whole below that.
    r = p.OD / 2
    edge = p.SCREW_Y + p.CBORE_D / 2                                    # the counterbore's outer edge
    thin_from = math.sqrt(r ** 2 - (edge + p.HEAD_WALL_MIN) ** 2)
    assert p.HEAD_WALL_MIN >= 1.2 and thin_from > p.SEAT_Z + 1.0
    for x, y in p.SCREW_XY:
        side = 1 if y > 0 else -1
        feather = k.box(x=(x - 0.5, x + 0.5), y=sorted((side * edge, side * r)), z=(thin_from + 0.05, r))
        assert k.overlap(upper, feather) == 0.0
        wall = k.box(x=(x - 0.2, x + 0.2), y=sorted((side * (edge + 0.05), side * (edge + p.HEAD_WALL_MIN - 0.05))),
                     z=(p.SEAT_Z + 0.05, thin_from - 0.05))
        assert math.isclose(k.overlap(upper, wall), k.volume(wall), rel_tol=1e-6)


def _head_recesses() -> float:
    """Volume taken out of the round body for the four screw heads: each counterbore, plus the
    slot that opens its outer side above the height where the wall beside it would be too thin."""
    r = p.OD / 2
    body = k.rod_x(p.X_MIN, p.X_MAX, p.OD)
    thin_from = math.sqrt(r ** 2 - (p.SCREW_Y + p.CBORE_D / 2 + p.HEAD_WALL_MIN) ** 2)
    total = 0.0
    for x, y in p.SCREW_XY:
        side = 1 if y > 0 else -1
        bore = k.rod_z((x, y), p.CBORE_D, p.SEAT_Z, p.OD)
        slot = k.box((x - p.CBORE_D / 2, x + p.CBORE_D / 2), sorted((y, side * p.OD)), (thin_from, p.OD))
        total += k.overlap(body, bore.union(slot))
    return total


def test_screws_reach_their_pilot_holes(upper, lower):
    for xy in p.SCREW_XY:
        shank = k.screw(xy, p.PILOT_D - 0.05, p.SEAT_Z - p.SCREW_LEN, p.SEAT_Z)
        assert k.overlap(upper, shank) == 0.0 and k.overlap(lower, shank) == 0.0
        thread = k.screw(xy, p.SCREW_THREAD, p.SEAT_Z - p.SCREW_LEN, 0)
        assert k.overlap(lower, thread) > 0.0 and k.overlap(upper, k.screw(xy, p.SCREW_THREAD, 0, p.SEAT_Z)) == 0.0


def _expected_volumes() -> tuple[float, float]:
    """What each half's volume should be: its half-cylinder less the cuts listed here, worked out
    by hand (the head recesses by building them again from their description)."""
    r = p.OD / 2
    half = math.pi * r ** 2 / 2 * (p.X_MAX - p.X_MIN)
    pocket_l = p.BOARD_L + 2 * p.GAP
    chambers = 2 * (math.pi * p.CHAMBER_R ** 2 / 2 * p.CHAMBER_L)
    ribs = len(p.RIB_AT) * p.RIB_W
    bores = sum(math.pi / 8 * (c.bore_d ** 2 * (c.length - ribs) + c.rib_d ** 2 * ribs) for c in p.COLLARS)
    xs = [x for x, _ in p.J3_HOLES_XY]
    ys = [y for _, y in p.J3_HOLES_XY]
    m = p.PIN_POCKET_MARGIN
    lower_cuts = (
        2 * p.POCKET_HALF_W * pocket_l * -p.Z_BOARD_BOTTOM                                   # board pocket
        + 2 * p.TRENCH_HALF_W * pocket_l * p.UNDER_ROOM                                      # trench
        + (max(xs) - min(xs) + 2 * m) * (max(ys) - min(ys) + 2 * m) * (p.Z_TRENCH - p.PIN_POCKET_Z)   # pin pocket
        + chambers + bores
        + 4 * math.pi / 4 * p.PILOT_D ** 2 * p.PILOT_DEPTH                                   # pilot holes
        + 4 * math.pi / 4 * (p.PILOT_RELIEF_D ** 2 - p.PILOT_D ** 2) * p.PILOT_RELIEF_DEPTH  # and their relieved mouths
    )
    rails = 2 * (p.POCKET_HALF_W - p.RAIL_INNER_Y) * (p.BOARD_L - 2 * p.RAIL_END) * (p.Z_CEILING - p.Z_RAIL)
    led_depth = math.sqrt(r ** 2 - p.LED_XY[1] ** 2) - p.Z_CEILING      # on the hole's axis
    upper_cuts = (
        2 * p.POCKET_HALF_W * pocket_l * p.Z_CEILING - rails                                 # cavity less the rails
        + chambers + bores
        + 4 * math.pi / 4 * p.CLEAR_D ** 2 * p.SEAT_Z                                        # clearance holes
        + _head_recesses()                                                                   # counterbores
        + math.pi / 4 * p.LED_HOLE_D ** 2 * led_depth                                        # LED hole
    )
    return half - lower_cuts, half - upper_cuts


VOLUME_TOLERANCE = 0.5      # mm^3: a 1 mm hole 1 mm deep is 0.8


def test_nothing_else_is_cut_away(upper, lower):
    # A hole in the wrong place, or one left out, shows as plastic missing or left over.
    expected_lower, expected_upper = _expected_volumes()
    assert math.isclose(k.volume(lower), expected_lower, abs_tol=VOLUME_TOLERANCE)
    assert math.isclose(k.volume(upper), expected_upper, abs_tol=VOLUME_TOLERANCE)


def test_a_stray_hole_would_be_noticed(upper, lower):
    # the check above is only as good as its tolerance: spoil each half slightly and it must object
    expected_lower, expected_upper = _expected_volumes()
    holed_lid = upper.cut(k.rod_z((10, -3), 2.0, 0, p.OD))                      # a second 2 mm hole through the lid
    assert not math.isclose(k.volume(holed_lid), expected_upper, abs_tol=VOLUME_TOLERANCE)
    plugged_lid = upper.union(k.rod_z(p.LED_XY, p.LED_HOLE_D, p.Z_CEILING + 0.5, p.Z_CEILING + 1.5))   # LED hole blocked
    assert not math.isclose(k.volume(plugged_lid), expected_upper, abs_tol=VOLUME_TOLERANCE)
    holed_floor = lower.cut(k.rod_z((30, 0), 1.0, -p.OD, 0))                    # a 1 mm hole through the floor
    assert not math.isclose(k.volume(holed_floor), expected_lower, abs_tol=VOLUME_TOLERANCE)


def test_the_lid_goes_on_only_one_way_round(upper):
    # Turned end for end, the lid's screw holes must miss the pilot holes by so much that a screw
    # cannot be started: wherever it sits in the lid's hole, its axis is on solid plastic, well
    # clear of the pilot hole's mouth.
    middle = (p.X_MIN + p.X_MAX) / 2
    slop = (p.CLEAR_D - p.SCREW_THREAD) / 2
    turned_holes = [(2 * middle - x, -y) for x, y in p.SCREW_XY]
    for pilot in p.SCREW_XY:
        miss = min(math.dist(pilot, hole) for hole in turned_holes)
        assert miss - slop >= p.PILOT_RELIEF_D / 2 + 0.5
    turned = upper.rotate((middle, 0, 0), (middle, 0, 1), 180)
    for pilot in p.SCREW_XY:              # and a screw standing in each pilot hole is stopped by the turned lid
        shank = k.screw(pilot, p.SCREW_THREAD, 0.05, p.SEAT_Z)
        assert k.overlap(turned, shank) > 0.8 * k.volume(shank)
