"""Write everything JLC3DP and a reviewer need into enclosure/out/.

Run as:  python -W ignore -m enclosure.export

- lower.step, upper.step, lower.stl, upper.stl: the two half-shells, one solid per file, in mm.
- view-lower.png, view-upper.png, view-closed.png: line pictures with hidden lines removed.
- enclosure.pdf: three pages of dimensioned sections and views.

Every outline in the drawing is cut from the solids themselves (section() and level_faces()),
so the drawing shows what will be printed. Only the dimension figures come from params.py,
and the tests check the solids against those.
"""
import math
import pathlib
import re
import subprocess
import tempfile

import cadquery as cq
import matplotlib
import matplotlib.image

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from cadquery.occ_impl.exporters.svg import getSVG  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Circle, PathPatch, Rectangle  # noqa: E402
from matplotlib.path import Path  # noqa: E402

from enclosure import keepouts as k, model, params as p  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent / "out"
STAMP = "2026-11-11T00:00:00"      # fixed, so that exporting twice gives identical files
PICTURE_TURN = 22                  # degrees: how far the pictures turn the shell about the vertical
PICTURE_TIP = 52                   # and how far they tip its top towards the viewer


# --- solids ---------------------------------------------------------------------------

def write_solids(halves: dict[str, cq.Workplane]) -> None:
    for name, shape in halves.items():
        step = OUT / f"{name}.step"
        cq.exporters.export(shape, str(step))
        text = step.read_text()
        text = re.sub(r"(FILE_NAME\('[^']*',')[^']*(')", rf"\g<1>{STAMP}\g<2>", text)
        # OpenCascade names the product with a counter that goes up on every export
        text = re.sub(r"Open CASCADE STEP translator [0-9.]+ \d+", f"dongle enclosure, {name} half", text)
        step.write_text(text)
        cq.exporters.export(shape, str(OUT / f"{name}.stl"), tolerance=0.01, angularTolerance=0.1)


# --- pictures -------------------------------------------------------------------------

def _picture(shape: cq.Workplane, name: str, tip: float = PICTURE_TIP) -> None:
    # Turn the shape a little about the vertical, tip its top towards the viewer, then look straight
    # down: looking down z, OpenCascade draws x across the picture, so the shell lies along it.
    posed = shape.rotate((0, 0, 0), (0, 0, 1), PICTURE_TURN).rotate((0, 0, 0), (1, 0, 0), -tip)
    svg = getSVG(posed.val(), {
        "width": 1600, "height": 800, "marginLeft": 30, "marginTop": 30,
        "showAxes": False, "showHidden": False, "projectionDir": (0, 0, 1),
        "strokeWidth": 0.1, "strokeColor": (20, 20, 20),
    })
    with tempfile.TemporaryDirectory() as tmp:
        source, drawn = pathlib.Path(tmp) / "view.svg", pathlib.Path(tmp) / "view.png"
        source.write_text(svg)
        subprocess.run(["rsvg-convert", "-w", "2100", "-b", "white", "-o", str(drawn), str(source)], check=True)
        # the SVG leaves the drawing in one corner of its page: keep only the part with lines in it
        image = matplotlib.image.imread(drawn)[:, :, :3]
        ink = image.min(axis=2) < 0.97
        rows, columns = ink.any(axis=1).nonzero()[0], ink.any(axis=0).nonzero()[0]
        edge = 30
        image = image[max(rows[0] - edge, 0):rows[-1] + edge, max(columns[0] - edge, 0):columns[-1] + edge]
        matplotlib.image.imsave(OUT / name, image)


def write_pictures(halves: dict[str, cq.Workplane]) -> None:
    lower, upper = halves["lower"], halves["upper"]
    _picture(lower, "view-lower.png")
    # The upper half turned over end for end, so its inside faces up and the amp end is on the left.
    # (Rolled over about its length instead, the near wall would hide the LED hole.)
    _picture(upper.rotate((0, 0, 0), (0, 1, 0), 180), "view-upper.png")
    both = cq.Workplane("XY").newObject([cq.Compound.makeCompound([lower.val(), upper.val()])])
    _picture(both, "view-closed.png")


# --- outlines cut from the solids ------------------------------------------------------

_AXES = {(1, 0, 0): (1, 2), (0, 1, 0): (0, 2), (0, 0, 1): (0, 1)}


