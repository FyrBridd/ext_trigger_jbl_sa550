"""Generate the project's custom footprints into hardware/lib/dongle.pretty.

Run as:  python -m hardware.design.gen_footprints

- WirePads_1x0N_Strain: hand-solder pads for a cable's wires, each with an
  unplated strain-relief hole on the board-end side.
- TC2030-MCP-NL: Tag-Connect 6-pin no-legs programming footprint, numbered for
  the TC2030-MCP-NL (Microchip RJ12) cable. See hardware/lib/README.md.
"""
import pathlib
import shutil

import pcbnew

LIB_DIR = pathlib.Path(__file__).resolve().parents[1] / "lib" / "dongle.pretty"
STOCK_CONNECTOR_LIB = "/usr/share/kicad/footprints/Connector.pretty"
STOCK_TC2030 = "Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical"

# Wire pad geometry, mm
WIRE_PITCH = 2.54
WIRE_PAD_DRILL = 1.0
WIRE_PAD_COPPER = 1.8
STRAIN_DRILL = 1.5
STRAIN_OFFSET_X = -3.0   # strain-relief hole sits this far from its pad, toward the board end

# TC2030-MCP-NL pad positions (mm; x right, y down, top-side view), typed in from the
# Tag-Connect drawing "FOOTPRINT FOR TC2030-MCP-NL" sheet 1: the single alignment hole
# is on the left; pins 1, 3, 5 are the lower row and 2, 4, 6 the upper row.
MCP_PAD_XY: dict[str, tuple[float, float]] = {
    "1": (-1.27, 0.635), "2": (-1.27, -0.635),
    "3": (0.0, 0.635), "4": (0.0, -0.635),
    "5": (1.27, 0.635), "6": (1.27, -0.635),
}

NOT_ASSEMBLED = pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM

mm = pcbnew.FromMM


def _pt(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def _line(fp, layer, x1, y1, x2, y2, width=0.12):
    s = pcbnew.PCB_SHAPE(fp)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(_pt(x1, y1))
    s.SetEnd(_pt(x2, y2))
    s.SetLayer(layer)
    s.SetWidth(mm(width))
    fp.Add(s)


def _rect(fp, layer, x1, y1, x2, y2, width=0.12):
    _line(fp, layer, x1, y1, x2, y1, width)
    _line(fp, layer, x2, y1, x2, y2, width)
    _line(fp, layer, x2, y2, x1, y2, width)
    _line(fp, layer, x1, y2, x1, y1, width)


def _round_pad(fp, number, x, y, drill, copper, attribute):
    pad = pcbnew.PAD(fp)
    pad.SetNumber(number)
    pad.SetAttribute(attribute)
    pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    pad.SetSize(pcbnew.VECTOR2I(mm(copper), mm(copper)))
    pad.SetDrillSize(pcbnew.VECTOR2I(mm(drill), mm(drill)))
    if attribute == pcbnew.PAD_ATTRIB_PTH:
        pad.SetLayerSet(pcbnew.PAD.PTHMask())
    else:
        pad.SetLayerSet(pcbnew.PAD.UnplatedHoleMask())
    pad.SetPosition(_pt(x, y))
    fp.Add(pad)
    return pad


def wire_pads(board, n):
    name = f"WirePads_1x{n:02d}_Strain"
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPID(pcbnew.LIB_ID("dongle", name))
    fp.SetAttributes(pcbnew.FP_THROUGH_HOLE | NOT_ASSEMBLED)
    fp.SetLibDescription(f"{n} hand-solder wire pads, each with a strain-relief hole toward the board end")
    fp.Reference().SetText("REF**")
    fp.Reference().SetPosition(_pt(-1.5, -2.2))
    fp.Reference().SetLayer(pcbnew.F_Fab)
    fp.Value().SetText(name)
    fp.Value().SetPosition(_pt(-1.5, (n - 1) * WIRE_PITCH + 2.2))
    fp.Value().SetLayer(pcbnew.F_Fab)
    for i in range(n):
        y = i * WIRE_PITCH
        _round_pad(fp, str(i + 1), 0.0, y, WIRE_PAD_DRILL, WIRE_PAD_COPPER, pcbnew.PAD_ATTRIB_PTH)
        # an unplated hole's "copper" equals its drill: no annular ring
        _round_pad(fp, "", STRAIN_OFFSET_X, y, STRAIN_DRILL, STRAIN_DRILL, pcbnew.PAD_ATTRIB_NPTH)
    top, bottom = -1.4, (n - 1) * WIRE_PITCH + 1.4
    left, right = STRAIN_OFFSET_X - 0.85, 1.4   # 0.1 outside the strain hole's edge
    _rect(fp, pcbnew.F_CrtYd, left, top, right, bottom, 0.05)
    _rect(fp, pcbnew.B_CrtYd, left, top, right, bottom, 0.05)
    _rect(fp, pcbnew.F_Fab, left, top, right, bottom, 0.1)
    return name, fp


def tc2030_mcp_nl():
    name = "TC2030-MCP-NL"
    fp = pcbnew.FootprintLoad(STOCK_CONNECTOR_LIB, STOCK_TC2030)
    fp.SetFPID(pcbnew.LIB_ID("dongle", name))
    fp.SetAttributes(fp.GetAttributes() | NOT_ASSEMBLED)
    fp.SetLibDescription("Tag-Connect TC2030-MCP-NL: 1 MCLR/VPP, 2 VDD, 3 GND, 4 PGD (UPDI), 5 PGC, 6 unused")
    fp.Value().SetText(name)
    by_xy = {xy: number for number, xy in MCP_PAD_XY.items()}
    for pad in fp.Pads():
        if not pad.GetNumber():
            continue  # alignment hole
        xy = (round(pcbnew.ToMM(pad.GetPosition().x), 3), round(pcbnew.ToMM(pad.GetPosition().y), 3))
        pad.SetNumber(by_xy[xy])
    return name, fp


def main():
    if LIB_DIR.exists():
        shutil.rmtree(LIB_DIR)
    LIB_DIR.mkdir(parents=True)
    board = pcbnew.BOARD()
    # pcbnew.FootprintSave() guesses the format from the directory's contents and
    # fails on an empty one, so ask for the KiCad format explicitly.
    kicad_format = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.KICAD_SEXP)
    for name, fp in (wire_pads(board, 2), wire_pads(board, 3), tc2030_mcp_nl()):
        kicad_format.FootprintSave(str(LIB_DIR), fp)
        print(f"wrote {LIB_DIR.name}/{name}.kicad_mod")


if __name__ == "__main__":
    main()
