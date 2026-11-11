import math

from enclosure import params as p
from hardware.design import cables


def test_overall_size():
    assert p.OD == 20.0
    assert math.isclose(p.X_MAX - p.X_MIN, 74.8)
    assert math.isclose(p.X_MIN, -(p.GAP + p.CHAMBER_L + p.COLLAR_L + p.LID_KEY))
    assert math.isclose(p.X_MAX, p.BOARD_L + p.GAP + p.CHAMBER_L + p.COLLAR_L)


def test_board_frame():
    assert p.board_to_shell(0, 0) == (0, 6.5)
    assert p.board_to_shell(45, 13) == (45, -6.5)
    assert p.LED_XY == (27.98, 4.7)                       # D3, towards the board's upper edge
    assert sorted(p.J3_HOLES_XY) == [(20.38, 2.44), (21.4, -2.64), (22.42, 2.44)]


def test_wire_pads_are_at_the_ends_of_the_board():
    assert sorted(p.WIRE_PADS_XY) == [
        (4.85, -1.27), (4.85, 1.27),                       # trigger: G below the centreline, + above
        (40.15, -2.54), (40.15, 0.0), (40.15, 2.54),       # amp: T, R, G
    ]


def test_collars_follow_the_cables():
    assert p.TRIGGER_COLLAR.cable is cables.TRIGGER and p.AMP_COLLAR.cable is cables.SERIAL
    assert math.isclose(p.TRIGGER_COLLAR.bore_d, 4.0) and math.isclose(p.TRIGGER_COLLAR.rib_d, 3.0)
    assert math.isclose(p.AMP_COLLAR.bore_d, 5.1) and math.isclose(p.AMP_COLLAR.rib_d, 4.1)
    assert p.TRIGGER_COLLAR.x_outer == p.X_MIN and p.AMP_COLLAR.x_outer == p.X_MAX
    assert math.isclose(p.TRIGGER_COLLAR.length, p.AMP_COLLAR.length + p.LID_KEY) and p.TRIGGER_COLLAR.nose == p.LID_KEY
    assert math.isclose(p.TRIGGER_COLLAR.x_inner, -6.3) and math.isclose(p.AMP_COLLAR.x_inner, 51.3)


def test_ribs_sit_either_side_of_the_screws():
    assert [tuple(round(v, 3) for v in span) for span in p.TRIGGER_COLLAR.rib_spans()] == [(-12.9, -11.9), (-9.9, -8.9)]
    assert [tuple(round(v, 3) for v in span) for span in p.AMP_COLLAR.rib_spans()] == [(53.9, 54.9), (56.9, 57.9)]
    for collar in (p.TRIGGER_COLLAR, p.AMP_COLLAR):      # each pair of screws clamps between its collar's two ribs
        first, second = collar.rib_spans()
        mine = [x for x, _ in p.SCREW_XY if min(collar.x_outer, collar.x_inner) < x < max(collar.x_outer, collar.x_inner)]
        assert len(mine) == 2 and all(first[1] < x < second[0] for x in mine)


def test_ribs_grip_across_the_tolerances():
    # radial bite with the print 0.3 mm big and the cable at its thinnest, and the reverse
    for collar in (p.TRIGGER_COLLAR, p.AMP_COLLAR):
        c = collar.cable
        loosest = ((c.jacket_dia - c.jacket_tolerance) - (collar.rib_d + 0.3)) / 2
        tightest = ((c.jacket_dia + c.jacket_tolerance) - (collar.rib_d - 0.3)) / 2
        assert loosest > 0.09 and tightest < 0.61


def test_jlc3dp_rules():
    corner_wall = p.OD / 2 - math.hypot(p.BOARD_W / 2 + p.GAP, p.Z_BOARD_TOP + p.TOP_ROOM)
    assert corner_wall >= 1.5
    assert p.PILOT_D >= 1.5 and p.LED_HOLE_D >= 2.0 and p.RIB_W >= 0.8
    for x, y in p.SCREW_XY:                               # plastic round every screw
        assert p.OD / 2 - math.hypot(y, 0) - p.PILOT_D / 2 > 1.5
        assert abs(y) - p.PILOT_D / 2 - p.AMP_COLLAR.bore_d / 2 > 1.5
    depth_available = math.sqrt((p.OD / 2) ** 2 - p.SCREW_XY[0][1] ** 2)
    assert depth_available - p.PILOT_DEPTH >= 1.2          # floor under each pilot hole
    assert p.SCREW_LEN - p.SEAT_Z <= p.PILOT_DEPTH        # the screw does not bottom out in its hole


SMALL_PRINT = 0.3      # JLC3DP's tolerance: the outside may come out this much small on diameter


def test_plastic_round_the_thread_the_screws_cut():
    # More than 1.5 mm (JLC3DP's rule round screws) wherever a screw cuts thread: from the relieved
    # mouth down to the screw's tip. Thinnest towards the round outside at the tip's depth, and
    # towards the cable bore.
    radius = (p.OD - SMALL_PRINT) / 2
    tip_depth = p.SCREW_LEN - p.SEAT_Z
    for x, y in p.SCREW_XY:
        assert radius - math.hypot(abs(y) + p.PILOT_D / 2, tip_depth) > 1.5
        collar = p.TRIGGER_COLLAR if x < 0 else p.AMP_COLLAR
        assert abs(y) - p.PILOT_D / 2 - collar.bore_d / 2 > 1.5