def _ring(wire, axes) -> list[tuple[float, float]]:
    """A closed wire as a list of 2-D points, in order round the loop."""
    runs = []
    for edge in wire:
        count = 2 if edge.geomType() == "LINE" else 64
        runs.append([tuple(v.toTuple()[i] for i in axes) for v in edge.positions(np.linspace(0, 1, count))])
    if len(runs) > 1:               # edges come in order round the wire, but each may run either way
        ends_of_next = (runs[1][0], runs[1][-1])
        if min(math.dist(runs[0][0], e) for e in ends_of_next) < min(math.dist(runs[0][-1], e) for e in ends_of_next):
            runs[0].reverse()
    points = list(runs[0])
    for run in runs[1:]:
        if math.dist(points[-1], run[0]) > math.dist(points[-1], run[-1]):
            run.reverse()
        points += run[1:]
    return points


def ring_area(ring) -> float:
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]))) / 2


def _signed_area(ring) -> float:
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1])) / 2


def _face_rings(face, axes):
    return _ring(face.outerWire(), axes), [_ring(w, axes) for w in face.innerWires()]


def section(shape, origin, normal):
    """Cut a solid with the plane through `origin` square to an axis. Returns the cut faces
    as (outline, holes) pairs of 2-D rings: (y, z) for a cut across the shell, (x, z) for a
    cut along it, (x, y) for a level cut."""
    axes = _AXES[tuple(round(abs(v)) for v in normal)]
    solid = shape.val() if isinstance(shape, cq.Workplane) else shape
    cut = solid.intersect(cq.Face.makePlane(400, 400, basePnt=origin, dir=normal))
    return [_face_rings(face, axes) for face in cut.Faces()]


def level_faces(shape):
    """Every flat face of a solid that faces straight up: (height, outline, holes) in (x, y)."""
    found = []
    for face in shape.val().Faces():
        if face.geomType() == "PLANE" and face.normalAt().z > 0.999:
            found.append((face.Center().z, *_face_rings(face, (0, 1))))
    return sorted(found, key=lambda item: item[0])


# --- drawing helpers ------------------------------------------------------------------

LOWER = dict(facecolor="#bdbdbd", edgecolor="black", linewidth=0.6, hatch="////")
UPPER = dict(facecolor="#e4e4e4", edgecolor="black", linewidth=0.6, hatch="\\\\\\\\")
BOARD = dict(facecolor="#3f8f5f", edgecolor="black", linewidth=0.5)
PARTS = dict(fill=False, edgecolor="#1f4fbf", linewidth=0.7, linestyle="--")
CABLE = dict(facecolor="#444444", edgecolor="black", linewidth=0.4, alpha=0.45)
STEEL = dict(facecolor="#f2c200", edgecolor="black", linewidth=0.4, alpha=0.9)
SMALL = 6.5


def _patch(outline, holes, **style) -> PathPatch:
    vertices, codes = [], []
    for index, ring in enumerate([outline, *holes]):
        ring = list(ring)
        if (_signed_area(ring) > 0) != (index == 0):     # outline anticlockwise, holes clockwise
            ring.reverse()
        vertices += ring + [ring[0]]
        codes += [Path.MOVETO] + [Path.LINETO] * (len(ring) - 1) + [Path.CLOSEPOLY]
    return PathPatch(Path(vertices, codes), **style)


def _cut(ax, shape, origin, normal, style) -> None:
    for outline, holes in section(shape, origin, normal):
        ax.add_patch(_patch(outline, holes, **style))


def _label(ax, x, y, text, **kw) -> None:
    kw = {"fontsize": SMALL, "ha": "center", "va": "center", **kw}
    ax.text(x, y, text, bbox=dict(facecolor="white", edgecolor="none", pad=0.6, alpha=0.9), **kw)


def _hdim(ax, x1, x2, y, text, from_y=None, text_dy=0.0) -> None:
    """A horizontal dimension from x1 to x2, drawn at height y."""
    if from_y is not None:
        for x in (x1, x2):
            ax.plot([x, x], [from_y, y], color="black", linewidth=0.3)
    ax.annotate("", (x1, y), (x2, y), arrowprops=dict(arrowstyle="<->", linewidth=0.5, shrinkA=0, shrinkB=0))
    _label(ax, (x1 + x2) / 2, y + text_dy, text)


