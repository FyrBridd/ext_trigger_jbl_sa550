import json
import pathlib

import pytest

from tools import jlc_stock as j

FIX = json.loads((pathlib.Path(__file__).parent / "fixtures/jlc_C1337190.json").read_text())


def test_parse_exact_match():
    comp = j.parse_component(FIX, "C1337190")
    assert comp.model == "ATTINY412-SSNR" and comp.package == "SOIC-8"
    assert comp.library_type == "expand" and comp.stock > 0


def test_parse_ignores_near_matches():
    assert j.parse_component(FIX, "C133719") is None


def bom(*codes):
    return [{"LCSC Part #": c, "Designator": "X1", "Comment": "part"} for c in codes]


def reply(code, stock, library="base"):
    return {"data": {"componentPageInfo": {"list": [
        {"componentCode": code, "componentModelEn": "M", "componentSpecificationEn": "P",
         "componentLibraryType": library, "preferredComponentFlag": False, "stockCount": stock}]}}}


def test_check_passes_and_fails_on_threshold():
    fetcher = lambda code: reply(code, 150)  # noqa: E731
    assert all(r.ok for r in j.check(bom("C1"), fetcher, min_stock=100))
    assert not any(r.ok for r in j.check(bom("C1"), fetcher, min_stock=200))


def test_check_fails_when_part_missing():
    fetcher = lambda code: {"data": {"componentPageInfo": {"list": []}}}  # noqa: E731
    assert [r.ok for r in j.check(bom("C1"), fetcher, min_stock=1)] == [False]


def test_malformed_reply_is_an_api_error():
    with pytest.raises(j.ApiError):
        j.check(bom("C1"), lambda code: {"code": 500}, min_stock=1)


def test_report_names_every_part_and_the_verdict():
    results = j.check(bom("C1", "C2"), lambda code: reply(code, 5 if code == "C2" else 5000), min_stock=200)
    text = j.report(results, min_stock=200, alternates=[])
    assert "C1" in text and "C2" in text
    assert "NOT ENOUGH STOCK" in text and "| C2 |" in text


def test_main_exit_codes(tmp_path, monkeypatch):
    bom_file = tmp_path / "bom.csv"
    bom_file.write_text('Comment,Designator,Footprint,LCSC Part #\npart,X1,F,C1\n')
    monkeypatch.setattr(j, "fetch", lambda code: reply(code, 5000))
    assert j.main(["--bom", str(bom_file), "--report", str(tmp_path / "r.md")]) == 0
    assert "C1" in (tmp_path / "r.md").read_text()
    monkeypatch.setattr(j, "fetch", lambda code: reply(code, 3))
    assert j.main(["--bom", str(bom_file)]) == 1

    def down(code):
        raise j.ApiError("no reply")
    monkeypatch.setattr(j, "fetch", down)
    assert j.main(["--bom", str(bom_file)]) == 2
