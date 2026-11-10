import pathlib

import pcbnew

LIB = str(pathlib.Path("hardware/lib/dongle.pretty").resolve())
STOCK = "/usr/share/kicad/footprints/Connector.pretty"
mm = pcbnew.ToMM


def load(name):
    fp = pcbnew.FootprintLoad(LIB, name)
    assert fp is not None, f"footprint {name} not found in {LIB}"
    return fp


def test_wire_pad_geometry():
    for n, name in ((2, "WirePads_1x02_Strain"), (3, "WirePads_1x03_Strain")):
        fp = load(name)
        plated = sorted((p for p in fp.Pads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH),
                        key=lambda p: p.GetNumber())
        holes = [p for p in fp.Pads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH]
        assert [p.GetNumber() for p in plated] == [str(i) for i in range(1, n + 1)]
        assert len(holes) == n
        for i, p in enumerate(plated):
            assert round(mm(p.GetDrillSize().x), 2) == 1.0 and round(mm(p.GetSize().x), 2) == 1.8
            assert round(mm(p.GetPosition().y - plated[0].GetPosition().y), 2) == round(i * 2.54, 2)
        for h in holes:
            assert round(mm(h.GetDrillSize().x), 2) == 1.5
            assert round(mm(h.GetPosition().x - plated[0].GetPosition().x), 2) == -3.0
        assert sorted(round(mm(h.GetPosition().y - plated[0].GetPosition().y), 2) for h in holes) == \
            [round(i * 2.54, 2) for i in range(n)]


def test_wire_pads_are_not_placed_by_the_assembler():
    for name in ("WirePads_1x02_Strain", "WirePads_1x03_Strain", "TC2030-MCP-NL"):
        attrs = load(name).GetAttributes()
        assert attrs & pcbnew.FP_EXCLUDE_FROM_POS_FILES and attrs & pcbnew.FP_EXCLUDE_FROM_BOM, name


def test_tc2030_pad_positions():
    stock = pcbnew.FootprintLoad(STOCK, "Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical")
    ours = load("TC2030-MCP-NL")

    def copper(fp):
        return sorted((mm(p.GetPosition().x), mm(p.GetPosition().y)) for p in fp.Pads() if p.GetNumber())

    assert copper(ours) == copper(stock)  # same land pattern
    assert sorted(p.GetNumber() for p in ours.Pads() if p.GetNumber()) == list("123456")
    # MCP_PAD_XY in gen_footprints is the table recorded in hardware/lib/README.md
    from hardware.design.gen_footprints import MCP_PAD_XY
    for p in ours.Pads():
        if p.GetNumber():
            assert MCP_PAD_XY[p.GetNumber()] == (round(mm(p.GetPosition().x), 3), round(mm(p.GetPosition().y), 3))


def test_tc2030_alignment_holes_and_no_paste():
    ours = load("TC2030-MCP-NL")
    holes = sorted((round(mm(p.GetPosition().x), 3), round(mm(p.GetPosition().y), 3))
                   for p in ours.Pads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH)
    assert holes == [(-2.54, 0.0), (2.54, -1.016), (2.54, 1.016)]
    for p in ours.Pads():
        if p.GetNumber():
            assert not p.GetLayerSet().Contains(pcbnew.F_Paste), "contact pads must have no solder paste"
