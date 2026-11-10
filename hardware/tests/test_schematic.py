import pathlib

import pytest

from hardware.design import circuit as c
from hardware.design import gen_sch, kicad

SCH = pathlib.Path("hardware/dongle/dongle.kicad_sch")


@pytest.fixture(scope="module", autouse=True)
def generated():
    gen_sch.main()


def test_erc_has_no_errors():
    errors = [v for v in kicad.erc(SCH) if v["severity"] == "error"]
    assert errors == []


def test_erc_warnings_are_only_allowed_kinds():
    allowed = {"lib_symbol_issues", "lib_symbol_mismatch", "footprint_link_issues"}
    assert {v["type"] for v in kicad.erc(SCH) if v["severity"] == "warning"} <= allowed


def test_exported_netlist_equals_circuit():
    exported = kicad.export_netlist(SCH)
    expected = {name: set(pins) for name, pins in c.NETS.items()}
    named = {n.lstrip("/"): pins for n, pins in exported.items() if not n.startswith("unconnected-")}
    assert named == expected


def test_unconnected_pins_are_exactly_the_declared_ones():
    exported = kicad.export_netlist(SCH)
    floating = {pin for n, pins in exported.items() if n.startswith("unconnected-") for pin in pins}
    assert floating == set(c.NO_CONNECT)


def test_every_part_has_footprint_and_lcsc_field():
    fields = kicad.symbol_fields(SCH)  # {ref: {"Footprint": ..., "LCSC": ..., "Value": ...}}
    assert set(fields) == set(c.PARTS)
    for ref, part in c.PARTS.items():
        assert fields[ref]["Footprint"] == part.footprint
        assert fields[ref]["Value"] == part.value
        assert fields[ref].get("LCSC", "") == (part.lcsc or "")


def test_symbol_uuids_are_stable():
    assert gen_sch.symbol_uuid("U2") == gen_sch.symbol_uuid("U2")
    assert gen_sch.symbol_uuid("U2") != gen_sch.symbol_uuid("U3")


def test_pdf_is_written():
    out = pathlib.Path("hardware/fab/schematic.pdf")
    kicad.export_pdf(SCH, out)
    assert out.read_bytes().startswith(b"%PDF") and out.stat().st_size > 10_000


# --- the drawing itself: a wired schematic, not a list of labelled pins ---------

POWER_NETS_BY_SYMBOL = {"GND", "+3V3"}


def _nodes(kind):
    tree = kicad.parse_sexpr(SCH.read_text())
    return [n for n in tree if isinstance(n, list) and n and n[0] == kind]


def test_each_net_is_drawn_once_with_wires_not_repeated_labels():
    """A net is joined by drawn wires. Its name appears on one label at most; a
    second label of the same name would be a connection the eye cannot follow."""
    import collections
    names = collections.Counter(str(n[1]) for n in _nodes("label"))
    assert names, "no net labels at all"
    assert set(names) == set(c.NETS) - POWER_NETS_BY_SYMBOL
    assert {n: k for n, k in names.items() if k != 1} == {}


def test_ground_and_supply_use_power_symbols():
    values = []
    for sym in _nodes("symbol"):
        props = {str(x[1]): str(x[2]) for x in sym if isinstance(x, list) and x[0] == "property"}
        if props.get("Reference", "").startswith("#PWR"):
            values.append(props["Value"])
    assert set(values) == POWER_NETS_BY_SYMBOL
    assert values.count("GND") >= 10 and values.count("+3V3") >= 5


def test_every_connected_pin_is_reached_by_a_wire():
    ends = set()
    for w in _nodes("wire"):
        pts = next(x for x in w if isinstance(x, list) and x[0] == "pts")
        for xy in pts[1:]:
            ends.add((round(float(xy[1]), 2), round(float(xy[2]), 2)))
    assert len(_nodes("wire")) >= 60
    power_pins = set()   # a power symbol or test pad may sit directly on a part's pin
    for ref, pins in gen_sch.pin_positions().items():
        if ref.startswith("#") or ref.startswith("TP"):
            power_pins |= {(round(x, 2), round(y, 2)) for x, y in pins.values()}
    for net, pins in c.NETS.items():
        for ref, number in pins:
            x, y = gen_sch.pin_positions()[ref][number]
            at = (round(x, 2), round(y, 2))
            assert at in ends or at in power_pins, f"{ref}.{number} ({net}) has no wire"
