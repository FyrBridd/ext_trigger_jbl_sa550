# Dongle Enclosure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A two-part screwed shell for the dongle board, ready to order from JLC3DP, generated and checked from the headless box.

**Architecture:** A Python script builds both half-shells with CadQuery from one parameter file, which takes the board size, LED and programming-pad positions from `hardware/design/layout.py` and the cable sizes from `hardware/design/cables.py`. A second module builds solids for everything the shell must fit round (board, tallest parts, wires, cables, screws, programming-cable pins). Tests intersect those solids with the shell: no overlap means it fits, a required overlap means it grips or supports.

**Tech Stack:** Docker dev container (`tools/dev`), CadQuery 2.8.0, pytest, matplotlib (drawings), librsvg (`rsvg-convert`, pictures).

**Spec:** `docs/superpowers/specs/2026-11-10-wiim-trigger-jbl-dongle-design.md`, section 8. Read it first. Two things in it are out of date and this plan corrects them: the board is 13 × 45 mm, so the shell is about 18 mm across and 72 mm long, not 17–18 × 60; and the cables are now named (`docs/cables.md`), so the shell is designed to their published jacket sizes, not to a measurement.

## Global Constraints

- All commands run through `tools/dev`. Never use sudo.
- Shape: a cylinder split lengthwise into a lower and an upper half, held by four screws. Appearance does not matter; protection and cable grip do.
- Nothing in the shell touches a fitted part: at least 0.3 mm from the board's edges and ends, 2.5 mm of room above the board (tallest part 1.75 mm), 1.8 mm below it (wire runs up to 1.2 mm).
- JLC3DP rules for MJF PA12: walls at least 1.2 mm, and more than 1.5 mm round screws; holes at least 1.5 mm across; 0.2–0.4 mm between mating parts; tolerance ±0.3 mm, holes tend small.
- Each half is one solid, exported as its own STEP and STL file.
- Every review document is a PDF or Markdown file. Pictures are embedded in the Markdown.
- Sizes that come from the board or the cables are read from `hardware/design/layout.py` and `hardware/design/cables.py`, never retyped.
- Commit after each task with the message given, on the current branch. Commit messages end with the line `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`. Do not push.

## Review Focus

Mistakes most likely to waste a print:

1. **Mirror-image and wrong-end errors.** The LED hole on the wrong side of the centreline, the programming-pin pocket in the wrong place along the board, or the two cable collars swapped. Pinned by `test_led_hole_is_over_the_led`, `test_programming_pins_have_a_pocket` and `test_each_collar_matches_its_cable`, each using explicit coordinates.
2. **Print tolerance eating the clearance.** Pinned by `test_parts_and_wires_have_clearance`, which inflates the keep-out solids by 0.3 mm.
3. **A collar that does not grip, or cannot close.** Pinned by `test_collar_ribs_bite_but_the_cable_passes`.
4. **Nowhere for the wires.** Six cut-back cores and three live ones at the amp end. Pinned by `test_wire_chambers_are_open`.
5. **Screws that strip or split the plastic.** The pilot size is an estimate until a print is tried. Pinned as far as it can be by `test_screw_holes` and the JLC3DP rule checks in `test_params.py`; flagged in the review document.

---

## Coordinates

One frame for everything in `enclosure/`:

- **x** along the shell, 0 at the board's trigger-end edge, 45 at its amp-end edge.
- **y** across, 0 on the board's centreline. Looking down on the top of the board with the trigger end on the left, +y is away from you (the board's upper edge in `board.pdf`).
- **z** up, 0 on the plane where the halves meet, which is also the cylinder's axis.

`layout.py` measures y downward from the board's upper edge, so a layout point (x, y) is shell point (x, WIDTH/2 − y). The LED, at layout (27.98, 1.8), is at shell (27.98, +4.7).

## Parameters

`enclosure/params.py`. Lengths in mm.

