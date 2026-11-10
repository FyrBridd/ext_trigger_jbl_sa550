import csv
import pathlib
import zipfile

import pcbnew
import pytest

from hardware.design import circuit as c
from hardware.design import export_fab

FAB = pathlib.Path("hardware/fab")
PCB = "hardware/dongle/dongle.kicad_pcb"


@pytest.fixture(scope="module", autouse=True)
def exported():
    export_fab.main()


def rows(name):
    with (FAB / name).open(newline="") as f:
        return list(csv.DictReader(f))


def test_bom_matches_circuit():
    bom = rows("bom.csv")
    assert list(bom[0]) == ["Comment", "Designator", "Footprint", "LCSC Part #"]
    got = {r["LCSC Part #"]: set(r["Designator"].split(",")) for r in bom}
    want = {}
    for ref, p in c.PARTS.items():
        if p.assemble:
            want.setdefault(p.lcsc, set()).add(ref)
    assert got == want


def test_bom_comment_is_the_part_value():
    for r in rows("bom.csv"):
        refs = r["Designator"].split(",")
        assert {c.PARTS[ref].value for ref in refs} == {r["Comment"]}


def test_cpl_lists_exactly_the_assembled_parts():
    cpl = rows("cpl.csv")
    assert list(cpl[0]) == ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]
    assert {r["Designator"] for r in cpl} == {r for r, p in c.PARTS.items() if p.assemble}
    assert {r["Layer"] for r in cpl} == {"Top"}


def test_cpl_positions_match_the_board():
    board = pcbnew.LoadBoard(PCB)
    for r in rows("cpl.csv"):
        fp = board.FindFootprintByReference(r["Designator"])
        assert abs(float(r["Mid X"].rstrip("m")) - pcbnew.ToMM(fp.GetPosition().x)) < 0.01, r["Designator"]
        # KiCad's placement files, like its Gerbers, count Y upwards
        assert abs(float(r["Mid Y"].rstrip("m")) + pcbnew.ToMM(fp.GetPosition().y)) < 0.01, r["Designator"]


def test_cpl_rotations():
    board = pcbnew.LoadBoard(PCB)
    cpl = {r["Designator"]: float(r["Rotation"]) for r in rows("cpl.csv")}
    for ref, offset in (("U1", 180), ("U2", 270), ("U3", 270), ("R1", 0), ("D1", 0)):
        kicad_rot = board.FindFootprintByReference(ref).GetOrientationDegrees()
        assert cpl[ref] == (kicad_rot + offset) % 360, ref


def test_gerber_zip_has_all_layers():
    names = " ".join(zipfile.ZipFile(FAB / "gerbers.zip").namelist())
    for token in ("F_Cu", "B_Cu", "F_Mask", "B_Mask", "F_Paste", "F_Silkscreen", "B_Silkscreen",
                  "Edge_Cuts", "PTH.drl", "NPTH.drl"):
        assert token in names, token


def test_step_written():
    data = (FAB / "dongle.step").read_bytes()
    assert data.startswith(b"ISO-10303-21") and len(data) > 20_000


def test_board_pdf_has_three_pages():
    data = (FAB / "board.pdf").read_bytes()
    assert data.startswith(b"%PDF")
    import subprocess
    info = subprocess.run(["pdfinfo", str(FAB / "board.pdf")], capture_output=True, text=True, check=True).stdout
    assert "Pages:           3" in info


def test_renders_written():
    for name in ("board-top.png", "board-bottom.png", "schematic.pdf"):
        assert (FAB / name).stat().st_size > 10_000, name
