"""Generate the KiCad board from circuit.py and layout.py.

Run as:  python -m hardware.design.gen_pcb
"""
import json
import pathlib

import pcbnew

from hardware.design import circuit as c
from hardware.design import gen_sch, kicad, layout

PROJECT_DIR = pathlib.Path(__file__).resolve().parents[1] / "dongle"
PCB_PATH = PROJECT_DIR / "dongle.kicad_pcb"
PROJECT_LIB = pathlib.Path(__file__).resolve().parents[1] / "lib" / "dongle.pretty"
STOCK_LIBS = pathlib.Path("/usr/share/kicad/footprints")

NOT_ASSEMBLED = pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM

mm = pcbnew.FromMM


def net_name(name: str) -> str:
    """The board's name for a circuit net. KiCad puts a "/" in front of nets named
    by labels on the top sheet, and the board must match the schematic exactly."""
    return name if name.startswith("/") else "/" + name


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


def _set_design_rules(board, clearance: float = layout.CLEARANCE) -> None:
    rules = board.GetDesignSettings()
    nets = rules.m_NetSettings
    default = nets.GetDefaultNetclass()
    default.SetClearance(mm(clearance))
    default.SetTrackWidth(mm(layout.TRACK_SIGNAL))
    default.SetViaDiameter(mm(layout.VIA_DIAMETER))
    default.SetViaDrill(mm(layout.VIA_DRILL))
    power = pcbnew.NETCLASS("Power")
    power.SetClearance(mm(clearance))
    power.SetTrackWidth(mm(layout.TRACK_POWER))
    power.SetViaDiameter(mm(layout.VIA_DIAMETER))
    power.SetViaDrill(mm(layout.VIA_DRILL))
    nets.SetNetclass("Power", power)
    for name in layout.POWER_NETS:
        nets.SetNetclassPatternAssignment(net_name(name), "Power")
    rules.m_MinClearance = mm(0.15)
    rules.m_TrackMinWidth = mm(0.15)
    rules.m_ViasMinSize = mm(0.6)
    rules.m_MinThroughDrill = mm(0.3)
    rules.m_CopperEdgeClearance = mm(0.3)
    rules.m_HoleToHoleMin = mm(0.5)


def _add_parts(board) -> None:
    nets = {}
    for name in c.NETS:
        net = pcbnew.NETINFO_ITEM(board, net_name(name))
        board.Add(net)
        nets[name] = net
    net_of_pin = {pin: nets[name] for name, pins in c.NETS.items() for pin in pins}

    # A pin left unconnected on purpose still has a net of its own in KiCad, with a
    # name KiCad makes up. Take those names from the schematic so the board matches.
    for name, pins in kicad.export_netlist(gen_sch.PROJECT_DIR / f"{gen_sch.NAME}.kicad_sch").items():
        if name.startswith("unconnected-"):
            net = pcbnew.NETINFO_ITEM(board, name)
            board.Add(net)
            for pin in pins:
                net_of_pin[pin] = net

    for ref, part in c.PARTS.items():
        x, y, rotation = layout.PLACEMENTS[ref]
        fp = _load_footprint(part.footprint)
        fp.SetReference(ref)
        fp.SetValue(part.value)
        fp.SetPath(pcbnew.KIID_PATH("/" + gen_sch.symbol_uuid(ref)))
        if part.lcsc:
            fp.SetField("LCSC", part.lcsc)
            fp.GetField("LCSC").SetVisible(False)
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


def _polygon_zone(board, corners, layer) -> pcbnew.ZONE:
    zone = pcbnew.ZONE(board)
    zone.SetLayer(layer)
    outline = zone.Outline()
    outline.NewOutline()
    for x, y in corners:
        outline.Append(pt(x, y))
    board.Add(zone)
    return zone


def _rect(x1, y1, x2, y2):
    return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]


