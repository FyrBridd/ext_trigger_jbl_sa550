"""Thin helpers around kicad-cli: run a check or export, and parse what comes back."""
import json
import pathlib
import subprocess
import tempfile


def _cli(*args) -> str:
    done = subprocess.run(["kicad-cli", *map(str, args)], capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"kicad-cli {' '.join(map(str, args))} failed:\n{done.stdout}\n{done.stderr}")
    return done.stdout


# --- s-expression reading (KiCad netlists) ---------------------------------

class Q(str):
    """A string that was quoted in the s-expression (as opposed to a bare token)."""


def parse_sexpr(text: str):
    """Parse one s-expression into nested lists. Quoted strings come back as Q,
    bare tokens as plain str, so the tree can be written out again unchanged."""
    pos = 0
    n = len(text)

    def read():
        nonlocal pos
        while pos < n and text[pos].isspace():
            pos += 1
        if text[pos] == "(":
            pos += 1
            items = []
            while True:
                while pos < n and text[pos].isspace():
                    pos += 1
                if text[pos] == ")":
                    pos += 1
                    return items
                items.append(read())
        if text[pos] == '"':
            pos += 1
            out = []
            while text[pos] != '"':
                ch = text[pos]
                if ch == "\\":
                    pos += 1
                    ch = "\n" if text[pos] == "n" else text[pos]
                out.append(ch)
                pos += 1
            pos += 1
            return Q("".join(out))
        start = pos
        while pos < n and not text[pos].isspace() and text[pos] not in "()":
            pos += 1
        return text[start:pos]

    return read()


def dump_sexpr(node, depth: int = 0) -> str:
    """Write a tree from parse_sexpr back out as text KiCad can read."""
    if isinstance(node, Q):
        return '"' + node.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    if isinstance(node, str):
        return node
    if all(not isinstance(x, list) for x in node):
        return "(" + " ".join(dump_sexpr(x) for x in node) + ")"
    pad = "\t" * (depth + 1)
    head = [dump_sexpr(x) for x in node if not isinstance(x, list)]
    body = [pad + dump_sexpr(x, depth + 1) for x in node if isinstance(x, list)]
    return "(" + " ".join(head) + "\n" + "\n".join(body) + "\n" + "\t" * depth + ")"


def _children(node, name):
    return [x for x in node if isinstance(x, list) and x and x[0] == name]


def _child(node, name):
    found = _children(node, name)
    return found[0] if found else None


def _value(node, name, default=""):
    child = _child(node, name)
    return child[1] if child and len(child) > 1 and isinstance(child[1], str) else default


def _netlist_tree(sch_path):
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp) / "netlist.net"
        _cli("sch", "export", "netlist", "--format", "kicadsexpr", "-o", out, sch_path)
        return parse_sexpr(out.read_text())


# --- schematic ---------------------------------------------------------------

def erc(sch_path) -> list[dict]:
    """Every ERC violation, as dicts with at least type, severity and description."""
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp) / "erc.json"
        _cli("sch", "erc", "--format", "json", "--severity-all", "-o", out, sch_path)
        report = json.loads(out.read_text())
    return [v for sheet in report.get("sheets", []) for v in sheet.get("violations", [])]


def export_netlist(sch_path) -> dict[str, set[tuple[str, str]]]:
    """Net name -> set of (reference, pin number), as KiCad itself sees the schematic."""
    tree = _netlist_tree(sch_path)
    nets = {}
    for net in _children(_child(tree, "nets"), "net"):
        pins = {(_value(node, "ref"), _value(node, "pin")) for node in _children(net, "node")}
        nets[_value(net, "name")] = pins
    return nets


def symbol_fields(sch_path) -> dict[str, dict[str, str]]:
    """Reference -> {field name: value}, always including Value and Footprint."""
    tree = _netlist_tree(sch_path)
    out = {}
    for comp in _children(_child(tree, "components"), "comp"):
        fields = {"Value": _value(comp, "value"), "Footprint": _value(comp, "footprint")}
        for field in _children(_child(comp, "fields") or [], "field"):
            name = _value(field, "name")
            text = [x for x in field[1:] if isinstance(x, str)]
            if name and text:
                fields[name] = text[0]
        out[_value(comp, "ref")] = fields
    return out


def export_pdf(sch_path, out_path) -> None:
    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    _cli("sch", "export", "pdf", "-o", out_path, sch_path)


# --- board -----------------------------------------------------------------

def drc(pcb_path, parity: bool = False) -> dict:
    """KiCad's design rule check report: violations, unconnected_items, schematic_parity."""
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp) / "drc.json"
        extra = ["--schematic-parity"] if parity else []
        _cli("pcb", "drc", "--format", "json", "--severity-all", *extra, "-o", out, pcb_path)
        report = json.loads(out.read_text())
    for key in ("violations", "unconnected_items", "schematic_parity"):
        report.setdefault(key, [])
    return report


def refill_zones(pcb_path) -> None:
    """Fill the board's copper pours with KiCad's own filler and save the result."""
    with tempfile.TemporaryDirectory() as tmp:
        _cli("pcb", "drc", "--refill-zones", "--save-board", "--format", "json",
             "-o", pathlib.Path(tmp) / "drc.json", pcb_path)


def render(pcb_path, out_png, side: str = "top", width: int = 1800, height: int = 700) -> None:
    """A 3D-style picture of the board from one side."""
    pathlib.Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    _cli("pcb", "render", "--side", side, "--width", width, "--height", height,
         "--quality", "basic", "-o", out_png, pcb_path)
