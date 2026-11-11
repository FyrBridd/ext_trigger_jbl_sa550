# WiiM trigger to JBL SA550 serial dongle

A small inline board, powered by a WiiM Ultra's 12 V trigger output, that keeps
a JBL SA550 Classic amplifier switched on and on its STB input over RS232.

**Status (2026-11-11):** board designed and checked, firmware written and
tested against a simulated amp, enclosure designed and checked against the
board and cables. Nothing has been ordered, printed or run on hardware.

## Where to look

| To | Read |
|---|---|
| Review the board before ordering | `docs/hardware-review.md` |
| See the schematic and board | `hardware/fab/schematic.pdf`, `hardware/fab/board.pdf` |
| Check the sums | `docs/hardware-calculations.md` |
| Order from JLCPCB | `docs/hardware-review.md`, section 6 |
| Buy the two cables | `docs/cables.md` |
| Review, order and assemble the enclosure | `docs/enclosure.md`, `enclosure/out/enclosure.pdf` |
| Flash the chip | `docs/flashing.md` |
| Get the first board working | `docs/bring-up.md` |
| Understand the amp's protocol | `docs/research.md` |
| Understand the design decisions | `docs/superpowers/specs/2026-11-10-wiim-trigger-jbl-dongle-design.md` |

## Working on it

All tools (KiCad 10, the AVR compiler, CadQuery, the tests) run in a Docker container.
Run everything through the wrapper `tools/dev`, or use the make targets:

| Command | Does |
|---|---|
| `make hw` | Regenerates the schematic, board and JLCPCB files from `hardware/design/` |
| `make hw-test` | Checks them: KiCad rule checks, schematic against board, files against the circuit |
| `make stock` | Checks every part is in stock at JLCPCB |
| `make fw-test` | Runs the firmware's tests on this machine, against a simulated amp |
| `make fw` | Builds the 16 firmware files in `firmware/release/` |
| `make route` | Re-runs the board autorouter (only after changing the circuit or placement) |
| `make enc` | Regenerates the enclosure's STEP and STL files, pictures and drawing in `enclosure/out/` |
| `make enc-test` | Checks the enclosure fits the board, cables and screws |

The circuit lives in `hardware/design/circuit.py`, the board placement in
`hardware/design/layout.py`, the firmware in `firmware/src/`, the enclosure
in `enclosure/params.py` and `enclosure/model.py`. Files under
`hardware/dongle/`, `hardware/fab/` and `enclosure/out/` are generated; do
not edit them.