def _vdim(ax, z1, z2, x, text, from_x=None, text_dx=0.0, rotate=True) -> None:
    """A vertical dimension from z1 to z2, drawn at position x."""
    if from_x is not None:
        for z in (z1, z2):
            ax.plot([from_x, x], [z, z], color="black", linewidth=0.3)
    ax.annotate("", (x, z1), (x, z2), arrowprops=dict(arrowstyle="<->", linewidth=0.5, shrinkA=0, shrinkB=0))
    _label(ax, x + text_dx, (z1 + z2) / 2, text, rotation=90 if rotate else 0)


def _note(ax, at, text_at, text, **kw) -> None:
    """A label with a leader line to the thing it names."""
    kw = {"fontsize": SMALL, "ha": "center", "va": "center", **kw}
    ax.annotate(
        text, at, text_at,
        arrowprops=dict(arrowstyle="-|>", linewidth=0.4, shrinkA=1, shrinkB=0, color="black"),
        bbox=dict(facecolor="white", edgecolor="none", pad=0.6, alpha=0.9), **kw,
    )


def _frame(ax, xlim, ylim, title) -> None:
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=8.5, loc="left")


def _page(pdf, fig, title, footer) -> None:
    fig.suptitle(title, fontsize=12, x=0.02, ha="left", fontweight="bold")
    fig.text(0.02, 0.015, footer, fontsize=6.5, ha="left", va="bottom")
    pdf.savefig(fig)
    plt.close(fig)


