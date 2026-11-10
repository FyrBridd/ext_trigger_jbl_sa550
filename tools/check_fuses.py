"""Refuse a firmware hex file whose fuse settings are not the ones this project expects.

    python tools/check_fuses.py <file.hex> [...]

The fuse bytes sit in the hex file at address 0x820000 (Microchip's convention
for AVR parts). The check that matters most: SYSCFG0 must leave pin PA0 as
UPDI. Programming it as GPIO or reset would lock the programmer out.
Exit status 0 if every file passes, 1 otherwise.
"""
import pathlib
import sys

FUSE_BASE = 0x820000

# index: (name, expected value, why)
EXPECTED = {
    0: ("WDTCFG", 0x0A, "watchdog always on, 4 s"),
    1: ("BODCFG", 0x44, "brown-out detector on while running, 2.6 V"),
    2: ("OSCCFG", 0x02, "20 MHz oscillator"),
    4: ("TCD0CFG", 0x00, "default"),
    5: ("SYSCFG0", 0xF6, "PA0 stays UPDI; EEPROM erased with chip erase"),
    6: ("SYSCFG1", 0x07, "64 ms start-up time"),
    7: ("APPEND", 0x00, "default"),
    8: ("BOOTEND", 0x00, "default"),
}
RSTPINCFG_MASK, RSTPINCFG_UPDI = 0x0C, 0x04


def read_hex(path) -> dict[int, int]:
    """Absolute address -> byte, from an Intel HEX file."""
    memory, upper = {}, 0
    for line in pathlib.Path(path).read_text().splitlines():
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


def write_test_hex(path, blocks: dict[int, bytes]) -> None:
    """Write blocks of bytes at absolute addresses as Intel HEX (for the tests)."""
    def record(kind, address, payload):
        body = bytes([len(payload), (address >> 8) & 0xFF, address & 0xFF, kind]) + payload
        return ":" + (body + bytes([(-sum(body)) & 0xFF])).hex().upper()

    lines = []
    for base, data in blocks.items():
        lines.append(record(0x04, 0, bytes([(base >> 24) & 0xFF, (base >> 16) & 0xFF])))
        for offset in range(0, len(data), 16):
            lines.append(record(0x00, (base + offset) & 0xFFFF, data[offset:offset + 16]))
    lines.append(record(0x01, 0, b""))
    pathlib.Path(path).write_text("\n".join(lines) + "\n")


def check(path) -> list[str]:
    """Problems found with the file's fuses; an empty list means it passes."""
    memory = read_hex(path)
    if not any(FUSE_BASE <= a < FUSE_BASE + 16 for a in memory):
        return [f"no fuse records at 0x{FUSE_BASE:06X}"]
    problems = []
    for index, (name, expected, why) in EXPECTED.items():
        actual = memory.get(FUSE_BASE + index)
        if actual is None:
            problems.append(f"{name} is missing")
        elif name == "SYSCFG0" and actual & RSTPINCFG_MASK != RSTPINCFG_UPDI:
            problems.append(f"SYSCFG0 is 0x{actual:02X}: PA0 would no longer be UPDI and the "
                            f"programmer would be locked out")
        elif actual != expected:
            problems.append(f"{name} is 0x{actual:02X}, expected 0x{expected:02X} ({why})")
    return problems


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 1
    failed = False
    for path in argv:
        for problem in check(path):
            print(f"{path}: {problem}", file=sys.stderr)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
