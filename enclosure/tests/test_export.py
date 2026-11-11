import pathlib
import subprocess

import cadquery as cq
import pytest

from enclosure import export, keepouts as k, model

OUT = pathlib.Path("enclosure/out")


@pytest.fixture(scope="module", autouse=True)
def exported():
    export.main()


@pytest.mark.parametrize("name", ["lower", "upper"])
def test_step_file_holds_the_same_single_solid(name):
    back = cq.importers.importStep(str(OUT / f"{name}.step"))
    assert back.solids().size() == 1
    assert abs(k.volume(back) - k.volume(getattr(model, name)())) < 0.5
    box, meant = back.val().BoundingBox(), getattr(model, name)().val().BoundingBox()
    assert abs(box.xlen - meant.xlen) < 1e-3 and abs(box.zmin - meant.zmin) < 1e-3   # millimetres, same frame


@pytest.mark.parametrize("name", ["lower", "upper"])
def test_stl_written(name):
    assert (OUT / f"{name}.stl").stat().st_size > 50_000


def test_pictures_written():
    for name in ("view-lower.png", "view-upper.png", "view-closed.png"):
        data = (OUT / name).read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) > 15_000


def test_pictures_fill_their_frames():
    import matplotlib.image
    for name in ("view-lower.png", "view-upper.png", "view-closed.png"):
        ink = matplotlib.image.imread(OUT / name)[:, :, :3].min(axis=2) < 0.5      # True where a line is drawn
        columns, rows = ink.any(axis=0).nonzero()[0], ink.any(axis=1).nonzero()[0]
        assert (columns[-1] - columns[0]) / ink.shape[1] > 0.8, name                 # the shell lies along the picture
        assert (rows[-1] - rows[0]) / ink.shape[0] > 0.5, name


def test_drawing_has_three_pages():
    info = subprocess.run(["pdfinfo", str(OUT / "enclosure.pdf")], capture_output=True, text=True, check=True).stdout
    assert "Pages:           3" in info


def test_exporting_twice_gives_the_same_files():
    names = ["lower.step", "upper.step", "lower.stl", "upper.stl", "enclosure.pdf"]
    first = {n: (OUT / n).read_bytes() for n in names}
    export.main()
    assert [n for n in names if (OUT / n).read_bytes() != first[n]] == []


def test_sections_come_from_the_solid():
    # the drawing's outlines are cut from the model: a slice across mid-board has the areas the shapes have
    rings = export.section(model.lower(), origin=(22, 0, 0), normal=(1, 0, 0))
    area = sum(export.ring_area(outer) - sum(export.ring_area(h) for h in holes) for outer, holes in rings)
    slab = k.box((21.99, 22.01), (-20, 20), (-20, 20))
    assert area == pytest.approx(k.overlap(model.lower(), slab) / 0.02, rel=1e-3)