def _mm(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


R = p.OD / 2
SCREW_XS = sorted({x for x, _ in p.SCREW_XY})
SCREW_TIP_Z = p.SEAT_Z - p.SCREW_LEN


# --- page 1: sections along the shell ---------------------------------------------------

def _along(ax, halves, y, title):
    _cut(ax, halves["lower"], (0, y, 0), (0, 1, 0), LOWER)
    _cut(ax, halves["upper"], (0, y, 0), (0, 1, 0), UPPER)
    ax.add_patch(Rectangle((0, p.Z_BOARD_BOTTOM), p.BOARD_L, p.BOARD_T, **BOARD))
    ax.add_patch(Rectangle((p.PART_EDGE, p.Z_BOARD_TOP), p.BOARD_L - 2 * p.PART_EDGE, p.PART_H, **PARTS))
    _frame(ax, (p.X_MIN - 13, p.X_MAX + 13), (-R - 5.5, R + 4.5), title)


def _page_along(pdf, halves):
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(11.69, 8.27))
    fig.subplots_adjust(left=0.02, right=0.98, top=0.9, bottom=0.05, hspace=0.12)

    _along(top, halves, 0.0, "Section along the centreline (y = 0), trigger end on the left")
    for collar in p.COLLARS:
        out = 1 if collar.x_outer > collar.x_inner else -1
        x1, x2 = sorted((collar.x_inner, collar.x_outer + out * 11))
        d = collar.cable.jacket_dia
        top.add_patch(Rectangle((x1, -d / 2), x2 - x1, d, **CABLE))
        _label(top, collar.x_outer + out * 6.5, 0,
               f"{'trigger' if out < 0 else 'amp'} cable\n{_mm(d)} mm")
        rib = collar.rib_spans()[0 if out < 0 else 1]
        _note(top, ((rib[0] + rib[1]) / 2, collar.rib_d / 2), (collar.x_outer + out * 6.5, R + 2.5),
              f"ribs: {_mm(collar.rib_d)} mm across,\nbore {_mm(collar.bore_d)} mm")
    _hdim(top, p.X_MIN, p.X_MAX, -R - 3.8, f"{_mm(p.X_MAX - p.X_MIN)} overall", from_y=-R)
    _hdim(top, 0, p.BOARD_L, -R - 1.6, f"board {_mm(p.BOARD_L)}", from_y=p.Z_BOARD_BOTTOM)
    _hdim(top, p.X_MIN, p.TRIGGER_COLLAR.x_inner, R + 1.2, f"collar {_mm(p.TRIGGER_COLLAR.length)}", from_y=R)
    _hdim(top, p.TRIGGER_COLLAR.x_inner, -p.GAP, R + 1.2, f"wires {_mm(p.CHAMBER_L)}", from_y=R)
    _hdim(top, p.BOARD_L + p.GAP, p.AMP_COLLAR.x_inner, R + 1.2, f"wires {_mm(p.CHAMBER_L)}", from_y=R)
    _hdim(top, p.AMP_COLLAR.x_inner, p.X_MAX, R + 1.2, f"collar {_mm(p.AMP_COLLAR.length)}", from_y=R)
    _vdim(top, -R, R, p.X_MIN - 9.5, f"{_mm(p.OD)} diameter", from_x=p.X_MIN, text_dx=-1.2)
    _vdim(top, p.Z_BOARD_TOP, p.Z_CEILING, 9.0, _mm(p.TOP_ROOM), text_dx=1.6, rotate=False)
    _vdim(top, p.Z_TRENCH, p.Z_BOARD_BOTTOM, 13.0, _mm(p.UNDER_ROOM), text_dx=1.6, rotate=False)
    _note(top, (33, p.Z_BOARD_TOP + p.PART_H), (36, R + 2.5), f"tallest part, {_mm(p.PART_H)} mm (dashed)")
    pocket_x = sum(x for x, _ in p.J3_HOLES_XY) / 3
    _note(top, (pocket_x, p.PIN_POCKET_Z + 0.2), (pocket_x + 15, -6.6),
          f"pocket for the programming cable's pins,\n{_mm(p.Z_BOARD_BOTTOM - p.PIN_POCKET_Z)} mm below the board")
    _label(top, 6, R - 2.2, "upper half")
    _label(top, 6, -R + 2.2, "lower half")

    _along(bottom, halves, p.SCREW_Y, f"Section through one pair of screws (y = +{_mm(p.SCREW_Y)})")
    for x in SCREW_XS:
        bottom.add_patch(Rectangle((x - p.SCREW_THREAD / 2, SCREW_TIP_Z), p.SCREW_THREAD, p.SCREW_LEN, **STEEL))
        bottom.add_patch(Rectangle((x - p.SCREW_HEAD_D / 2, p.SEAT_Z), p.SCREW_HEAD_D, p.SCREW_HEAD_H, **STEEL))
    left, right = SCREW_XS
    _note(bottom, (left, p.SEAT_Z + p.SCREW_HEAD_H), (left + 9, R + 2.6),
          f"{_mm(p.SCREW_THREAD)} × {_mm(p.SCREW_LEN)} mm screw; head up to {_mm(p.SCREW_HEAD_D)} × {_mm(p.SCREW_HEAD_H)} mm\n"
          f"in a {_mm(p.CBORE_D)} mm counterbore")
    _vdim(bottom, 0, p.SEAT_Z, right + 5.5, f"seat {_mm(p.SEAT_Z)}", from_x=right + p.CBORE_D / 2, text_dx=1.2)
    _vdim(bottom, -p.PILOT_DEPTH, 0, right + 5.5, f"pilot {_mm(p.PILOT_DEPTH)} deep",
          from_x=right + p.PILOT_D / 2, text_dx=1.2)
    _note(bottom, (right - p.PILOT_D / 2, -3.0), (right - 12, -R - 2.6),
          f"pilot hole {_mm(p.PILOT_D)} mm; the screw's thread\nengages {_mm(-SCREW_TIP_Z - p.PILOT_RELIEF_DEPTH)} mm of it")
    _note(bottom, (left + p.PILOT_RELIEF_D / 2, -p.PILOT_RELIEF_DEPTH / 2), (left + 9, -R - 2.6),
          f"mouth opened to {_mm(p.PILOT_RELIEF_D)} mm,\n{_mm(p.PILOT_RELIEF_DEPTH)} mm deep")
    _note(bottom, (left - p.CLEAR_D / 2, 1.5), (left - 8, -R - 2.6), f"clearance hole\n{_mm(p.CLEAR_D)} mm")
    _note(bottom, (p.LED_XY[0], R - 2.0), (p.LED_XY[0] + 4, R + 2.6), "LED hole (page 2, D)")
    _note(bottom, (22.5, p.Z_BOARD_BOTTOM), (22.5, -R - 2.6),
          "at this distance from the centreline the board is over\nthe trench; its ledges are further out (page 2, D)")
    _label(bottom, 12, R - 2.5, "upper half")
    _label(bottom, 12, -R + 2.5, "lower half")
    _label(bottom, p.X_MIN - 6.5, 0.5,
           f"this end is {_mm(p.LID_KEY)} mm longer:\nturned end for end,\nthe lid's screw holes\nmiss the pilot holes")

    _page(pdf, fig, "Dongle enclosure — 1 of 3: sections along the shell",
          "Millimetres. Hatched = printed nylon (darker: lower half). Green = the board. "
          "Outlines are cut from the STEP solids by enclosure/export.py.")