| Name | Value | Meaning |
|---|---|---|
| `OD` | 18.0 | outside diameter |
| `BOARD_L`, `BOARD_W` | `layout.LENGTH`, `layout.WIDTH` | 45, 13 |
| `BOARD_T` | 1.6 | board thickness |
| `GAP` | 0.3 | room round the board's edges and ends |
| `Z_BOARD_BOTTOM` | −1.15 | so `Z_BOARD_TOP` is +0.45 |
| `TOP_ROOM` | 2.5 | cavity above the board: ceiling at z = +2.95 |
| `UNDER_ROOM` | 1.8 | trench below the board: floor at z = −2.95 |
| `LEDGE_W` | 1.6 | the board rests on this much at each long edge; trench half-width 5.2 |
| `RAIL_GAP` | 0.3 | hold-down rails in the upper half stop this far above the board |
| `RAIL_INNER_Y` | 5.9 | rails occupy \|y\| from 5.9 to 6.8 |
| `CHAMBER_L`, `CHAMBER_R` | 6.0, 5.5 | wire chamber between each collar and the board |
| `COLLAR_L` | 7.0 | length of each cable collar |
| `X_MIN`, `X_MAX` | −13.3, 58.3 | so the overall length is 71.6 |
| `BORE_CLEARANCE` | 0.3 | collar bore diameter = jacket + 0.3 |
| `RIB_BITE` | 0.7 | rib inner diameter = jacket − 0.7 |
| `RIB_W`, `RIB_AT` | 1.0, (1.5, 4.5) | two ring-shaped ribs per collar, measured from the shell's end |
| `SCREW_THREAD`, `SCREW_LEN` | 2.2, 8.0 | thread-forming screw for plastics |
| `SCREW_HEAD_D`, `SCREW_HEAD_H` | 4.2, 1.7 | largest head allowed for |
| `PILOT_D`, `PILOT_DEPTH` | 1.8, 5.5 | in the lower half |
| `CLEAR_D` | 2.6 | through the upper half |
| `CBORE_D`, `SEAT_Z` | 4.6, 3.0 | counterbore; the screw head sits at z = +3.0 |
| `SCREW_XY` | (−9.8, ±5.2), (54.8, ±5.2) | four screws, beside the cables |
| `LED_HOLE_D` | 2.0 | over D3 |
| `PIN_POCKET_Z` | −4.0 | pocket floor under the programming footprint's three alignment holes |

Derived, and asserted in tests: wall at the cavity's top corners `OD/2 − hypot(6.8, 2.95)` = 1.59 mm; trigger collar bore 4.0 and rib 3.0; amp collar bore 5.1 and rib 4.1.

The Tag-Connect cable's alignment pins stand 3.175 mm past its compressed contact pins (Tag-Connect drawing TC2030-MCP-NL, sheet 2), so they come 1.6 mm through a 1.6 mm board. The pin pocket gives them 2.85 mm, so the board can be programmed while it sits in the lower half.

## File structure

```
tools/Dockerfile               add cadquery 2.8.0 and librsvg2-bin
enclosure/__init__.py
enclosure/params.py            every dimension, with where it comes from
enclosure/keepouts.py          solids for the things the shell must fit round
enclosure/model.py             lower() and upper(): the two half-shells
enclosure/export.py            STEP, STL, pictures and the drawing PDF
enclosure/out/                 generated files (committed)
enclosure/tests/               pytest
docs/enclosure.md              review document, ordering and assembly steps
```

---

### Task 1: CAD tooling in the dev container

**Files:**
- Modify: `tools/Dockerfile`, `tools/tests/test_env.py`, `Makefile`
- Create: `enclosure/__init__.py`, `enclosure/tests/__init__.py`

**Interfaces:**
- Produces: inside `tools/dev`, `import cadquery` (2.8.0) and the command `rsvg-convert`. Make targets `enc` (`python -W ignore -m enclosure.export`) and `enc-test` (`pytest enclosure/tests -q`).

- [ ] **Step 1: Add the failing tests** to `tools/tests/test_env.py`

```python
def test_cadquery_builds_a_solid():
    import importlib.metadata
    import cadquery as cq
    assert importlib.metadata.version("cadquery") == "2.8.0"
    assert abs(cq.Workplane("XY").box(1, 2, 3).val().Volume() - 6.0) < 1e-9

def test_drawing_tools_present():
    import matplotlib  # noqa: F401
    assert shutil.which("rsvg-convert") and shutil.which("pdfinfo")
```

- [ ] **Step 2: Run** `tools/dev pytest tools/tests/test_env.py -q` — expected: 2 failed.
- [ ] **Step 3: Edit `tools/Dockerfile`:** add `librsvg2-bin` to the apt line and `cadquery==2.8.0 matplotlib` to the pip line. (Already tried in a throwaway image on this box: it installs and builds solids.)
- [ ] **Step 4: Run** the same command — expected: all pass. Then `tools/dev pytest tools/tests hardware/tests -q` — expected: all pass, so the new packages have not disturbed KiCad.
- [ ] **Step 5: Add the two Makefile targets and commit** — `chore: CadQuery and SVG conversion in the dev container`

