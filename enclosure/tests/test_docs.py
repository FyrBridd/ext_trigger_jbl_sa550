"""The review documents quote sizes from the model. These fail if a size changes and a document
is left behind."""
import math
import pathlib

from enclosure import params as p

DOCS = pathlib.Path(__file__).resolve().parents[2] / "docs"


def mm(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def one_line(name: str) -> str:
    return " ".join((DOCS / name).read_text().split())


def test_enclosure_review_quotes_the_models_sizes():
    text = one_line("enclosure.md")
    r = p.OD / 2
    tip_depth = p.SCREW_LEN - p.SEAT_Z
    for phrase in [
        f"{mm(p.OD)} diameter × {mm(p.X_MAX - p.X_MIN)} long",
        f"{mm(2 * p.POCKET_HALF_W)} × {mm(p.BOARD_L + 2 * p.GAP)}",
        f"bore {mm(p.TRIGGER_COLLAR.bore_d)}, ribs {mm(p.TRIGGER_COLLAR.rib_d)}",
        f"bore {mm(p.AMP_COLLAR.bore_d)}, ribs {mm(p.AMP_COLLAR.rib_d)}",
        f"modelled {mm(p.PILOT_D)} mm, {mm(p.PILOT_DEPTH)} mm deep",
        f"{mm(p.CBORE_D)} mm counterbore",
        f"{mm(p.PILOT_RELIEF_D)} mm across, {mm(p.PILOT_RELIEF_DEPTH)} mm deep",
        # plastic round the thread: to the amp cable's bore, and to the outside at the screw tip's depth
        f"{mm(p.SCREW_Y - p.PILOT_D / 2 - p.AMP_COLLAR.bore_d / 2)} to the cable bore",
        f"{mm(r - math.hypot(p.SCREW_Y + p.PILOT_D / 2, tip_depth))} to the outside",
        f"{mm(p.FREE_CORE)} mm of each core",
        f"{mm(p.LID_KEY)} mm longer",
    ]:
        assert phrase in text, phrase


def test_soldering_instructions_give_the_free_core_length():
    # the cables are soldered during bring-up, before the shell is fitted: the length has to be there
    for name in ("bring-up.md", "cables.md"):
        assert f"{mm(p.FREE_CORE)} mm of each core" in one_line(name), name


def test_documents_do_not_claim_what_the_model_does_not_do():
    text = one_line("enclosure.md")
    assert "More than 1.5 mm of plastic round every screw bore" not in text
    assert "past the inner rib" not in text