# --- page 2: sections across the shell --------------------------------------------------

def _across(ax, halves, x, title, board=False):
    _cut(ax, halves["lower"], (x, 0, 0), (1, 0, 0), LOWER)
    _cut(ax, halves["upper"], (x, 0, 0), (1, 0, 0), UPPER)
    if board:
        ax.add_patch(Rectangle((-p.BOARD_W / 2, p.Z_BOARD_BOTTOM), p.BOARD_W, p.BOARD_T, **BOARD))
        half = p.BOARD_W / 2 - p.PART_EDGE
        ax.add_patch(Rectangle((-half, p.Z_BOARD_TOP), 2 * half, p.PART_H, **PARTS))
    _frame(ax, (-R - 7.5, R + 7.5), (-R - 4.2, R + 3.2), title)


def _screws_across(ax):
    for y in (p.SCREW_Y, -p.SCREW_Y):
        ax.add_patch(Rectangle((y - p.SCREW_THREAD / 2, SCREW_TIP_Z), p.SCREW_THREAD, p.SCREW_LEN, **STEEL))
        ax.add_patch(Rectangle((y - p.SCREW_HEAD_D / 2, p.SEAT_Z), p.SCREW_HEAD_D, p.SCREW_HEAD_H, **STEEL))


def _page_across(pdf, halves):
    fig, axes = plt.subplots(2, 3, figsize=(11.69, 8.27))
    fig.subplots_adjust(left=0.01, right=0.99, top=0.9, bottom=0.05, hspace=0.1, wspace=0.02)
    (a, b, c), (d, e, f) = axes
    trigger, amp = p.TRIGGER_COLLAR, p.AMP_COLLAR

    # trigger-end screws
    x = SCREW_XS[0]
    _across(a, halves, x, f"A. Trigger-end screws (x = {_mm(x)})")
    a.add_patch(Circle((0, 0), trigger.cable.jacket_dia / 2, **CABLE))
    _screws_across(a)
    _note(a, (0, trigger.bore_d / 2), (0, R + 1.8),
          f"{_mm(trigger.cable.jacket_dia)} mm cable in a {_mm(trigger.bore_d)} mm bore")
    _hdim(a, -p.SCREW_Y, p.SCREW_Y, -R - 2.2, f"screws {_mm(2 * p.SCREW_Y)} apart", from_y=SCREW_TIP_Z)

    # trigger wire chamber
    _across(b, halves, -3.0, "B. Trigger-end wire chamber (x = −3)")
    _hdim(b, -p.CHAMBER_R, p.CHAMBER_R, 0, f"{_mm(2 * p.CHAMBER_R)} across")
    _vdim(b, p.CHAMBER_R, R, 0, _mm(R - p.CHAMBER_R), text_dx=1.8, rotate=False)
    _label(b, 0, -2.6, "room for the wires between\nthe cable's end and the board")

    # programming footprint
    x = sum(px for px, _ in p.J3_HOLES_XY) / 3
    _across(c, halves, x, f"C. Programming footprint (x = {_mm(x)})", board=True)
    for _, y in p.J3_HOLES_XY:
        c.add_patch(Rectangle((y - p.PIN_D / 2, p.Z_BOARD_BOTTOM - 1.6), p.PIN_D, 1.6 + p.BOARD_T + 2.0,
                              facecolor="#d62728", edgecolor="black", linewidth=0.3))
    _note(c, (p.J3_HOLES_XY[0][1], p.Z_BOARD_BOTTOM - 1.6), (0, -R - 2.2),
          f"Tag-Connect alignment pins come 1.6 mm through the board;\n"
          f"the pocket under them is {_mm(p.Z_BOARD_BOTTOM - p.PIN_POCKET_Z)} mm deep")
    _note(c, (p.RAIL_INNER_Y + 0.45, p.Z_RAIL + 0.8), (R + 3.2, R - 0.5),
          f"rail stops {_mm(p.RAIL_GAP)} mm\nabove the board")

    # LED hole
    led_x, led_y = p.LED_XY
    _across(d, halves, led_x, f"D. LED hole (x = {_mm(led_x)})", board=True)
    d.add_patch(Rectangle((led_y - 0.4, p.Z_BOARD_TOP), 0.8, 0.6, facecolor="#d62728", edgecolor="black", linewidth=0.3))
    _note(d, (led_y, p.Z_BOARD_TOP + 0.6), (R + 3.4, 1.2), "LED (D3)")
    _hdim(d, led_y - p.LED_HOLE_D / 2, led_y + p.LED_HOLE_D / 2, R + 1.4, f"hole {_mm(p.LED_HOLE_D)}",
          from_y=math.sqrt(R ** 2 - led_y ** 2))
    _vdim(d, p.Z_BOARD_TOP, p.Z_CEILING, -2.0, _mm(p.TOP_ROOM), text_dx=-1.7, rotate=False)
    _vdim(d, p.Z_TRENCH, p.Z_BOARD_BOTTOM, -2.0, _mm(p.UNDER_ROOM), text_dx=-1.7, rotate=False)
    _hdim(d, -p.POCKET_HALF_W, p.POCKET_HALF_W, -R - 0.9, f"pocket {_mm(2 * p.POCKET_HALF_W)} for a {_mm(p.BOARD_W)} board",
          from_y=p.Z_BOARD_BOTTOM)
    _hdim(d, -p.TRENCH_HALF_W, p.TRENCH_HALF_W, -R - 2.9, f"trench {_mm(2 * p.TRENCH_HALF_W)}", from_y=p.Z_TRENCH)
    _note(d, (-p.TRENCH_HALF_W - 0.6, p.Z_BOARD_BOTTOM), (-R - 3.3, -5.5),
          f"board rests\n{_mm(p.BOARD_W / 2 - p.TRENCH_HALF_W)} mm\non each ledge")

    # an amp-end rib
    lo, hi = amp.rib_spans()[0]
    _across(e, halves, (lo + hi) / 2, f"E. Amp-end collar at a rib (x = {_mm((lo + hi) / 2)})")
    e.add_patch(Circle((0, 0), amp.cable.jacket_dia / 2, **CABLE))
    e.add_patch(Circle((0, 0), amp.rib_d / 2, fill=False, edgecolor="#d62728", linewidth=0.8))
    _note(e, (amp.rib_d / 2 * 0.71, amp.rib_d / 2 * 0.71), (R + 0.5, R + 1.6),
          f"rib {_mm(amp.rib_d)} mm across squeezes the {_mm(amp.cable.jacket_dia)} mm cable\n"
          f"by {_mm((amp.cable.jacket_dia - amp.rib_d) / 2)} mm all round (red = the rib's edge)")
    _label(e, 0, -R - 2.2, f"trigger end: rib {_mm(trigger.rib_d)} mm on a {_mm(trigger.cable.jacket_dia)} mm cable")

    # amp-end screws
    x = SCREW_XS[1]
    _across(f, halves, x, f"F. Amp-end screws (x = {_mm(x)})")
    f.add_patch(Circle((0, 0), amp.cable.jacket_dia / 2, **CABLE))
    _screws_across(f)
    pilot_corner = (p.SCREW_Y + p.PILOT_D / 2, -p.PILOT_DEPTH)
    seat_corner = (p.SCREW_Y + p.CBORE_D / 2, p.SEAT_Z)
    _note(f, pilot_corner, (R + 3.2, -R - 1.4), f"{_mm(R - math.hypot(*pilot_corner))} mm outside the\nhole's bottom corner")
    _note(f, seat_corner, (R + 3.6, R + 0.6), f"{_mm(R - math.hypot(*seat_corner))} mm\nbeside the head")
    _note(f, (-p.SCREW_Y + p.PILOT_D / 2, -2.5), (-R - 3.4, -R - 1.4),
          f"{_mm(p.SCREW_Y - p.PILOT_D / 2 - amp.bore_d / 2)} mm between\nhole and cable bore")
    _note(f, (0, amp.bore_d / 2), (0, R + 1.8), f"{_mm(amp.cable.jacket_dia)} mm cable in a {_mm(amp.bore_d)} mm bore")

    _page(pdf, fig, "Dongle enclosure — 2 of 3: sections across the shell",
          "Millimetres. Each is seen from the amp end, so +y (the board's upper edge in board.pdf, where the LED is) is on the right. "
          "Hatched = printed nylon. Yellow = screws. Blue dashes = tallest part.")


