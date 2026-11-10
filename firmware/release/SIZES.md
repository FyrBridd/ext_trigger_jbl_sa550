# Firmware sizes

Limits for the ATtiny412 and ATtiny402: 4096 bytes of flash; 200 bytes of static RAM (of 256, the rest is stack).

| Build | Flash | RAM | Fits |
|---|---|---|---|
| dongle-pd-id-q0-dbg | 2258 | 48 | yes |
| dongle-pd-id-q0 | 1564 | 45 | yes |
| dongle-pd-id-q1-dbg | 2244 | 48 | yes |
| dongle-pd-id-q1 | 1548 | 45 | yes |
| dongle-pd-ir-q0-dbg | 2284 | 48 | yes |
| dongle-pd-ir-q0 | 1588 | 45 | yes |
| dongle-pd-ir-q1-dbg | 2270 | 48 | yes |
| dongle-pd-ir-q1 | 1572 | 45 | yes |
| dongle-pr-id-q0-dbg | 2288 | 48 | yes |
| dongle-pr-id-q0 | 1590 | 45 | yes |
| dongle-pr-id-q1-dbg | 2274 | 48 | yes |
| dongle-pr-id-q1 | 1574 | 45 | yes |
| dongle-pr-ir-q0-dbg | 2298 | 48 | yes |
| dongle-pr-ir-q0 | 1526 | 45 | yes |
| dongle-pr-ir-q1-dbg | 2284 | 48 | yes |
| dongle-pr-ir-q1 | 1510 | 45 | yes |

The default build (dongle-pd-id-q1) also fits the ATtiny202 (2048 bytes of flash, 128 of RAM): it uses 1548 and 45.
