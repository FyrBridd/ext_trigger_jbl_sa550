"""Generate the KiCad board from circuit.py and layout.py.

Run as:  python -m hardware.design.gen_pcb
"""
import pathlib

import pcbnew

from hardware.design import circuit as c
from hardware.design import gen_sch, layout

PROJECT_DIR = pathlib.Path(__file__).resolve().parents[1] / "dongle"
PCB_PATH = PROJECT_DIR / "dongle.kicad_pcb"
PROJECT_LIB = pathlib.Path(__file__).resolve().parents[1] / "lib" / "dongle.pretty"
STOCK_LIBS = pathlib.Path("/usr/share/kicad/footprints")

NOT_ASSEMBLED = pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM

mm = pcbnew.FromMM


def pt(x: float, y: float) -> pcbnew.VECTOR2I:
    """A board position (mm from the board's top-left corner) as a KiCad point."""
    return pcbnew.VECTOR2I(mm(layout.ORIGIN[0] + x), mm(layout.ORIGIN[1] + y))


def _load_footprint(lib_id: str) -> pcbnew.FOOTPRINT:
    nickname, name = lib_id.split(":")
    lib_dir = PROJECT_LIB if nickname == "dongle" else STOCK_LIBS / f"{nickname}.pretty"
    fp = pcbnew.FootprintLoad(str(lib_dir), name)
    if fp is None:
        raise RuntimeError(f"footprint {lib_id} not found in {lib_dir}")
    fp.SetFPID(pcbnew.LIB_ID(nickname, name))
    return fp


def _add_outline(board) -> None:
    corners = [(0, 0), (layout.LENGTH, 0), (layout.LENGTH, layout.WIDTH), (0, layout.WIDTH)]
    for (x1, y1), (x2, y2) in zip(corners, corners[1:] + corners[:1]):
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(pt(x1, y1))
        seg.SetEnd(pt(x2, y2))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(mm(0.1))
        board.Add(seg)


def _set_design_rules(board) -> None:
    rules = board.GetDesignSettings()
    rules.m_MinClearance = mm(0.15)
    rules.m_TrackMinWidth = mm(0.15)
    rules.m_ViasMinSize = mm(0.6)
    rules.m_MinThroughDrill = mm(0.3)
    rules.m_CopperEdgeClearance = mm(0.3)
    rules.m_HoleToHoleMin = mm(0.5)


def _add_parts(board) -> None:
    nets = {}
    for name in c.NETS:
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
        nets[name] = net
    net_of_pin = {pin: nets[name] for name, pins in c.NETS.items() for pin in pins}

    for ref, part in c.PARTS.items():
        x, y, rotation = layout.PLACEMENTS[ref]
        fp = _load_footprint(part.footprint)
        fp.SetReference(ref)
        fp.SetValue(part.value)
        fp.SetPath(pcbnew.KIID_PATH("/" + gen_sch.symbol_uuid(ref)))
        if not part.assemble:
            fp.SetAttributes(fp.GetAttributes() | NOT_ASSEMBLED)
        board.Add(fp)
        fp.SetPosition(pt(x, y))
        if ref in layout.BOTTOM:
            fp.Flip(pt(x, y), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetOrientationDegrees(rotation)
        for pad in fp.Pads():
            net = net_of_pin.get((ref, pad.GetNumber()))
            if net is not None:
                pad.SetNet(net)


def _text(board, text, x, y, side) -> None:
    item = pcbnew.PCB_TEXT(board)
    item.SetText(text)
    item.SetPosition(pt(x, y))
    item.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(1.0)))
    item.SetTextThickness(mm(0.15))
    item.SetLayer(pcbnew.F_SilkS if side == "top" else pcbnew.B_SilkS)
    item.SetMirrored(side == "bottom")
    board.Add(item)


def _add_silkscreen(board) -> None:
    # Reference designators do not fit between the parts; they go on the
    # fabrication layers, which appear in the board drawing but are not printed.
    for fp in board.GetFootprints():
        on_top = fp.GetLayer() == pcbnew.F_Cu
        fp.Reference().SetLayer(pcbnew.F_Fab if on_top else pcbnew.B_Fab)
        fp.Reference().SetTextSize(pcbnew.VECTOR2I(mm(0.6), mm(0.6)))
        fp.Reference().SetTextThickness(mm(0.1))
        fp.Reference().SetPosition(fp.GetPosition())
        fp.Value().SetVisible(False)
    for text, x, y, side in layout.SILK:
        _text(board, text, x, y, side)
    dx, dy = layout.TEST_PAD_LABEL_OFFSET
    for ref, label in c.TEST_PADS.items():
        x, y, _ = layout.PLACEMENTS[ref]
        _text(board, label, x + dx, y + dy, "bottom")


def _add_tracks(board) -> None:
    layers = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}
    for net_name, layer, width, points in layout.TRACKS:
        net = board.FindNet(net_name)
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            track = pcbnew.PCB_TRACK(board)
            track.SetStart(pt(x1, y1))
            track.SetEnd(pt(x2, y2))
            track.SetWidth(mm(width))
            track.SetLayer(layers[layer])
            track.SetNet(net)
            board.Add(track)
    for net_name, x, y in layout.VIAS:
        via = pcbnew.PCB_VIA(board)
        via.SetPosition(pt(x, y))
        via.SetWidth(pcbnew.F_Cu, mm(0.6)) if _via_width_takes_layer() else via.SetWidth(mm(0.6))
        via.SetDrill(mm(0.3))
        via.SetNet(board.FindNet(net_name))
        board.Add(via)


def _via_width_takes_layer() -> bool:
    try:
        pcbnew.PCB_VIA(None).SetWidth(pcbnew.F_Cu, 1)
        return True
    except TypeError:
        return False


def build() -> pcbnew.BOARD:
    board = pcbnew.NewBoard(str(PCB_PATH))
    _set_design_rules(board)
    _add_outline(board)
    _add_parts(board)
    _add_silkscreen(board)
    _add_tracks(board)
    return board


def main() -> None:
    gen_sch.write_project_files()
    if PCB_PATH.exists():
        PCB_PATH.unlink()
    board = build()
    pcbnew.SaveBoard(str(PCB_PATH), board)


if __name__ == "__main__":
    main()
