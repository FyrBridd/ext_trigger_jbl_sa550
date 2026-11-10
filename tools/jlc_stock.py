"""Check that every part on the bill of materials is in stock at JLCPCB.

    python tools/jlc_stock.py --bom hardware/fab/bom.csv [--min-stock 200] [--report FILE]

Exit status: 0 every part found with enough stock; 1 a part is missing or short;
2 JLCPCB's parts service could not be reached or its reply was not understood.

Run it again on the day of ordering. It uses the search service behind
JLCPCB's parts web page, which is unofficial and may change without notice;
status 2 means "could not check", not "out of stock". Only the part number is
sent.
"""
import argparse
import csv
import datetime
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass

API = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"

# Controllers that fit the same footprint, reported for information only.
ALTERNATES = [("C616056", "ATtiny402-SSNR, same 4 KB flash"), ("C2052951", "ATtiny202-SSNR, only 2 KB flash")]


class ApiError(Exception):
    """JLCPCB's parts service did not give a usable answer."""


@dataclass(frozen=True)
class Component:
    lcsc: str
    model: str
    package: str
    library_type: str   # "base" (no fee) or "expand" (extended: one-off fee per order)
    preferred: bool
    stock: int


@dataclass(frozen=True)
class Result:
    lcsc: str
    designators: str
    comment: str
    component: Component | None
    ok: bool


def fetch(lcsc: str) -> dict:
    body = json.dumps({"keyword": lcsc, "currentPage": 1, "pageSize": 25}).encode()
    request = urllib.request.Request(API, data=body, headers={
        "Content-Type": "application/json", "Accept": "application/json", "User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=40) as reply:
            return json.load(reply)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        raise ApiError(f"no usable reply for {lcsc}: {e}") from e


def parse_component(api_json: dict, lcsc: str) -> Component | None:
    """The entry for exactly this part number, or None if JLCPCB does not list it."""
    try:
        entries = api_json["data"]["componentPageInfo"]["list"] or []
    except (KeyError, TypeError) as e:
        raise ApiError(f"unexpected reply shape for {lcsc}: {str(api_json)[:120]}") from e
    for entry in entries:   # the search also returns near matches
        if entry.get("componentCode") == lcsc:
            return Component(lcsc, entry.get("componentModelEn") or "", entry.get("componentSpecificationEn") or "",
                             entry.get("componentLibraryType") or "", bool(entry.get("preferredComponentFlag")),
                             int(entry.get("stockCount") or 0))
    return None


def check(bom_rows, fetcher, min_stock: int) -> list[Result]:
    results = []
    for row in bom_rows:
        lcsc = row["LCSC Part #"]
        component = parse_component(fetcher(lcsc), lcsc)
        ok = component is not None and component.stock >= min_stock
        results.append(Result(lcsc, row.get("Designator", ""), row.get("Comment", ""), component, ok))
    return results


def _kind(component: Component) -> str:
    if component.library_type == "base":
        return "Basic"
    return "Preferred extended" if component.preferred else "Extended"


def report(results, min_stock: int, alternates) -> str:
    today = datetime.date.today().isoformat()
    verdict = "all parts in stock" if all(r.ok for r in results) else "NOT ENOUGH STOCK for at least one part"
    lines = [f"# JLCPCB stock check, {today}", "",
             f"Result: **{verdict}** (minimum {min_stock} of each).", "",
             "| LCSC | Part | Fitted as | Kind | In stock | Enough |", "|---|---|---|---|---|---|"]
    for r in results:
        if r.component is None:
            lines.append(f"| {r.lcsc} | not listed by JLCPCB | {r.designators} | | 0 | **no** |")
        else:
            c = r.component
            lines.append(f"| {r.lcsc} | {c.model} ({c.package}) | {r.designators} | {_kind(c)} | "
                         f"{c.stock:,} | {'yes' if r.ok else '**no**'} |")
    if alternates:
        lines += ["", "Alternate controllers for the same footprint (not on the bill of materials):", "",
                  "| LCSC | Part | In stock |", "|---|---|---|"]
        for lcsc, note, component in alternates:
            stock = f"{component.stock:,}" if component else "not listed"
            lines.append(f"| {lcsc} | {note} | {stock} |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    args = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    args.add_argument("--bom", required=True)
    args.add_argument("--min-stock", type=int, default=200)
    args.add_argument("--report")
    opts = args.parse_args(argv)
    with open(opts.bom, newline="") as f:
        rows = list(csv.DictReader(f))
    try:
        results = check(rows, fetch, opts.min_stock)
        alternates = [(lcsc, note, parse_component(fetch(lcsc), lcsc)) for lcsc, note in ALTERNATES]
    except ApiError as e:
        print(f"Could not check stock: {e}", file=sys.stderr)
        return 2
    text = report(results, opts.min_stock, alternates)
    print(text)
    if opts.report:
        with open(opts.report, "w") as f:
            f.write(text)
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
