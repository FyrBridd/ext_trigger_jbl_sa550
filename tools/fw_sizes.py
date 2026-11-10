"""Check firmware builds against the controller's memory and write a size table.

    python tools/fw_sizes.py --out firmware/release/SIZES.md build/avr/*.elf

Every build must fit the ATtiny412 and ATtiny402: 4096 bytes of flash and 256
bytes of RAM, of which at least 56 are left for the stack. The default release
build is also reported against the ATtiny202's 2048 bytes. Exit status 1 if
any build is too big.
"""
import argparse
import pathlib
import subprocess
import sys

FLASH_LIMIT, RAM_LIMIT, RAM_TOTAL = 4096, 200, 256
SMALL_FLASH, SMALL_RAM_TOTAL = 2048, 128
DEFAULT_BUILD = "dongle-pd-id-q1"


def sizes(elf) -> tuple[int, int]:
    """(flash bytes, static RAM bytes) of an ELF file."""
    out = subprocess.run(["avr-size", "-A", str(elf)], capture_output=True, text=True, check=True).stdout
    section = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[1].isdigit():
            section[parts[0]] = int(parts[1])
    flash = section.get(".text", 0) + section.get(".data", 0) + section.get(".rodata", 0)
    ram = section.get(".data", 0) + section.get(".bss", 0)
    return flash, ram


def main(argv=None) -> int:
    args = argparse.ArgumentParser()
    args.add_argument("--out", required=True)
    args.add_argument("elfs", nargs="+")
    opts = args.parse_args(argv)
    rows, failed = [], False
    for elf in sorted(opts.elfs):
        name = pathlib.Path(elf).stem
        flash, ram = sizes(elf)
        ok = flash <= FLASH_LIMIT and ram <= RAM_LIMIT
        failed |= not ok
        rows.append((name, flash, ram, ok))
    lines = ["# Firmware sizes", "",
             f"Limits for the ATtiny412 and ATtiny402: {FLASH_LIMIT} bytes of flash; {RAM_LIMIT} bytes of "
             f"static RAM (of {RAM_TOTAL}, the rest is stack).", "",
             "| Build | Flash | RAM | Fits |", "|---|---|---|---|"]
    lines += [f"| {n} | {f} | {r} | {'yes' if ok else '**NO**'} |" for n, f, r, ok in rows]
    for name, flash, ram, _ in rows:
        if name == DEFAULT_BUILD:
            fits = flash <= SMALL_FLASH and ram <= SMALL_RAM_TOTAL - 56
            lines += ["", f"The default build ({name}) {'also fits' if fits else 'does not fit'} the ATtiny202 "
                          f"({SMALL_FLASH} bytes of flash, {SMALL_RAM_TOTAL} of RAM): it uses {flash} and {ram}."]
    pathlib.Path(opts.out).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
