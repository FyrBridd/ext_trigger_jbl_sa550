# Firmware sizes

Limits for the ATtiny412 and ATtiny402: 4096 bytes of flash; 200 bytes of static RAM (of 256, the rest is stack).

| Build | Flash | RAM | Fits |
|---|---|---|---|
| dongle-pd-id-q0-dbg | 2446 | 52 | yes |
| dongle-pd-id-q0 | 1808 | 49 | yes |
| dongle-pd-id-q1-dbg | 2364 | 52 | yes |
| dongle-pd-id-q1 | 1718 | 49 | yes |
| dongle-pd-ir-q0-dbg | 2472 | 52 | yes |
| dongle-pd-ir-q0 | 1832 | 49 | yes |
| dongle-pd-ir-q1-dbg | 2390 | 52 | yes |
| dongle-pd-ir-q1 | 1742 | 49 | yes |
| dongle-pr-id-q0-dbg | 2474 | 52 | yes |
| dongle-pr-id-q0 | 1838 | 49 | yes |
| dongle-pr-id-q1-dbg | 2392 | 52 | yes |
| dongle-pr-id-q1 | 1748 | 49 | yes |
| dongle-pr-ir-q0-dbg | 2486 | 52 | yes |
| dongle-pr-ir-q0 | 1804 | 49 | yes |
| dongle-pr-ir-q1-dbg | 2404 | 52 | yes |
| dongle-pr-ir-q1 | 1716 | 49 | yes |

The default build (dongle-pd-id-q1) also fits the ATtiny202 (2048 bytes of flash, 128 of RAM): it uses 1718 and 49.