def test_walls_round_the_rest_of_each_screw_bore():
    # At least 1.2 mm (JLC3DP's minimum wall) round the parts of each bore that carry no thread:
    # the pilot hole below the screw's tip, its relieved mouth, the clearance hole, the head recess.
    radius = (p.OD - SMALL_PRINT) / 2
    for _, y in p.SCREW_XY:
        assert radius - math.hypot(abs(y) + p.PILOT_D / 2, p.PILOT_DEPTH) >= 1.2      # bottom of the pilot hole
        assert radius - math.hypot(abs(y) + p.CBORE_D / 2, p.SEAT_Z) >= 1.2           # beside the head, at its seat
        assert abs(y) - p.PILOT_RELIEF_D / 2 - p.AMP_COLLAR.bore_d / 2 >= 1.2         # mouth to the cable bore
        assert abs(y) - p.CLEAR_D / 2 - p.AMP_COLLAR.bore_d / 2 >= 1.2                # clearance hole to the cable bore
        assert math.hypot(abs(y) - p.CBORE_D / 2, p.SEAT_Z) - p.AMP_COLLAR.bore_d / 2 >= 1.2   # head recess to the cable bore
    assert (p.COLLAR_L - p.CBORE_D) / 2 >= 1.2 - 1e-9      # head recess to the shell's end and to the chamber


def test_screws_cannot_bottom_out():
    # The seat and the hole's depth may each be 0.3 mm out, and a blind hole can keep powder at the
    # bottom: leave 1 mm under the screw's tip.
    assert p.PILOT_DEPTH - (p.SCREW_LEN - p.SEAT_Z) >= 1.0


def test_free_core_length_puts_each_jacket_end_in_its_collar():
    # docs tell the builder to leave FREE_CORE of each core free beyond the jacket. Worked from the
    # wire's path: jacket end -> over the board's end -> down the strain-relief hole -> 3 mm along the
    # underside -> up through the pad. The fixed part of that path is about 7.9 mm (an estimate).
    fixed, hole_from_end = 7.9, 1.85
    for collar in p.COLLARS:
        board_end = 0.0 if collar.x_outer < 0 else p.BOARD_L
        inner_rib_edge = min(abs(edge - board_end) for span in collar.rib_spans() for edge in span)
        across = max(abs(y) for x, y in p.WIRE_PADS_XY if abs(x - board_end) < 10)
        def jacket_end(core):            # how far the jacket's end is from the board's end, wire taut
            return math.sqrt(max((core - fixed) ** 2 - across ** 2, 0.0)) - hole_from_end
        assert jacket_end(p.FREE_CORE) <= inner_rib_edge - 0.5          # the jacket reaches past both ribs
        assert jacket_end(p.FREE_CORE - p.FREE_CORE_TOL) >= 2.0         # short cores still reach, with room to fan out
        # long cores bow in the chamber: no more than 3 mm of each has to be taken up that way
        assert jacket_end(p.FREE_CORE + p.FREE_CORE_TOL) - (inner_rib_edge - 0.5) <= 3.0


def test_room_for_the_tallest_part_and_the_wires():
    assert p.TOP_ROOM - 1.75 >= 0.3 + 0.3                  # SOIC-8, clearance, print tolerance
    assert p.UNDER_ROOM - max(c.insulation_dia_max for c in cables.CABLES) >= 0.3 + 0.3


def test_a_screwdriver_reaches_the_screws():
    # A PZ1 driver has a 4.5 mm round blade (Wera 355 PZ 1 x 80), and it goes into the counterbore
    # above the head. The counterbore may print 0.3 mm small; leave 0.3 mm on top of that.
    assert p.DRIVER_BLADE_D == 4.5
    assert p.CBORE_D - 0.3 >= p.DRIVER_BLADE_D + 0.3
    assert p.SCREW_HEAD_D >= 3.9 and p.SCREW_HEAD_H >= 1.5      # the named screw's head (docs/enclosure.md)
    assert p.CLEAR_D - 0.3 > p.SCREW_THREAD                     # the thread passes the upper half freely


def test_pilot_holes_follow_the_screw_suppliers_guidance():
    # Westfield's data sheet for this screw: hole 0.75 x d in PA 6; thread engagement at least 2 x d;
    # the hole's mouth relieved to the thread's outside diameter so the plastic there cannot crack or lift.
    recommended = 0.75 * p.SCREW_THREAD
    assert p.PILOT_D - 0.3 <= recommended <= p.PILOT_D          # within what a 0.3 mm-small print gives
    assert p.PILOT_RELIEF_D >= p.SCREW_THREAD + 0.2 - 1e-9 and 0.3 <= p.PILOT_RELIEF_DEPTH <= 1.0
    engaged = (p.SCREW_LEN - p.SEAT_Z) - p.PILOT_RELIEF_DEPTH
    assert engaged >= 2 * p.SCREW_THREAD - 1e-9
