"""Print the debug reply log from a dump of the dongle's EEPROM.

    python tools/decode_eeprom.py <file>

<file> is the EEPROM read back from a dongle running a debug build: either raw
bytes, or an Intel HEX file with the EEPROM at address 0 or at 0x810000 (where
Microchip's tools put it). The layout is described in firmware/src/dbglog.h.
"""
import pathlib
import sys

MAGIC, VERSION = 0xD5, 0x01
BASE, BUCKET_SIZE, RECORDS, RECORD_SIZE = 4, 20, 3, 6
BUCKETS = ["power_query", "power_on", "input_query", "select_stb", "unsolicited"]
TITLES = {
    "power_query": "Power query (21 01 00 01 F0 0D)",
    "power_on": "Power on",
    "input_query": "Input query (21 01 1D 01 F0 0D)",
    "select_stb": "Select STB",
    "unsolicited": "Frames the amp sent without being asked",
}
EEPROM_SIZE = 128
MICROCHIP_EEPROM_BASE = 0x810000

ANSWERS = {
    0x00: "ok",
    0x82: "zone invalid",
    0x83: "command not recognised",
    0x84: "parameter not recognised",
    0x85: "command invalid at this time",
    0x86: "invalid data length",
}
COMMANDS = {0x00: "power", 0x08: "simulated remote control", 0x1D: "input"}
INPUTS = {1: "Phono", 2: "AUX", 3: "PVR", 4: "AV", 5: "STB", 6: "CD", 7: "BD", 8: "SAT"}


def _parse_ihex(text: str) -> dict[int, int]:
    memory, upper = {}, 0
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith(":"):
            continue
        raw = bytes.fromhex(line[1:])
        count, address, kind, data = raw[0], (raw[1] << 8) | raw[2], raw[3], raw[4:4 + raw[0]]
        if kind == 0x00:
            for i, byte in enumerate(data):
                memory[upper + address + i] = byte
        elif kind == 0x04:
            upper = ((data[0] << 8) | data[1]) << 16
        elif kind == 0x02:
            upper = ((data[0] << 8) | data[1]) << 4
        elif kind == 0x01:
            break
    return memory


def load(path) -> bytes:
    """The 128 EEPROM bytes from a raw dump or an Intel HEX file."""
    raw = pathlib.Path(path).read_bytes()
    if not raw.lstrip().startswith(b":"):
        return raw[:EEPROM_SIZE].ljust(EEPROM_SIZE, b"\xff")
    memory = _parse_ihex(raw.decode("ascii", errors="replace"))
    base = MICROCHIP_EEPROM_BASE if any(a >= MICROCHIP_EEPROM_BASE for a in memory) else 0
    return bytes(memory.get(base + i, 0xFF) for i in range(EEPROM_SIZE))


def to_ihex(data: bytes, base: int, path) -> pathlib.Path:
    """Write bytes as Intel HEX at `base` (used by the tests to make sample files)."""
    def record(kind, address, payload):
        body = bytes([len(payload), (address >> 8) & 0xFF, address & 0xFF, kind]) + payload
        return ":" + (body + bytes([(-sum(body)) & 0xFF])).hex().upper()

    lines = [record(0x04, 0, bytes([(base >> 24) & 0xFF, (base >> 16) & 0xFF]))]
    for offset in range(0, len(data), 16):
        lines.append(record(0x00, (base + offset) & 0xFFFF, data[offset:offset + 16]))
    lines.append(record(0x01, 0, b""))
    path = pathlib.Path(path)
    path.write_text("\n".join(lines) + "\n")
    return path


def decode(data: bytes) -> dict:
    if len(data) < BASE + BUCKET_SIZE * len(BUCKETS) or data[0] != MAGIC or data[1] != VERSION:
        return {"error": "no log found (EEPROM blank or not a debug build)"}
    log = {"boots": data[2]}
    for k, name in enumerate(BUCKETS):
        at = BASE + BUCKET_SIZE * k
        records = []
        for i in range(min(data[at + 1], RECORDS)):
            rec = data[at + 2 + RECORD_SIZE * i: at + 2 + RECORD_SIZE * (i + 1)]
            records.append({"cmd": rec[0], "answer": rec[1], "data": list(rec[3:3 + min(rec[2], 3)])})
        log[name] = {"timeouts": data[at], "records": records}
    return log


def _describe(record: dict) -> str:
    cmd, answer, data = record["cmd"], record["answer"], record["data"]
    text = f"command 0x{cmd:02X} ({COMMANDS.get(cmd, 'other')}), answer 0x{answer:02X} " \
           f"({ANSWERS.get(answer, 'unknown')}), data [{' '.join(f'{b:02X}' for b in data)}]"
    if answer == 0 and data:
        if cmd == 0x00:
            text += " = " + {0: "standby", 1: "on"}.get(data[0], "?")
        elif cmd == 0x1D:
            name = INPUTS.get(data[0] & 0x0F, "?")
            text += f" = {name}" + (", processor mode" if data[0] & 0x10 else "")
    return text


def render(log: dict) -> str:
    if "error" in log:
        return log["error"] + "\n"
    lines = [f"Debug reply log: the dongle has started {log['boots']} time(s) since it was flashed.", ""]
    for name in BUCKETS:
        bucket = log[name]
        lines.append(TITLES[name])
        if name != "unsolicited":
            lines.append(f"  went unanswered {bucket['timeouts']} time(s)" + (" or more" if bucket["timeouts"] == 255 else ""))
        if not bucket["records"]:
            lines.append("  no frames recorded")
        for record in bucket["records"]:
            lines.append("  " + _describe(record))
        lines.append("")
    lines.append("Each section keeps the first three different frames it saw.")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__)
        return 2
    print(render(decode(load(argv[0]))), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