def _add_keepouts(board) -> None:
    """Rule areas for the Tag-Connect footprint (see hardware/lib/README.md)."""
    j3 = board.FindFootprintByReference("J3")
    pads = [p for p in j3.Pads() if p.GetNumber()]
    ox, oy = layout.ORIGIN
    xs = sorted({round(pcbnew.ToMM(p.GetPosition().x) - ox, 3) for p in pads})
    ys = sorted({round(pcbnew.ToMM(p.GetPosition().y) - oy, 3) for p in pads})
    r = pcbnew.ToMM(pads[0].GetSize().x) / 2

    # Tag-Connect: nothing between the two rows of contact pads, and no other track
    # within 0.51 mm of a pad. Each pad's own track leaves sideways, away from the
    # other row, through a gap ("channel") in the keep-out.
    halo = r + layout.TAG_CONNECT_PAD_CLEARANCE
    channel = 0.5    # half-height of each pad's escape channel (a 0.4 mm track plus the router's clearance)
    top, bottom = ys[0] - halo, ys[-1] + halo
    areas = [
        _rect(xs[0] + r, top, xs[-1] - r, bottom),           # between the rows
        _rect(xs[0] - r, top, xs[-1] + r, ys[0] - r),         # beyond the first pads
        _rect(xs[0] - r, ys[-1] + r, xs[-1] + r, bottom),     # beyond the last pads
    ]
    edges = [top] + [v for y in ys for v in (y - channel, y + channel)] + [bottom]
    for y1, y2 in zip(edges[::2], edges[1::2]):   # outside each row: teeth between the channels
        areas.append(_rect(xs[0] - halo, y1, xs[0] - r, y2))
        areas.append(_rect(xs[-1] + r, y1, xs[-1] + halo, y2))
    for corners in areas:
        area = _polygon_zone(board, corners, pcbnew.F_Cu)
        area.SetIsRuleArea(True)
        area.SetZoneName("TC2030 pad clearance")
        area.SetDoNotAllowTracks(True)
        area.SetDoNotAllowVias(True)
        area.SetDoNotAllowZoneFills(True)
        area.SetDoNotAllowPads(False)
        area.SetDoNotAllowFootprints(False)

    # no vias anywhere under the footprint: the cable's retaining clip sits behind it
    box = j3.GetBoundingBox(False)
    x1, y1 = pcbnew.ToMM(box.GetLeft()) - ox, pcbnew.ToMM(box.GetTop()) - oy
    x2, y2 = pcbnew.ToMM(box.GetRight()) - ox, pcbnew.ToMM(box.GetBottom()) - oy
    vias = _polygon_zone(board, _rect(x1, y1, x2, y2), pcbnew.F_Cu)
    vias.SetLayerSet(pcbnew.LSET.AllCuMask())
    vias.SetIsRuleArea(True)
    vias.SetZoneName("TC2030 no vias")
    vias.SetDoNotAllowTracks(False)
    vias.SetDoNotAllowVias(True)
    vias.SetDoNotAllowZoneFills(False)
    vias.SetDoNotAllowPads(False)
    vias.SetDoNotAllowFootprints(False)


def _add_pour_keepout(board) -> None:
    """Keep the ground pour the distance Tag-Connect asks for from the contact pads.
    Not given to the autorouter, which would read it as a ban on tracks too."""
    j3 = board.FindFootprintByReference("J3")
    pads = [p for p in j3.Pads() if p.GetNumber()]
    ox, oy = layout.ORIGIN
    xs = sorted({round(pcbnew.ToMM(p.GetPosition().x) - ox, 3) for p in pads})
    ys = sorted({round(pcbnew.ToMM(p.GetPosition().y) - oy, 3) for p in pads})
    r = pcbnew.ToMM(pads[0].GetSize().x) / 2
    c_ = layout.TAG_CONNECT_PAD_CLEARANCE + r
    pour = _polygon_zone(board, _rect(xs[0] - c_, ys[0] - c_, xs[-1] + c_, ys[-1] + c_), pcbnew.F_Cu)
    pour.SetIsRuleArea(True)
    pour.SetZoneName("TC2030 no pour near pads")
    pour.SetDoNotAllowTracks(False)
    pour.SetDoNotAllowVias(False)
    pour.SetDoNotAllowZoneFills(True)
    pour.SetDoNotAllowPads(False)
    pour.SetDoNotAllowFootprints(False)



def _add_ground_pour(board) -> None:
    gnd = board.FindNet(net_name("GND"))
    i = layout.GND_ZONE_INSET
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        zone = _polygon_zone(board, _rect(i, i, layout.LENGTH - i, layout.WIDTH - i), layer)
        zone.SetNet(gnd)
        zone.SetZoneName("GND top" if layer == pcbnew.F_Cu else "GND bottom")
        zone.SetLocalClearance(mm(0.25))
        zone.SetMinThickness(mm(0.2))
        # thermal spokes on the through-hole wire pads so they can be hand-soldered;
        # solid connection to surface-mount pads
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)
        zone.SetThermalReliefGap(mm(0.3))
        zone.SetThermalReliefSpokeWidth(mm(0.4))
        zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    # The pour is filled by kicad-cli after the board is saved (see main): filling
    # from this script ignores holes, tracks and pads.