# --- page 3: views from above -----------------------------------------------------------

def _ruler(ax, y, marks, baseline_from):
    """Positions along the shell, measured from the board's trigger-end edge."""
    xs = [x for x, _ in marks]
    ax.plot([min(xs), max(xs)], [y, y], color="black", linewidth=0.5)
    for index, (x, text) in enumerate(marks):
        ax.plot([x, x], [baseline_from, y - 0.6], color="black", linewidth=0.25, linestyle=":")
        ax.plot([x, x], [y - 0.6, y + 0.6], color="black", linewidth=0.5)
        ax.text(x, y - 1.2 - (index % 2) * 2.4, text, fontsize=6, ha="center", va="top")


def _page_above(pdf, halves):
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(11.69, 8.27))
    fig.subplots_adjust(left=0.02, right=0.98, top=0.9, bottom=0.05, hspace=0.1)
    xlim = (p.X_MIN - 16, p.X_MAX + 16)
    board_outline = dict(fill=False, edgecolor="#3f8f5f", linewidth=0.9, linestyle="--")

    # the lower half, every level face shaded by its depth
    _frame(top, xlim, (-R - 8.5, R + 3), "Lower half from above (the side the board drops into). Darker = deeper.")
    top.add_patch(Rectangle((p.X_MIN, -R), p.X_MAX - p.X_MIN, 2 * R, facecolor="#f3ead2", edgecolor="black", linewidth=0.6))
    deepest = -p.PILOT_DEPTH
    for z, outline, holes in level_faces(halves["lower"]):
        shade = 0.93 - 0.6 * (z / deepest)
        top.add_patch(_patch(outline, holes, facecolor=str(round(shade, 3)), edgecolor="black", linewidth=0.5))
    top.add_patch(Rectangle((0, -p.BOARD_W / 2), p.BOARD_L, p.BOARD_W, **board_outline))
    for x, y in p.J3_HOLES_XY:
        top.add_patch(Circle((x, y), 0.5, facecolor="#d62728", edgecolor="none"))
    for x, y in p.WIRE_PADS_XY:
        top.add_patch(Circle((x, y), 0.5, fill=False, edgecolor="#1f4fbf", linewidth=0.7))
    _note(top, p.J3_HOLES_XY[0], (p.J3_HOLES_XY[0][0] - 9, -3.2), "programming pins\n(red) over their pocket")
    _note(top, p.WIRE_PADS_XY[0], (11.5, 3.6), "wire pads (blue)\nover the trench")
    _note(top, (34, -p.BOARD_W / 2), (34, -3.4), "board outline (green dashes)")
    _note(top, (30, p.TRENCH_HALF_W + 0.8), (30, 3.4), "ledge")
    _note(top, (p.SCREW_XY[0][0], p.SCREW_XY[0][1]), (p.X_MIN - 9, R - 1), f"pilot holes\n{_mm(p.PILOT_D)} mm")
    _label(top, p.X_MIN - 9, -1.5, "cream = curved\n(cable bore,\nwire chamber)")
    _label(top, p.X_MAX + 8, -R - 4.5, "amp end\n(the wider bore)")
    _label(top, p.X_MIN - 9, -R - 4.5, "trigger end")
    pin_xs = [x for x, _ in p.J3_HOLES_XY]
    _ruler(top, -R - 2.2, [
        (p.X_MIN, _mm(p.X_MIN)), (SCREW_XS[0], f"screws {_mm(SCREW_XS[0])}"),
        (p.TRIGGER_COLLAR.x_inner, _mm(p.TRIGGER_COLLAR.x_inner)), (0, "board 0"),
        (min(pin_xs) - p.PIN_POCKET_MARGIN, f"pin pocket {_mm(min(pin_xs) - p.PIN_POCKET_MARGIN)}"),
        (max(pin_xs) + p.PIN_POCKET_MARGIN, _mm(max(pin_xs) + p.PIN_POCKET_MARGIN)),
        (p.BOARD_L, f"board {_mm(p.BOARD_L)}"), (p.AMP_COLLAR.x_inner, _mm(p.AMP_COLLAR.x_inner)),
        (SCREW_XS[1], f"screws {_mm(SCREW_XS[1])}"), (p.X_MAX, _mm(p.X_MAX)),
    ], baseline_from=-R)
    _vdim(top, -p.SCREW_Y, p.SCREW_Y, p.X_MAX + 3, f"screws {_mm(2 * p.SCREW_Y)}", from_x=SCREW_XS[1], text_dx=1.3)
    _vdim(top, -R, R, p.X_MAX + 13, _mm(p.OD), from_x=p.X_MAX, text_dx=1.3)

    # the upper half, sliced above its cavity so every opening through it shows
    level = p.Z_CEILING + 0.6
    _frame(bottom, xlim, (-R - 8.5, R + 3),
           f"Upper half from above, sliced {_mm(level)} mm above the split: every opening through the lid.")
    for outline, holes in section(halves["upper"], (0, 0, level), (0, 0, 1)):
        bottom.add_patch(_patch(outline, holes, **UPPER))
    bottom.add_patch(Rectangle((0, -p.BOARD_W / 2), p.BOARD_L, p.BOARD_W, **board_outline))
    bottom.plot([p.X_MIN - 3, p.X_MAX + 3], [0, 0], color="black", linewidth=0.4, linestyle="-.")
    _label(bottom, p.X_MAX + 9, 0, "centreline")
    led_x, led_y = p.LED_XY
    bottom.add_patch(Rectangle((led_x - 0.8, led_y - 0.4), 1.6, 0.8, facecolor="#d62728", edgecolor="none"))
    _note(bottom, (led_x + 1.0, led_y), (led_x + 12, 2.0), f"LED hole {_mm(p.LED_HOLE_D)} mm, over the LED (red)")
    _note(bottom, (SCREW_XS[0], p.SCREW_Y), (p.X_MIN - 9, R - 1), f"counterbores\n{_mm(p.CBORE_D)} mm")
    _label(bottom, 20, -3.0, "the lid is solid over the board except for the LED hole")
    _label(bottom, p.X_MIN - 9, -1.5, "white slots =\nthe wire chambers")
    _ruler(bottom, -R - 2.2, [
        (p.X_MIN, _mm(p.X_MIN)), (SCREW_XS[0], f"screws {_mm(SCREW_XS[0])}"), (0, "board 0"),
        (led_x, f"LED {_mm(led_x)}"), (p.BOARD_L, f"board {_mm(p.BOARD_L)}"),
        (SCREW_XS[1], f"screws {_mm(SCREW_XS[1])}"), (p.X_MAX, _mm(p.X_MAX)),
    ], baseline_from=-R)
    _vdim(bottom, 0, led_y, led_x - 4, f"{_mm(led_y)}", text_dx=-1.5, rotate=False)
    bottom.plot([led_x - 4, led_x - p.LED_HOLE_D / 2], [led_y, led_y], color="black", linewidth=0.3)

    _page(pdf, fig, "Dongle enclosure — 3 of 3: views from above",
          "Millimetres. Trigger end on the left; +y (the board's upper edge in board.pdf) at the top, as in board.pdf page 1. "
          "Positions along the shell are measured from the board's trigger-end edge.")


def write_drawing(halves: dict[str, cq.Workplane]) -> None:
    matplotlib.rcParams["hatch.linewidth"] = 0.25
    matplotlib.rcParams["pdf.compression"] = 6
    metadata = {"Title": "Dongle enclosure", "Creator": "enclosure/export.py", "Producer": "matplotlib",
                "CreationDate": None, "ModDate": None}
    with PdfPages(OUT / "enclosure.pdf", metadata=metadata) as pdf:
        _page_along(pdf, halves)
        _page_across(pdf, halves)
        _page_above(pdf, halves)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    halves = {"lower": model.lower(), "upper": model.upper()}
    write_solids(halves)
    write_pictures(halves)
    write_drawing(halves)
    for name in sorted(path.name for path in OUT.iterdir()):
        print("wrote", f"enclosure/out/{name}")


if __name__ == "__main__":
    main()
