import math

from enclosure import params as p
from hardware.design import cables


def test_overall_size():
    assert p.OD == 20.0
    assert math.isclose(p.X_MAX - p.X_MIN, 71.6)
    assert math.isclose(p.X_MIN, -(p.GAP + p.CHAMBER_L + p.COLLAR_L))


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
    assert math.isclose(p.TRIGGER_COLLAR.x_inner, -6.3) and math.isclose(p.AMP_COLLAR.x_inner, 51.3)


def test_ribs_sit_either_side_of_the_screws():
    assert [tuple(round(v, 3) for v in span) for span in p.TRIGGER_COLLAR.rib_spans()] == [(-12.3, -11.3), (-9.3, -8.3)]
    assert [tuple(round(v, 3) for v in span) for span in p.AMP_COLLAR.rib_spans()] == [(53.3, 54.3), (56.3, 57.3)]
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


def test_plastic_all_round_every_screw_bore():
    # The wall is thinnest where a bore's far end comes nearest the round outside: at the bottom
    # outer corner of a pilot hole, and beside the screw head at the level of its seat.
    radius = (p.OD - 0.3) / 2                              # the print may come out 0.3 mm small
    for _, y in p.SCREW_XY:
        assert radius - math.hypot(abs(y) + p.PILOT_D / 2, p.PILOT_DEPTH) > 1.5
        assert radius - math.hypot(abs(y) + p.CBORE_D / 2, p.SEAT_Z) > 1.5
        assert abs(y) - p.CLEAR_D / 2 - p.AMP_COLLAR.bore_d / 2 >= 1.2     # clearance hole to the cable bore
    assert (p.COLLAR_L - p.CBORE_D) / 2 >= 1.2 - 1e-9      # counterbore to the shell's end and to the chamber


def test_room_for_the_tallest_part_and_the_wires():
    assert p.TOP_ROOM - 1.75 >= 0.3 + 0.3                  # SOIC-8, clearance, print tolerance
    assert p.UNDER_ROOM - max(c.insulation_dia_max for c in cables.CABLES) >= 0.3 + 0.3