def _add_drawing_notes(board) -> None:
    """Title block text and the dimensions shown on the board drawing (User.Drawings)."""
    title = board.GetTitleBlock()
    title.SetTitle("WiiM trigger to JBL SA550 RS232 dongle - board")
    title.SetRevision("r1")
    title.SetComment(0, "${VIEW}")   # export_fab sets this per page; main() gives it a default
    title.SetComment(1, "Generated from hardware/design - do not edit by hand")

    def dimension(x1, y1, x2, y2, height):
        dim = pcbnew.PCB_DIM_ALIGNED(board, pcbnew.PCB_DIM_ALIGNED_T)
        dim.SetLayer(pcbnew.Dwgs_User)
        dim.SetStart(pt(x1, y1))
        dim.SetEnd(pt(x2, y2))
        dim.SetHeight(mm(height))
        dim.SetUnits(pcbnew.EDA_UNITS_MM)
        dim.SetPrecision(pcbnew.DIM_PRECISION_X_XX)
        dim.SetLineThickness(mm(0.1))
        dim.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))
        dim.SetTextThickness(mm(0.12))
        dim.Update()
        board.Add(dim)

    dimension(0, 0, layout.LENGTH, 0, -2.5)               # overall length, above the board
    dimension(0, 0, 0, layout.WIDTH, 2.5)                 # overall width, left of the board
    j1x, j2x = layout.PLACEMENTS["J1"][0], layout.PLACEMENTS["J2"][0]
    dimension(0, layout.WIDTH, j1x, layout.WIDTH, 2.0)    # board end to the trigger wire pads
    dimension(j2x, layout.WIDTH, layout.LENGTH, layout.WIDTH, 2.0)   # amplifier wire pads to board end
    j3x, j3y = layout.PLACEMENTS["J3"][:2]
    dimension(0, layout.WIDTH, j3x, layout.WIDTH, 4.5)    # board end to the programming footprint centre
    d3x = layout.PLACEMENTS["D3"][0]
    dimension(0, layout.WIDTH, d3x, layout.WIDTH, 7.0)    # board end to the LED centre

    note = pcbnew.PCB_TEXT(board)
    note.SetText("2 layers, 1.6 mm FR4, parts on top only.\n"
                 "Positions from the top-left corner:\n"
                 "LED (D3) centre %.2f, %.2f mm\n"
                 "programming footprint (J3) centre %.2f, %.2f mm"
                 % (d3x, layout.PLACEMENTS["D3"][1], j3x, j3y))
    note.SetLayer(pcbnew.Dwgs_User)
    note.SetPosition(pt(layout.LENGTH - 10, layout.WIDTH + 6.5))
    note.SetTextSize(pcbnew.VECTOR2I(mm(0.7), mm(0.7)))
    note.SetTextThickness(mm(0.1))
    board.Add(note)


def _add_tracks(board, tracks, vias, locked: bool = False) -> None:
    layers = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}
    for name, layer, width, points in tracks:
        net = board.FindNet(net_name(name))
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            track = pcbnew.PCB_TRACK(board)
            track.SetStart(pt(x1, y1))
            track.SetEnd(pt(x2, y2))
            track.SetWidth(mm(width))
            track.SetLayer(layers[layer])
            track.SetNet(net)
            track.SetLocked(locked)
            board.Add(track)
    for name, x, y in vias:
        via = pcbnew.PCB_VIA(board)
        via.SetPosition(pt(x, y))
        via.SetWidth(pcbnew.F_Cu, mm(layout.VIA_DIAMETER))
        via.SetDrill(mm(layout.VIA_DRILL))
        via.SetNet(board.FindNet(net_name(name)))
        via.SetLocked(locked)
        board.Add(via)


def build(routed: bool = True) -> pcbnew.BOARD:
    """The whole board. With routed=False it stops before tracks and the ground
    pour: that is the board the autorouter is given."""
    board = pcbnew.NewBoard(str(PCB_PATH))
    _set_design_rules(board, layout.CLEARANCE if routed else layout.ROUTING_CLEARANCE)
    _add_outline(board)
    _add_parts(board)
    _add_silkscreen(board)
    _add_drawing_notes(board)
    _add_keepouts(board)
    _add_tracks(board, layout.FIXED_TRACKS, layout.FIXED_VIAS, locked=True)
    if routed:
        _add_tracks(board, layout.ROUTED_TRACKS + layout.GND_TRACKS, layout.ROUTED_VIAS + layout.GND_VIAS)
        _add_pour_keepout(board)
        _add_ground_pour(board)
    return board


def main() -> None:
    gen_sch.main()   # the board takes its unconnected-pin net names from the schematic
    if PCB_PATH.exists():
        PCB_PATH.unlink()
    board = build()
    pcbnew.SaveBoard(str(PCB_PATH), board)
    # default value for the title block's ${VIEW}, kept in the project file
    pro = PROJECT_DIR / f"{gen_sch.NAME}.kicad_pro"
    settings = json.loads(pro.read_text())
    settings["text_variables"] = {"VIEW": "Board"}
    pro.write_text(json.dumps(settings, indent=2) + "\n")
    kicad.refill_zones(PCB_PATH)


if __name__ == "__main__":
    main()
