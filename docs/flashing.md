# Flashing the dongle

**None of this has been tried on real hardware yet.** The hex files build and
pass their checks; the steps below are from Microchip's and Tag-Connect's
documentation. Correct this file when the first board is flashed.

## What you need

- MPLAB ICD 5.
- Tag-Connect TC2030-MCP-NL cable. Its RJ12 plug goes straight into the
  ICD 5's jack; its spring pins press onto the six-pad footprint on the top
  of the board (centre 21.4 mm from the trigger end). The single alignment
  pin is at the bottom edge side of the footprint, the pair at the top.
- Power for the board: the WiiM's trigger, or a 12 V bench supply on the
  `+` and `G` wire pads. The ICD 5 only senses the 3.3 V; it does not need to
  supply it.
- A hex file from `firmware/release/`.

## Which file

File names are `dongle-p?-i?-q?[-dbg].hex`:

| Part | Meaning |
|---|---|
| `pd` / `pr` | Power-on is sent as the direct command / as a simulated remote-control code |
| `id` / `ir` | Select-STB is sent as the direct command / as a simulated remote-control code |
| `q1` / `q0` | The input is queried before selecting / never queried (STB is selected once after waking) |
| `-dbg` | Debug build: copies the amp's replies to test pad PA1 and logs them in the EEPROM |

Start with `dongle-pd-id-q1-dbg.hex`. `docs/bring-up.md` says when to try
another. Sizes are in `firmware/release/SIZES.md`.

## With MPLAB IPE on a desktop

1. Device: `ATtiny412`. Tool: the ICD 5. Connect.
2. If asked for the interface, choose UPDI. Leave high-voltage activation off.
3. Leave "power target from tool" off when the board has its own 12 V.
4. Load the hex file and press Program. This erases the chip first, which
   also clears the EEPROM log.
5. Fuses: the hex file contains them. Whether IPE applies them without being
   told to is not confirmed. After programming, read the device back and
   compare the fuse values with `firmware/FUSES.md`; set them by hand if they
   differ. **Do not change SYSCFG0.**

## From the command line on the Linux box

Not tested. It needs MPLAB X installed, which needs the sudo password once.

1. Install MPLAB X v6.35 without its GUI:
   `sudo ./MPLABX-v6.35-linux-installer.sh --nox11 -- --unattendedmodeui none --mode unattended --ipe 1 --collectInfo 0`
   - Microchip has a support article about this installer failing a checksum
     on recent Ubuntu, because Ubuntu's replacement `md5sum` behaves
     differently. The published workaround is to install GNU coreutils. This
     box has the same replacement tools, so expect to need it.
2. Find the tool: `find /opt/microchip -name ipecmd.sh`
3. Program: `ipecmd.sh -TPICD5 -PATtiny412 -ORIUPDI -M -F<file.hex> -OL`
4. Read the chip back to a file: add `-GF<output.hex>`.

If this route does not work, flash from a desktop with hex files built here.

## Reading the debug log back

1. Read the device with the ICD 5 (IPE: Read, then File > Export > Hex; or
   `-GF` above). Do this **before** programming again, which erases the log.
2. `tools/dev python tools/decode_eeprom.py <that file>`

It accepts an Intel HEX file with the EEPROM at address 0x810000 (Microchip's
convention) or at 0, or a raw 128-byte dump. If it prints "no log found", the
EEPROM was blank or the chip was running a build without `-dbg`.

## Rebuilding the firmware

| Command | Does |
|---|---|
| `make fw-test` | Runs every host test: protocol, controller, and whole-loop scenarios against a simulated amp. |
| `make fw` | Rebuilds all 16 hex files, and checks their size and fuses. |

Timings (poll interval, timeouts) are in `firmware/src/config.h`.
