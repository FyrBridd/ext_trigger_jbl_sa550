from hardware.design import circuit as c

SPEC_LCSC = {
    "U1": "C14289", "U2": "C1337190", "U3": "C13482",
    "D1": "C8598", "D2": "C19077510", "D3": "C2286", "D4": "C8598",
    "C1": "C15850", "C2": "C15850",
    "R1": "C22775", "R2": "C21190", "R3": "C25804",
    **{f"C{i}": "C14663" for i in range(3, 9)},
}


def all_pins():
    return [p for pins in c.NETS.values() for p in pins]


def test_lcsc_numbers_match_spec():
    assert {r: p.lcsc for r, p in c.PARTS.items() if p.assemble} == SPEC_LCSC


def test_unassembled_parts_have_no_lcsc():
    assert all(p.lcsc is None for p in c.PARTS.values() if not p.assemble)


def test_no_pin_in_two_nets():
    pins = all_pins() + c.NO_CONNECT
    assert len(pins) == len(set(pins))


def test_every_net_has_two_or_more_pins():
    assert all(len(pins) >= 2 for pins in c.NETS.values())


def test_every_pin_ref_is_a_part():
    assert {r for r, _ in all_pins() + c.NO_CONNECT} <= set(c.PARTS)


def test_ic_pins_fully_accounted_for():
    for ref, n in {"U1": 3, "U2": 8, "U3": 16, "J1": 2, "J2": 3, "J3": 6}.items():
        used = {pin for r, pin in all_pins() + c.NO_CONNECT if r == ref}
        assert used == {str(i) for i in range(1, n + 1)}, ref


def test_two_pin_parts_fully_connected():
    two_pin = [r for r in c.PARTS if r[0] in "RCD"]
    for ref in two_pin:
        used = {pin for r, pin in all_pins() if r == ref}
        assert used == {"1", "2"}, ref


def test_updi_only_reaches_programming_pad_and_test_pad():
    assert sorted(c.NETS["UPDI"]) == [("J3", "4"), ("TP6", "1"), ("U2", "6")]


def test_programming_pads_1_5_6_unconnected():
    assert {("J3", "1"), ("J3", "5"), ("J3", "6")} <= set(c.NO_CONNECT)


def test_pin_functions():
    f = c.PIN_FUNCTIONS
    assert f[("U1", "1")] == "GND" and f[("U1", "2")] == "VIN" and f[("U1", "3")] == "VOUT"
    assert f[("U2", "1")] == "VDD" and f[("U2", "8")] == "GND"
    assert f[("U2", "2")] == "PA6/TXD" and f[("U2", "3")] == "PA7/RXD" and f[("U2", "6")] == "PA0/UPDI"
    assert f[("U3", "11")] == "T1IN" and f[("U3", "14")] == "T1OUT"
    assert f[("U3", "13")] == "R1IN" and f[("U3", "12")] == "R1OUT"
    assert f[("U3", "16")] == "VCC" and f[("U3", "15")] == "GND" and f[("U3", "10")] == "T2IN"


def net_of(ref, pin):
    return next(name for name, pins in c.NETS.items() if (ref, pin) in pins)


def test_reversed_trigger_wires_have_no_path_to_anything():
    """Each trigger wire reaches the rest of the circuit only through a diode that
    blocks when the wires are swapped: D1 in the supply leg, D4 in the return leg.
    In particular the return wire is not tied straight to ground, which is shared
    with the amp and, through the audio cable, with the WiiM."""
    assert net_of("J1", "2") != "GND"
    # return leg: wire -> D4 cathode; D4 anode -> ground
    assert sorted(c.NETS[net_of("J1", "2")]) == [("D4", "1"), ("J1", "2")]
    assert net_of("D4", "2") == "GND"
    # supply leg: wire -> R1 -> D1 anode; D1 cathode -> the regulator's input
    assert sorted(c.NETS[net_of("J1", "1")]) == [("J1", "1"), ("R1", "1")]
    assert net_of("R1", "2") == net_of("D1", "2") and net_of("D1", "1") == "VIN"
    for diode in ("D1", "D4"):
        assert c.PARTS[diode].value == "B5819W" and c.PARTS[diode].symbol == "Device:D_Schottky"