---

### Task 2: Parameters

**Files:**
- Create: `enclosure/params.py`, `enclosure/tests/test_params.py`

**Interfaces:**
- Consumes: `hardware.design.layout` (`LENGTH`, `WIDTH`, `PLACEMENTS`), `hardware.design.cables` (`TRIGGER`, `SERIAL`), `hardware.design.gen_footprints` (wire pad geometry).
- Produces: the names in the Parameters table, plus:
  - `board_to_shell(x, y) -> tuple[float, float]`
  - `LED_XY`, `J3_HOLES_XY` (three points), `WIRE_PADS_XY` (five points), all in shell coordinates
  - `Collar` dataclass with `x_outer, x_inner, bore_d, rib_d, cable` and the two instances `TRIGGER_COLLAR` (x from −13.3 to −6.3) and `AMP_COLLAR` (x from 51.3 to 58.3)

- [ ] **Step 1: Write the failing tests** in `enclosure/tests/test_params.py`

```python
import math
from enclosure import params as p
from hardware.design import cables, layout

def test_overall_size():
    assert p.OD == 18.0
    assert math.isclose(p.X_MAX - p.X_MIN, 71.6)
    assert math.isclose(p.X_MIN, -(p.GAP + p.CHAMBER_L + p.COLLAR_L))

def test_board_frame():
    assert p.board_to_shell(0, 0) == (0, 6.5)
    assert p.board_to_shell(45, 13) == (45, -6.5)
    assert p.LED_XY == (27.98, 4.7)                       # D3, towards the board's upper edge
    assert sorted(p.J3_HOLES_XY) == [(20.38, 2.44), (21.4, -2.64), (22.42, 2.44)]

def test_collars_follow_the_cables():
    assert p.TRIGGER_COLLAR.cable is cables.TRIGGER and p.AMP_COLLAR.cable is cables.SERIAL
    assert math.isclose(p.TRIGGER_COLLAR.bore_d, 4.0) and math.isclose(p.TRIGGER_COLLAR.rib_d, 3.0)
    assert math.isclose(p.AMP_COLLAR.bore_d, 5.1) and math.isclose(p.AMP_COLLAR.rib_d, 4.1)
    assert p.TRIGGER_COLLAR.x_outer == p.X_MIN and p.AMP_COLLAR.x_outer == p.X_MAX

def test_ribs_grip_across_the_tolerances():
    # radial bite with the print 0.3 mm big and the cable at its thinnest, and the reverse
    for collar in (p.TRIGGER_COLLAR, p.AMP_COLLAR):
        c = collar.cable
        loosest = ((c.jacket_dia - c.jacket_tolerance) - (collar.rib_d + 0.3)) / 2
        tightest = ((c.jacket_dia + c.jacket_tolerance) - (collar.rib_d - 0.3)) / 2
        assert loosest > 0.09 and tightest < 0.61

def test_jlc3dp_rules():
    corner_wall = p.OD / 2 - math.hypot(p.BOARD_W / 2 + p.GAP, p.Z_BOARD_TOP + p.TOP_ROOM)
    assert corner_wall >= 1.5
    assert p.PILOT_D >= 1.5 and p.LED_HOLE_D >= 2.0 and p.RIB_W >= 0.8
    for x, y in p.SCREW_XY:                               # plastic round every screw
        assert p.OD / 2 - math.hypot(y, 0) - p.PILOT_D / 2 > 1.5
        assert abs(y) - p.PILOT_D / 2 - p.AMP_COLLAR.bore_d / 2 > 1.5
    depth_available = math.sqrt((p.OD / 2) ** 2 - p.SCREW_XY[0][1] ** 2)
    assert depth_available - p.PILOT_DEPTH >= 1.2          # floor under each pilot hole
    assert p.SCREW_LEN - p.SEAT_Z <= p.PILOT_DEPTH        # the screw does not bottom out in its hole

def test_room_for_the_tallest_part_and_the_wires():
    assert p.TOP_ROOM - 1.75 >= 0.3 + 0.3                  # SOIC-8, clearance, print tolerance
    assert p.UNDER_ROOM - max(c.insulation_dia_max for c in cables.CABLES) >= 0.3 + 0.3
```

