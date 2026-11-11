import math

from enclosure import keepouts as k, params as p


def bbox(shape):
    b = shape.val().BoundingBox()
    return (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)


def close(a, b):
    return len(a) == len(b) and all(math.isclose(x, y, abs_tol=1e-6) for x, y in zip(a, b))


def test_board_sits_where_the_parameters_say():
    assert close(bbox(k.board()), (0, 45, -6.5, 6.5, -1.15, 0.45))
    assert math.isclose(k.volume(k.board()), 45 * 13 * 1.6)


def test_parts_slab_and_its_clearance():
    assert close(bbox(k.parts()), (1, 44, -5.5, 5.5, 0.45, 2.2))
    assert close(bbox(k.parts(0.3)), (0.7, 44.3, -5.8, 5.8, 0.45, 2.5))


def test_underside_slabs_are_under_the_wire_pads():
    assert close(bbox(k.underside()), (0, 45, -4.5, 4.5, -2.35, -1.15))
    assert math.isclose(k.volume(k.underside()), 2 * 7 * 9 * 1.2)
    assert close(bbox(k.underside(0.3)), (-0.3, 45.3, -4.8, 4.8, -2.65, -1.15))
    for x, y in p.WIRE_PADS_XY:
        assert (0 <= x <= 7 or 38 <= x <= 45) and abs(y) <= 4.5


def test_cables_and_overlap():
    trigger = k.cable(p.TRIGGER_COLLAR)
    assert close(bbox(trigger)[:2], (p.X_MIN - 2, p.TRIGGER_COLLAR.x_inner))
    assert math.isclose(bbox(trigger)[3] - bbox(trigger)[2], 3.7, abs_tol=1e-6)
    amp = k.cable(p.AMP_COLLAR, 4.0)
    assert close(bbox(amp)[:2], (p.AMP_COLLAR.x_inner, p.X_MAX + 2))
    assert math.isclose(bbox(amp)[5] - bbox(amp)[4], 4.0, abs_tol=1e-6)
    assert k.overlap(k.board(), k.parts()) == 0.0                    # they only touch
    assert math.isclose(k.overlap(k.board(), k.board()), 45 * 13 * 1.6)


def test_wire_room_fills_each_chamber():
    assert close(bbox(k.wire_room(p.TRIGGER_COLLAR)), (-6.1, -0.5, -5, 5, -5, 5))
    assert close(bbox(k.wire_room(p.AMP_COLLAR)), (45.5, 51.1, -5, 5, -5, 5))


def test_led_and_programming_pins_are_on_the_right_side():
    b = bbox(k.led_sightline(1.6))
    assert math.isclose((b[0] + b[1]) / 2, 27.98) and math.isclose((b[2] + b[3]) / 2, 4.7)
    assert math.isclose(b[4], 0.45) and math.isclose(b[5], 12)
    pins = bbox(k.programming_pins())
    assert math.isclose(pins[4], -1.15 - 2.2) and pins[0] > 19 and pins[1] < 24
    assert k.programming_pins().solids().size() == 3


def test_screw_rod():
    rod = bbox(k.screw(p.SCREW_XY[0], 2.0, -3, 4))
    assert close(rod, (-10.8, -8.8, 4.2, 6.2, -3, 4))
