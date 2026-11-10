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
            if pad.GetNumber() and pad.GetNetname() and not pad.GetNetname().startswith("unconnected-"):
                got.setdefault(pad.GetNetname(), set()).add((fp.GetReference(), pad.GetNumber()))
    # board nets carry KiCad's leading "/" so that they match the schematic's names
    assert got == {"/" + n: set(p) for n, p in c.NETS.items()}


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


# --- routing -----------------------------------------------------------------

WIDE_NETS = {"/TRIG_IN", "/TRIG_R", "/VIN", "/+3V3", "/GND"}


def test_drc_clean_with_schematic_parity(board):
    r = kicad.drc(PCB, parity=True)
    assert [(v["type"], v["description"]) for v in r["violations"] if v["severity"] == "error"] == []
    assert r["unconnected_items"] == []
    assert r["schematic_parity"] == []


def test_drc_warnings_are_only_allowed_kinds(board):
    allowed = {"silk_overlap", "silk_over_copper", "lib_footprint_mismatch", "lib_footprint_issues"}
    assert {v["type"] for v in kicad.drc(PCB)["violations"] if v["severity"] == "warning"} <= allowed


def test_power_tracks_are_wide(board):
    for t in board.GetTracks():
        if t.GetClass() == "PCB_TRACK" and t.GetNetname() in WIDE_NETS:
            assert mm(t.GetWidth()) >= 0.4, t.GetNetname()


def test_signal_tracks_are_at_least_quarter_mm(board):
    tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
    assert tracks, "board has no tracks"
    assert all(mm(t.GetWidth()) >= 0.25 for t in tracks)


def test_no_vias_in_programming_footprint(board):
    j3 = board.FindFootprintByReference("J3").GetBoundingBox(False)
    assert not any(t.GetClass() == "PCB_VIA" and j3.Contains(t.GetPosition()) for t in board.GetTracks())


def test_ground_pour_on_both_layers(board):
    layers = set()
    for z in board.Zones():
        if not z.GetIsRuleArea() and z.GetNetname() == "/GND":
            layers |= {layer for layer in (pcbnew.F_Cu, pcbnew.B_Cu) if z.IsOnLayer(layer)}
    assert layers == {pcbnew.F_Cu, pcbnew.B_Cu}


def test_tag_connect_pads_keep_their_clearance(board):
    """Tag-Connect: no other copper within 0.020 in (0.51 mm) of a contact pad, and
    nothing between the two rows of pads. Checked on the top copper layer."""
    j3 = board.FindFootprintByReference("J3")
    pads = [p for p in j3.Pads() if p.GetNumber()]
    xs = sorted({p.GetPosition().x for p in pads})
    ys = [p.GetPosition().y for p in pads]
    between = pcbnew.BOX2I(pcbnew.VECTOR2I(xs[0] + pcbnew.FromMM(0.4), min(ys)),
                           pcbnew.VECTOR2I(xs[-1] - xs[0] - pcbnew.FromMM(0.8), max(ys) - min(ys)))
    for t in board.GetTracks():
        if t.GetClass() != "PCB_TRACK" or t.GetLayer() != pcbnew.F_Cu:
            continue
        assert not between.Intersects(t.GetBoundingBox()), f"{t.GetNetname()} track between the pad rows"
        for p in pads:
            if p.GetNetname() == t.GetNetname() and p.GetNetname():
                continue
            gap = _segment_point_distance(t.GetStart(), t.GetEnd(), p.GetPosition())
            gap -= t.GetWidth() / 2 + p.GetSize().x / 2
            assert mm(gap) >= 0.5, f"{t.GetNetname()} track {mm(gap):.2f} mm from J3 pad {p.GetNumber()}"


def _segment_point_distance(a, b, p) -> float:
    ax, ay, bx, by, px, py = a.x, a.y, b.x, b.y, p.x, p.y
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    cx, cy = ax + t * dx, ay + t * dy
    return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5
