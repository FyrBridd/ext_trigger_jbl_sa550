import pathlib

import pcbnew
import pytest

from hardware.design import circuit as c
from hardware.design import gen_pcb, kicad

PCB = pathlib.Path("hardware/dongle/dongle.kicad_pcb")
mm = pcbnew.ToMM


@pytest.fixture(scope="module")
def board():
    gen_pcb.main()
    return pcbnew.LoadBoard(str(PCB))


def outline(board):
    """The board outline as (left, top, right, bottom) in KiCad units, from the
    Edge.Cuts line ends (the bounding box would add the lines' own width)."""
    xs, ys = [], []
    for d in board.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts:
            for p in (d.GetStart(), d.GetEnd()):
                xs.append(p.x)
                ys.append(p.y)
    return min(xs), min(ys), max(xs), max(ys)


def test_outline_within_limits(board):
    left, top, right, bottom = outline(board)
    w, length = sorted((mm(right - left), mm(bottom - top)))
    assert 10.0 <= w <= 14.0 and 10.0 <= length <= 45.0


def test_all_parts_present_with_right_footprint(board):
    got = {fp.GetReference(): str(fp.GetFPID().GetUniStringLibId()) for fp in board.GetFootprints()}
    assert got == {r: p.footprint for r, p in c.PARTS.items()}


def test_assembled_parts_on_top(board):
    for fp in board.GetFootprints():
        if c.PARTS[fp.GetReference()].assemble:
            assert fp.GetLayer() == pcbnew.F_Cu, fp.GetReference()


def test_only_test_pads_are_on_the_bottom(board):
    bottom = {fp.GetReference() for fp in board.GetFootprints() if fp.GetLayer() == pcbnew.B_Cu}
    assert bottom == set(c.TEST_PADS)


def test_nothing_behind_programming_footprint(board):
    j3 = board.FindFootprintByReference("J3").GetBoundingBox(False)
    for fp in board.GetFootprints():
        if fp.GetLayer() == pcbnew.B_Cu:
            assert not fp.GetBoundingBox(False).Intersects(j3), fp.GetReference()


def test_test_pads_clear_of_the_wire_runs_under_the_board_ends(board):
    # wires run along the underside between each strain-relief hole and its pad
    left, _, right, _ = outline(board)
    for fp in board.GetFootprints():
        if fp.GetLayer() == pcbnew.B_Cu:
            x = fp.GetPosition().x
            assert mm(x - left) > 6.5 and mm(right - x) > 6.5, fp.GetReference()


def test_edge_clearance(board):
    left, top, right, bottom = outline(board)
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        box = fp.GetBoundingBox(False)  # pads and body, no text
        margin = 1.0 if c.PARTS[ref].assemble else 0.9  # 0.9: strain holes leave a 1 mm web
        assert mm(box.GetLeft() - left) >= margin, ref
        assert mm(right - box.GetRight()) >= margin, ref
        assert mm(box.GetTop() - top) >= margin, ref
        assert mm(bottom - box.GetBottom()) >= margin, ref


def test_pad_nets_match_circuit(board):
    got = {}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNumber() and pad.GetNetname():
                got.setdefault(pad.GetNetname(), set()).add((fp.GetReference(), pad.GetNumber()))
    assert got == {n: set(p) for n, p in c.NETS.items()}


def test_footprints_are_linked_to_their_symbols(board):
    from hardware.design import gen_sch
    for fp in board.GetFootprints():
        assert fp.GetPath().AsString() == "/" + gen_sch.symbol_uuid(fp.GetReference())
        assert fp.GetValue() == c.PARTS[fp.GetReference()].value


def test_only_assembled_parts_go_in_position_and_bom_files(board):
    for fp in board.GetFootprints():
        excluded = bool(fp.GetAttributes() & pcbnew.FP_EXCLUDE_FROM_POS_FILES)
        assert excluded == (not c.PARTS[fp.GetReference()].assemble), fp.GetReference()


def test_no_courtyard_overlap(board):
    kinds = {v["type"] for v in kicad.drc(PCB)["violations"]}
    assert "courtyards_overlap" not in kinds


def test_strain_holes_are_at_the_board_ends(board):
    left, _, right, _ = outline(board)
    for ref, end in (("J1", left), ("J2", right)):
        fp = board.FindFootprintByReference(ref)
        holes = [p for p in fp.Pads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH]
        plated = [p for p in fp.Pads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH]
        assert max(abs(mm(h.GetPosition().x - end)) for h in holes) < \
            min(abs(mm(p.GetPosition().x - end)) for p in plated), ref


def test_silkscreen_names_every_wire_pad_and_test_pad(board):
    top = {d.GetText() for d in board.GetDrawings() if d.GetClass() == "PCB_TEXT" and d.GetLayer() == pcbnew.F_SilkS}
    bottom = {d.GetText() for d in board.GetDrawings() if d.GetClass() == "PCB_TEXT" and d.GetLayer() == pcbnew.B_SilkS}
    assert {"+", "G", "R", "T"} <= top
    assert {"+12V", "GND", "5 GND", "3 RX", "2 TX"} <= bottom       # DB9 pin each wire goes to
    assert set(c.TEST_PADS.values()) <= bottom
    assert any("r1" in t for t in bottom)


def test_silkscreen_text_is_printable_by_jlcpcb(board):
    for d in board.GetDrawings():
        if d.GetClass() == "PCB_TEXT" and d.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
            assert mm(d.GetTextHeight()) >= 1.0 and mm(d.GetTextThickness()) >= 0.15, d.GetText()
            assert d.IsMirrored() == (d.GetLayer() == pcbnew.B_SilkS), d.GetText()
