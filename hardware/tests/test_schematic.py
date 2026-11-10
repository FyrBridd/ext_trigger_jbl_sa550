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