- [ ] **Step 2: Run** `tools/dev pytest enclosure/tests/test_params.py -q` — expected: import error.
- [ ] **Step 3: Write `enclosure/params.py`** from the Parameters table. Take `LED_XY` from `layout.PLACEMENTS["D3"]`. Work out `J3_HOLES_XY` and `WIRE_PADS_XY` from `layout.PLACEMENTS` and the footprints' hole offsets, turning each by the part's rotation (KiCad's rotation is anticlockwise seen from the top, with y down).
- [ ] **Step 4: Run** — expected: all pass.
- [ ] **Step 5: Commit** — `feat(enc): enclosure parameters from the board and cable data`

---

### Task 3: Keep-out solids

**Files:**
- Create: `enclosure/keepouts.py`, `enclosure/tests/test_keepouts.py`

**Interfaces:**
- Consumes: `params`.
- Produces, each returning a `cadquery.Workplane` holding one or more solids in shell coordinates:
  - `board()` — the bare board, 45 × 13 × 1.6.
  - `parts(clearance=0.0)` — a slab over the area where parts may be (the board less 1.0 mm at each edge), from the board's top up 1.75 mm, grown by `clearance` on every side except downward.
  - `underside(clearance=0.0)` — slabs under the two wire-pad areas (x from 0 to 7 and from 38 to 45, \|y\| ≤ 4.5), 1.2 mm deep, grown likewise except upward.
  - `cable(collar, diameter=None)` — a rod on the axis through that collar, of the cable's jacket diameter unless `diameter` is given, reaching 2 mm beyond the shell's end.
  - `wire_room(collar)` — a rod of radius 5.0 filling that end's wire chamber less 0.2 mm at each end.
  - `programming_pins()` — three rods of diameter 1.2 at `J3_HOLES_XY`, from the board's top down to 2.2 mm below its bottom.
  - `led_sightline(diameter)` — a rod over `LED_XY` from the board's top up to z = 12.
  - `screw(xy, diameter, z_from, z_to)` — a rod on one screw's axis.
  - `volume(shape) -> float` and `overlap(a, b) -> float` (volume of the intersection in mm³; exactly 0.0 when they do not meet or only touch, treating anything under 1e-6 as touching).

- [ ] **Step 1: Write the failing tests** in `enclosure/tests/test_keepouts.py`

```python
import math
from enclosure import keepouts as k, params as p

def bbox(shape): b = shape.val().BoundingBox(); return (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)
def close(a, b): return all(math.isclose(x, y, abs_tol=1e-6) for x, y in zip(a, b))

def test_board_sits_where_the_parameters_say():
    assert close(bbox(k.board()), (0, 45, -6.5, 6.5, -1.15, 0.45))
    assert math.isclose(k.volume(k.board()), 45 * 13 * 1.6)

def test_parts_slab_and_its_clearance():
    assert close(bbox(k.parts()), (1, 44, -5.5, 5.5, 0.45, 2.2))
    assert close(bbox(k.parts(0.3)), (0.7, 44.3, -5.8, 5.8, 0.45, 2.5))

def test_underside_slabs_are_under_the_wire_pads():
    assert close(bbox(k.underside()), (0, 45, -4.5, 4.5, -2.35, -1.15))
    assert math.isclose(k.volume(k.underside()), 2 * 7 * 9 * 1.2)
    for x, y in p.WIRE_PADS_XY:
        assert (0 <= x <= 7 or 38 <= x <= 45) and abs(y) <= 4.5

def test_cables_and_overlap():
    trigger = k.cable(p.TRIGGER_COLLAR)
    assert close(bbox(trigger)[:2], (p.X_MIN - 2, p.TRIGGER_COLLAR.x_inner))
    assert math.isclose(bbox(trigger)[3] - bbox(trigger)[2], 3.7, abs_tol=1e-6)
    assert k.overlap(k.board(), k.parts()) == 0.0                    # they only touch
    assert math.isclose(k.overlap(k.board(), k.board()), 45 * 13 * 1.6)

def test_led_and_programming_pins_are_on_the_right_side():
    b = bbox(k.led_sightline(1.6))
    assert math.isclose((b[0] + b[1]) / 2, 27.98) and math.isclose((b[2] + b[3]) / 2, 4.7)
    pins = bbox(k.programming_pins())
    assert math.isclose(pins[4], -1.15 - 2.2) and pins[0] > 19 and pins[1] < 24
```

- [ ] **Step 2: Run** — expected: import error.
- [ ] **Step 3: Write `enclosure/keepouts.py`.**
- [ ] **Step 4: Run** `tools/dev pytest enclosure/tests -q` — expected: all pass.
- [ ] **Step 5: Commit** — `feat(enc): solids for what the shell must fit round`

---

### Task 4: Lower half

**Files:**
- Create: `enclosure/model.py`, `enclosure/tests/test_lower.py`

**Interfaces:**
- Consumes: `params`, `keepouts`.
- Produces: `model.lower() -> cadquery.Workplane` (one solid, all of it at z ≤ 0 except nothing).

What the lower half is: the bottom half of an 18 mm cylinder from `X_MIN` to `X_MAX`, with these removed:
- the board pocket: \|y\| ≤ 6.8, x from −0.3 to 45.3, from z = −1.15 up;
- the trench under the board: \|y\| ≤ 5.2, same x, from z = −2.95 up;
- the pin pocket: a rectangle covering `J3_HOLES_XY` with 1.0 mm margin, from z = −4.0 up;
- each wire chamber: a half-round of radius 5.5 between the collar and the board pocket;
- each collar's bore, leaving its two ribs standing;
- four pilot holes, 1.8 mm across and 5.5 mm deep, at `SCREW_XY`.

- [ ] **Step 1: Write the failing tests** in `enclosure/tests/test_lower.py`

```python
import math, pytest
from enclosure import keepouts as k, model, params as p

@pytest.fixture(scope="module")
def lower(): return model.lower()

def test_one_valid_solid_below_the_split(lower):
    assert lower.solids().size() == 1 and lower.val().isValid()
    b = lower.val().BoundingBox()
    assert math.isclose(b.xmin, p.X_MIN) and math.isclose(b.xmax, p.X_MAX)
    assert math.isclose(b.zmax, 0, abs_tol=1e-6) and math.isclose(b.zmin, -9.0, abs_tol=1e-3)

def test_board_drops_in_and_rests_on_both_ledges(lower):
    assert k.overlap(lower, k.board()) == 0.0
    for side in (+1, -1):          # a sliver just under each long edge of the board must be plastic
        sliver = k.box(x=(1, 44), y=sorted((side * 5.4, side * 6.4)), z=(-1.35, -1.16))
        assert math.isclose(k.overlap(lower, sliver), k.volume(sliver), rel_tol=1e-6)

def test_board_cannot_slide_endways(lower):
    for x in ((-1.3, -0.4), (45.4, 46.3)):   # plastic beyond each end of the board, at its edges
        stop = k.box(x=x, y=(5.9, 6.4), z=(-1.1, -0.1))
        assert k.overlap(lower, stop) > 0.5 * k.volume(stop)

def test_parts_and_wires_have_clearance(lower):
    assert k.overlap(lower, k.underside(0.3)) == 0.0
    assert k.overlap(lower, k.parts(0.3)) == 0.0

def test_programming_pins_have_a_pocket(lower):
    assert k.overlap(lower, k.programming_pins()) == 0.0
    # and the pocket is only under the footprint: the same pins 6 mm along the board hit the floor
    for shift in (-6, 6):
        assert k.overlap(lower, k.programming_pins().translate((shift, 0, 0))) > 0.0

def test_wire_chambers_are_open(lower):
    for collar in (p.TRIGGER_COLLAR, p.AMP_COLLAR):
        assert k.overlap(lower, k.wire_room(collar)) == 0.0

def test_each_collar_matches_its_cable(lower):
    assert k.overlap(lower, k.cable(p.TRIGGER_COLLAR, 3.7)) > 0.0     # ribs bite a 3.7 mm cable
    assert k.overlap(lower, k.cable(p.AMP_COLLAR, 4.8)) > 0.0
    assert k.overlap(lower, k.cable(p.AMP_COLLAR, 3.7)) == 0.0        # the thin cable is loose in the fat collar

def test_collar_ribs_bite_but_the_cable_passes(lower):
    for collar in (p.TRIGGER_COLLAR, p.AMP_COLLAR):
        assert k.overlap(lower, k.cable(collar, collar.rib_d - 0.02)) == 0.0     # inside the ribs: free
        bite = k.overlap(lower, k.cable(collar, collar.cable.jacket_dia))
        ring = math.pi / 4 * (collar.cable.jacket_dia ** 2 - collar.rib_d ** 2) * p.RIB_W * len(p.RIB_AT) / 2
        assert math.isclose(bite, ring, rel_tol=0.02)                             # two half-rings, nothing else

def test_screw_holes(lower):
    for xy in p.SCREW_XY:
        assert k.overlap(lower, k.screw(xy, p.PILOT_D - 0.05, -p.PILOT_DEPTH + 0.05, 0)) == 0.0
        assert k.overlap(lower, k.screw(xy, p.PILOT_D + 0.4, -p.PILOT_DEPTH + 0.05, 0)) > 0.0   # not oversize
        assert k.overlap(lower, k.screw(xy, p.PILOT_D - 0.05, -p.PILOT_DEPTH - 1.0, -p.PILOT_DEPTH - 0.1)) > 0.0  # blind
```

  `k.box(x=(x1, x2), y=(y1, y2), z=(z1, z2))` is a small helper to add to `keepouts.py` in this task: an axis-aligned box between those limits.

- [ ] **Step 2: Run** — expected: import error.
- [ ] **Step 3: Write `model.lower()`** as described above, and `k.box`.
- [ ] **Step 4: Run** `tools/dev pytest enclosure/tests -q` — expected: all pass.
- [ ] **Step 5: Commit** — `feat(enc): lower half-shell`

---

### Task 5: Upper half, and the two together

**Files:**
- Modify: `enclosure/model.py`
- Create: `enclosure/tests/test_upper.py`

**Interfaces:**
- Produces: `model.upper() -> cadquery.Workplane` (one solid at z ≥ 0).

What the upper half is: the top half of the same cylinder, with these removed:
- the cavity over the board: \|y\| ≤ 6.8, x from −0.3 to 45.3, from z = 0 up to +2.95, **except** two hold-down rails, \|y\| from 5.9 to 6.8 and x from 1 to 44, which come down to z = +0.75;
- each wire chamber and each collar bore, as in the lower half (the ribs line up with the lower half's);
- four screw clearance holes, 2.6 mm, with a 4.6 mm counterbore from z = +3.0 upward;
- the LED hole, 2.0 mm, straight up over `LED_XY`.

- [ ] **Step 1: Write the failing tests** in `enclosure/tests/test_upper.py`

```python
import math, pytest
from enclosure import keepouts as k, model, params as p

@pytest.fixture(scope="module")
def upper(): return model.upper()
@pytest.fixture(scope="module")
def lower(): return model.lower()

def test_one_valid_solid_above_the_split(upper):
    assert upper.solids().size() == 1 and upper.val().isValid()
    b = upper.val().BoundingBox()
    assert math.isclose(b.zmin, 0, abs_tol=1e-6) and math.isclose(b.zmax, 9.0, abs_tol=1e-3)

def test_halves_meet_without_overlapping(upper, lower):
    assert k.overlap(upper, lower) == 0.0
    both = upper.val().BoundingBox().add(lower.val().BoundingBox())
    assert math.isclose(both.ylen, p.OD, abs_tol=1e-3) and math.isclose(both.zlen, p.OD, abs_tol=1e-3)

def test_board_and_parts_fit_under_the_lid(upper):
    assert k.overlap(upper, k.board()) == 0.0
    assert k.overlap(upper, k.parts(0.3)) == 0.0

def test_rails_hold_the_board_down_without_touching_it(upper):
    for side in (+1, -1):
        rail = k.box(x=(2, 43), y=sorted((side * 6.0, side * 6.7)), z=(0.8, 2.9))
        assert math.isclose(k.overlap(upper, rail), k.volume(rail), rel_tol=1e-6)      # the rail is there
        gap = k.box(x=(2, 43), y=sorted((side * 6.0, side * 6.7)), z=(0.46, 0.74))
        assert k.overlap(upper, gap) == 0.0                                           # 0.3 mm above the board

def test_led_hole_is_over_the_led(upper):
    assert k.overlap(upper, k.led_sightline(p.LED_HOLE_D - 0.05)) == 0.0     # clear line of sight
    assert k.overlap(upper, k.led_sightline(p.LED_HOLE_D + 0.6)) > 0.0       # and no bigger than meant
    assert k.overlap(upper, k.led_sightline(p.LED_HOLE_D - 0.05).mirror("XZ")) > 0.0   # not mirrored

def test_upper_collars_and_chambers(upper):
    for collar in (p.TRIGGER_COLLAR, p.AMP_COLLAR):
        assert k.overlap(upper, k.wire_room(collar)) == 0.0
        assert k.overlap(upper, k.cable(collar, collar.rib_d - 0.02)) == 0.0
        assert k.overlap(upper, k.cable(collar)) > 0.0

def test_screws_pass_and_their_heads_are_sunk(upper):
    for xy in p.SCREW_XY:
        assert k.overlap(upper, k.screw(xy, p.CLEAR_D - 0.05, 0, 9)) == 0.0
        assert k.overlap(upper, k.screw(xy, p.SCREW_HEAD_D, p.SEAT_Z, 9)) == 0.0          # head goes in
        assert k.overlap(upper, k.screw(xy, p.SCREW_HEAD_D, p.SEAT_Z - 1.0, p.SEAT_Z - 0.1)) > 0.0   # and has a seat
        top = math.sqrt((p.OD / 2) ** 2 - (abs(xy[1]) + p.SCREW_HEAD_D / 2) ** 2)
        assert p.SEAT_Z + p.SCREW_HEAD_H <= top                                             # nothing sticks out

def test_nothing_else_is_cut_away(upper, lower):
    # each half keeps most of its half-cylinder: a hole in the wrong place would show as missing plastic
    half = math.pi * (p.OD / 2) ** 2 / 2 * (p.X_MAX - p.X_MIN)
    assert 0.55 * half < k.volume(lower) < 0.80 * half
    assert 0.45 * half < k.volume(upper) < 0.75 * half
```

- [ ] **Step 2: Run** — expected: `model.upper` missing.
- [ ] **Step 3: Write `model.upper()`.**
- [ ] **Step 4: Run** `tools/dev pytest enclosure/tests -q` — expected: all pass. If either volume bound in `test_nothing_else_is_cut_away` fails, print the actual volumes and check them by hand against the list of cuts before touching the bound.
- [ ] **Step 5: Commit** — `feat(enc): upper half-shell and mating checks`

---

### Task 6: Name the screws

**Files:**
- Create: `docs/enclosure.md` (first section only; Task 8 completes it)
- Modify: `enclosure/params.py` only if the screw found needs different sizes

**Interfaces:**
- Produces: a named, purchasable screw whose head fits `SCREW_HEAD_D` and `SCREW_HEAD_H`, and the pilot hole size its maker recommends for nylon.

- [ ] **Step 1: Research.** Find a thread-forming screw for plastics, about 2.2 mm thread and 8 mm long, pan head, that a UK buyer can get in small quantities (for example a PT or "Plastite"-style screw from Accu, RS, Farnell or Toolstation). Record the maker's head diameter, head height, and recommended pilot hole in PA (nylon), each with its source. If nothing suitable is found, fall back to an M2 × 8 machine screw into a 1.7 mm pilot and say so.
- [ ] **Step 2: If the figures differ from the Parameters table,** change `params.py`, run `tools/dev pytest enclosure/tests -q`, and fix whatever the tests show.
- [ ] **Step 3: Write the "Screws" section of `docs/enclosure.md`:** the part, where to buy it, the figures and their sources, and a plain statement that the pilot size is untried in JLC3DP's nylon until the first print.
- [ ] **Step 4: Commit** — `docs(enc): screw specification`

---

### Task 7: Files for JLC3DP, pictures and drawing

**Files:**
- Create: `enclosure/export.py`, `enclosure/tests/test_export.py`
- Generated in `enclosure/out/`: `lower.step`, `upper.step`, `lower.stl`, `upper.stl`, `view-lower.png`, `view-upper.png`, `view-closed.png`, `enclosure.pdf`

**Interfaces:**
- Produces: `export.main()`; run as `python -W ignore -m enclosure.export`.

- STEP and STL of each half, one solid per file, in millimetres.
- Three pictures: each half seen from its open side with hidden lines removed, and the two together. Make them with CadQuery's SVG export, then `rsvg-convert` to PNG at 1600 px wide.
- `enclosure.pdf`, made with matplotlib, three pages, each titled:
  1. Side section along the axis (the plane y = 0), both halves, with the board, a part outline 1.75 mm tall, and both cables drawn in; overall length and diameter dimensioned.
  2. Cross-sections at x = 22 (mid-board), x = −3 (trigger wire chamber) and x = 54.8 (amp-end screws), with the board and cable drawn in; wall, ledge and clearances dimensioned.
  3. Top view of the lower half: board pocket, trench, pin pocket, screw holes, with their positions dimensioned from the trigger end.
  Get each section's outline from the solid itself (for example `shape.section(...)` or a thin intersecting slab), not by redrawing the parameters, so that the drawing shows what will be printed.

- [ ] **Step 1: Write the failing tests** in `enclosure/tests/test_export.py`

```python
import pathlib, subprocess, pytest
import cadquery as cq
from enclosure import export, keepouts as k, model

OUT = pathlib.Path("enclosure/out")

@pytest.fixture(scope="module", autouse=True)
def exported(): export.main()

@pytest.mark.parametrize("name", ["lower", "upper"])
def test_step_file_holds_the_same_single_solid(name):
    back = cq.importers.importStep(str(OUT / f"{name}.step"))
    assert back.solids().size() == 1
    assert abs(k.volume(back) - k.volume(getattr(model, name)())) < 0.5

@pytest.mark.parametrize("name", ["lower", "upper"])
def test_stl_written(name):
    assert (OUT / f"{name}.stl").stat().st_size > 50_000

def test_pictures_written():
    for name in ("view-lower.png", "view-upper.png", "view-closed.png"):
        data = (OUT / name).read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) > 20_000

def test_drawing_has_three_pages():
    info = subprocess.run(["pdfinfo", str(OUT / "enclosure.pdf")], capture_output=True, text=True, check=True).stdout
    assert "Pages:           3" in info
```

- [ ] **Step 2: Run** — expected: import error.
- [ ] **Step 3: Write `enclosure/export.py`.**
- [ ] **Step 4: Run** `tools/dev pytest enclosure/tests -q` — expected: all pass.
- [ ] **Step 5: Look at every picture and every page of the PDF** (convert the PDF pages to PNG with `pdftoppm`). Check: the board sits on its ledges with daylight above the part outline; the LED hole is over the LED in the top view; the pin pocket is under the programming footprint; the two collars differ in bore and the fat one is at the amp end; dimensions are readable and do not overlap. Fix and repeat.
- [ ] **Step 6: Commit** — `feat(enc): STEP, STL, pictures and drawing`

---

### Task 8: Review document, ordering and assembly

**Files:**
- Modify: `docs/enclosure.md`, `README.md`, `docs/bring-up.md`, `docs/superpowers/specs/2026-11-10-wiim-trigger-jbl-dongle-design.md` (section 8's size and the cable note), `docs/hardware-review.md` (the row that estimates the shell's size)

- [ ] **Step 1: Complete `docs/enclosure.md`,** in this order:
  1. What it is, with the three pictures embedded and a link to `enclosure/out/enclosure.pdf`.
  2. A table of the key sizes, read from `params.py`: outside diameter and length, room above and below the board, wall at its thinnest, collar bores and rib sizes against each cable, screw and hole sizes.
  3. What the automated checks prove, and what they cannot (grip in the hand, screw holding, how JLC3DP's tolerance falls on the day).
  4. Decisions made here that the owner has not seen, each with its reason: four screws beside the cables; ribbed collars; 18 × 72 mm; the LED hole's 4.7 mm depth; the programming-pin pocket; test pads reachable only with the board lifted out.
  5. Ordering from JLC3DP: upload `lower.step` and `upper.step` as two files in one order; MJF, PA12, black; quantity 1 each (2 if a spare is wanted).
  6. Assembly: thread and solder the wires (`docs/cables.md`); at the amp end cut the six spare cores back to different lengths inside the chamber; lay the board in the lower half, parts up, trigger end at the thin collar; seat each cable jacket across both ribs of its collar; fit the upper half with the LED hole over the LED; tighten the four screws evenly until the halves meet or the collars are firm, whichever comes first.
  7. What to check on the first print, and what to change if it is wrong: screws strip (smaller pilot) or split the boss (larger pilot); halves will not close on the cable (less rib bite); cable pulls through (more rib bite); board rattles (smaller rail gap).
- [ ] **Step 2: Update the other documents** so that none still says 17–18 × 60 mm or "about 19 mm across and 65–70 mm long", and add the shell's pull test wording in `docs/bring-up.md` C4 only if it needs changing. Add `docs/enclosure.md` to the README table and `make enc`, `make enc-test` to its commands.
- [ ] **Step 3: Run everything.**

Run: `tools/dev pytest tools/tests hardware/tests enclosure/tests -q`
Expected: all pass.

- [ ] **Step 4: Commit** — `docs(enc): enclosure review, ordering and assembly`
- [ ] **Step 5: Stop and hand over to the owner** to review `docs/enclosure.md` before anything is ordered.
