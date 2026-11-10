"""Write everything JLCPCB and the reviewer need into hardware/fab/.

Run as:  python -m hardware.design.export_fab

  gerbers.zip     Gerbers and drill files, for the bare board
  bom.csv         parts to fit, in JLCPCB's column format
  cpl.csv         where to fit them, in JLCPCB's column format
  dongle.step     3D model of the bare board, for the enclosure
  board.pdf       board drawing, three pages, for review without KiCad
  schematic.pdf   the schematic
  board-top.png, board-bottom.png   rendered pictures
"""
import csv
import pathlib
import re
import shutil
import subprocess
import tempfile
import zipfile

from hardware.design import circuit as c
from hardware.design import gen_pcb, gen_sch, kicad

FAB = pathlib.Path(__file__).resolve().parents[1] / "fab"
PCB = gen_pcb.PCB_PATH
SCH = gen_sch.PROJECT_DIR / f"{gen_sch.NAME}.kicad_sch"

GERBER_LAYERS = "F.Cu,B.Cu,F.Mask,B.Mask,F.Paste,F.SilkS,B.SilkS,Edge.Cuts"

# Degrees to add to KiCad's rotation so the part sits the right way round on
# JLCPCB's machines, by footprint name. From the community rotation tables for
# JLCPCB; a starting point to be checked in JLCPCB's placement preview.
ROTATION_OFFSETS: dict[str, int] = {r"^SOT-89": 180, r"^SOIC-": 270, r"^TSSOP-": 270}

# The board drawing's pages: (title, layers)
BOARD_PAGES = [
    ("Top: copper, silkscreen and part outlines", "F.Cu,F.SilkS,F.Fab,Edge.Cuts"),
    ("Bottom: copper and silkscreen (seen through the board from the top)", "B.Cu,B.SilkS,B.Fab,Edge.Cuts"),
    ("Outline, holes and dimensions", "Edge.Cuts,User.Drawings,F.Fab"),
]


def _run(*args) -> None:
    done = subprocess.run([str(a) for a in args], capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"{' '.join(map(str, args))} failed:\n{done.stdout}\n{done.stderr}")


def gerbers() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        _run("kicad-cli", "pcb", "export", "gerbers", "--layers", GERBER_LAYERS,
             "--subtract-soldermask", "-o", f"{tmp}/", PCB)
        _run("kicad-cli", "pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th",
             "--excellon-units", "mm", "-o", f"{tmp}/", PCB)
        with zipfile.ZipFile(FAB / "gerbers.zip", "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(tmp.iterdir()):
                if f.suffix != ".gbrjob":
                    z.write(f, f.name)


def bom() -> None:
    groups: dict[str, list] = {}
    for part in c.PARTS.values():
        if part.assemble:
            groups.setdefault(part.lcsc, []).append(part)
    with (FAB / "bom.csv").open("w", newline="") as f:
        out = csv.writer(f)
        out.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for lcsc, parts in groups.items():
            out.writerow([parts[0].value, ",".join(p.ref for p in parts),
                          parts[0].footprint.split(":")[1], lcsc])


def _rotation_offset(footprint_name: str) -> int:
    return next((deg for pattern, deg in ROTATION_OFFSETS.items() if re.match(pattern, footprint_name)), 0)


def cpl() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        pos = pathlib.Path(tmp) / "pos.csv"
        _run("kicad-cli", "pcb", "export", "pos", "--format", "csv", "--units", "mm",
             "--side", "front", "-o", pos, PCB)
        with pos.open(newline="") as f:
            placed = list(csv.DictReader(f))
    with (FAB / "cpl.csv").open("w", newline="") as f:
        out = csv.writer(f)
        out.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for row in placed:
            part = c.PARTS[row["Ref"]]
            if not part.assemble:
                continue
            rotation = (float(row["Rot"]) + _rotation_offset(part.footprint.split(":")[1])) % 360
            out.writerow([row["Ref"], f"{float(row['PosX']):.4f}mm", f"{float(row['PosY']):.4f}mm",
                          "Top", f"{rotation:g}"])


def step() -> None:
    # The container has no 3D part models, so this is the bare board with its holes.
    _run("kicad-cli", "pcb", "export", "step", "--force", "--no-components", "--drill-origin",
         "-o", FAB / "dongle.step", PCB)


def board_pdf() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        pages = []
        for i, (title, layers) in enumerate(BOARD_PAGES):
            page = pathlib.Path(tmp) / f"page{i}.pdf"
            _run("kicad-cli", "pcb", "export", "pdf", "--layers", layers, "--mode-single",
                 "--include-border-title", "--scale", "5", "--define-var", f"VIEW={title}",
                 "--drill-shape-opt", "2", "-o", page, PCB)
            pages.append(page)
        _run("pdfunite", *pages, FAB / "board.pdf")


def pictures() -> None:
    kicad.export_pdf(SCH, FAB / "schematic.pdf")
    kicad.render(PCB, FAB / "board-top.png", "top", 2400, 900)
    kicad.render(PCB, FAB / "board-bottom.png", "bottom", 2400, 900)


def main() -> None:
    gen_pcb.main()
    FAB.mkdir(parents=True, exist_ok=True)
    for old in ("gerbers.zip", "bom.csv", "cpl.csv", "dongle.step", "board.pdf"):
        (FAB / old).unlink(missing_ok=True)
    gerbers()
    bom()
    cpl()
    step()
    board_pdf()
    pictures()
    shutil.rmtree(FAB / "__pycache__", ignore_errors=True)


if __name__ == "__main__":
    main()
