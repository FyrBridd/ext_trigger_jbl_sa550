# Fuse settings (ATtiny412)

The fuses are part of every hex file in `firmware/release/`, at address
0x820000, and `tools/check_fuses.py` refuses a build whose fuses differ from
this table. Whether your programming tool applies fuse records from the hex
file automatically has not been tested; if it does not, enter these values by
hand.

| Fuse | Value | Meaning |
|---|---|---|
| WDTCFG | `0x0A` | Watchdog always on, 4 s. A hung controller restarts itself. |
| BODCFG | `0x44` | Brown-out detector on while running, at 2.6 V. The controller resets cleanly as the trigger supply collapses. |
| OSCCFG | `0x02` | 20 MHz internal oscillator (factory default). The firmware runs it divided by 6. |
| TCD0CFG | `0x00` | Factory default. |
| SYSCFG0 | `0xF6` | Factory default: pin PA0 is UPDI; the EEPROM is erased by a chip erase. |
| SYSCFG1 | `0x07` | Factory default: 64 ms start-up time. |
| APPEND | `0x00` | Factory default. |
| BOOTEND | `0x00` | Factory default. |

**Never change SYSCFG0 bits 3:2.** They choose what pin PA0 is. Anything but
UPDI (`01`) there stops the programmer from talking to the chip, and it can
only be recovered with a 12 V programming pulse that this board is not wired
for.

Only WDTCFG and BODCFG differ from a blank chip.
