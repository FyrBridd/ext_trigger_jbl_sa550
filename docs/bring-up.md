# Bring-up procedure

A step-by-step procedure for getting the first dongle working, written to be
followed alone. **It has not been run: no board exists yet.** Where a step
says "expect", that is what the design predicts, not something observed.
Please note what actually happens and correct this file.

You need: a multimeter, a scope (two channels with serial decode helps), the
ICD 5 with the TC2030-MCP-NL cable, the two cut cables, and
`docs/flashing.md`.

Board reference (top view, trigger end on the left):

- Trigger wire pads, left end: `+` (upper) and `G` (lower).
- Amp wire pads, right end: `G` (upper), `R` (middle), `T` (lower). Under
  the board they are labelled `5 GND`, `3 RX`, `2 TX`: the DB9 pin each goes
  to.
- Test pads are underneath, each labelled: `VIN`, `3V3`, `GND`, `TXL`,
  `RXL`, `UPDI`, `PA1`, `PA2`.
- LED patterns: **fast blink** (about 4 a second) = the amp is not
  answering; **slow blink** (about 1 a second) = the amp answers but is not
  yet on and on STB; **solid** = amp on and on STB.

## Part A — before the board exists

### A1. Trigger polarity

- **Do:** With the WiiM playing, measure across the tip and sleeve of a
  3.5 mm plug in its trigger socket.
- **Expect:** about +12 V on the tip relative to the sleeve.
- **If not:** note which is positive. The positive wire goes to `+`.
- **Why it matters:** swapped wires would short the WiiM's trigger output
  through the system's shared ground once the serial cable is connected.

### A2. Amp setting

- **Do:** In the SA550's menu, set "RS232 Stdby" to On.
- **Why:** it is Off by default, and the amp then ignores the port in
  standby, so the dongle could never wake it.

### A3. Which pin the amp transmits on

- **Do:** With the amp on (or in standby with A2 done), measure DB9 pins 2
  and 3 against pin 5 on the amp's socket.
- **Expect:** pin 3 sits at a steady negative voltage (roughly −5 to −10 V);
  pin 2 near 0 V.
- **If it is pin 2 that is negative:** the amp transmits on pin 2. Swap the
  `R` and `T` wires in step C1.

### A4. Cables

- **Do:** Measure both cables' outer diameters (for the shell). Cut them,
  and buzz out which wire colours go to the 3.5 mm tip and sleeve, and to
  DB9 pins 2, 3 and 5.

## Part B — the board alone

### B1. Power, with nothing else connected

- **Do:** Solder only the trigger cable (`+` and `G`). Each wire goes down
  through its strain-relief hole at the board end, along the underside, and
  up through its pad; solder on top. Plug into the WiiM and start playback.
  Do **not** connect the serial cable yet.
- **Expect:** 3.3 V (3.2–3.4 V) between test pads `3V3` and `GND`; about
  11 to 11.7 V on `VIN`; LED off (blank chip).
- **If `VIN` is 0 V:** polarity is reversed, or the trigger is off.
- **If `3V3` is wrong but `VIN` is right:** stop; do not go on.

### B2. The 3.3 V rail on the scope

- **Do:** Scope `3V3`, AC-coupled, 50 mV/division.
- **Expect:** a flat line, a few millivolts of noise.
- **If it oscillates** (a steady ripple of tens of millivolts or more): the
  regulator is unhappy with its ceramic output capacitor. Solder a 10 µF
  tantalum across C2 and tell me.

### B3. Flash

- **Do:** Flash `dongle-pd-id-q1-dbg.hex` (see `docs/flashing.md`).
- **Expect:** the LED blinks slowly for about a second, then fast: no amp
  is answering.
- **If the LED stays off:** the chip is not running. Check `3V3` at the
  chip, and that programming verified.

### B4. What the dongle sends

- **Do:** Scope the `T` wire pad against `G`.
- **Expect:** idle at about −5.5 V. Every 1.5 s, two bursts 1 s apart: the
  power query `21 01 00 01 F0 0D`, then the power-on command
  `21 01 00 01 01 0D`, at 38,400 baud. RS232 is inverted: a 1 bit is
  negative.
- **Also:** test pad `PA1` carries the debug trace at logic levels (idle
  3.3 V, 38,400 baud): `FE 01` when the power query goes out, `FE 02` for
  power-on, `FE 03` for the input query, `FE 04` for select-STB, and a copy
  of every byte the amp sends.
- **If the timing is off by more than a few percent:** note the measured bit
  time (26.0 µs is nominal).

## Part C — with the amp

Before starting: turn the WiiM's volume right down, or disconnect the
speakers. The STB input is in processor mode, so its volume is fixed.

### C1. Connect

- **Do:** Trigger off. Solder the serial cable: `T` to DB9 pin 2, `R` to
  pin 3, `G` to pin 5 (or `T` and `R` swapped if A3 said so). Trim the
  shield and unused wires back. Amp in standby. Plug the DB9 in. Start
  playback so the trigger comes on.
- **Expect:** slow blink at once (the amp answers "standby"); the amp wakes;
  a few seconds later the LED goes solid and the amp is on STB.

### C2. If it does not go solid

Stop the WiiM, read the chip's EEPROM back and decode it
(`docs/flashing.md`), then use this table. Flash the suggested file and
repeat C1.

| LED | Log shows | Likely cause | Do |
|---|---|---|---|
| Fast | no frames at all | The amp hears nothing, or the dongle cannot hear the amp | Check "RS232 Stdby". Check the `T`/`R` wires are not swapped (A3). Scope `R`: is the amp sending anything? |
| Fast, but the amp wakes | no frames | The amp obeys but its replies do not arrive | The `R` wire or its joint. |
| Slow, amp stays in standby | power query answered `00` (standby); power-on answered with an error such as `83`, or never answered | The SA550 does not accept the direct power-on | Flash `dongle-pr-id-q1-dbg.hex` (remote-code power-on). |
| Slow, amp on, wrong input | select STB answered with an error | The SA550 does not accept the direct select | Flash the `-ir-` version of whatever you are running. |
| Slow, amp on, wrong input | input query answered with an error, or never answered | The SA550 does not answer the input query | Flash the `-q0-` version: it selects STB once after waking without asking. |
| Slow, amp on and already on STB | input query answered with data that is not `05` or `15` | The SA550 numbers its inputs differently | Tell me the data byte; the STB code is one line in `firmware/src/config.h`. |
| Solid, but the amp is not on STB | — | The input code `05` is some other input on the SA550 | Tell me which input it chose. |

If none of these fits, send me the decoded log text, the LED pattern, and a
scope capture of `T` and `R` together covering one trigger-on.

### C3. Processor mode survives

- **Do:** With the LED solid, decode the log.
- **Expect:** the input query's reply is `15` ("STB, processor mode"), and
  the amp's display still shows fixed volume.
- **If it shows `05`:** selecting STB over serial dropped processor mode.
  Do not turn the volume up. Tell me; the fix is to restore it after
  selecting.

### C4. Acceptance

Tick each one on the real system, with the release build
(the same file name without `-dbg`):

- [ ] From standby, starting playback brings the amp on and to STB with no
      touch, and the dongle adds no more than about a second to the amp's
      own start-up.
- [ ] With music playing, switching the amp to another input is corrected
      within 5 seconds.
- [ ] With music playing, putting the amp in standby is corrected within
      5 seconds.
- [ ] In normal listening there are no clicks, mutes or display flicker
      from the dongle. (It asks the amp two questions every 2 seconds and
      sends nothing else.)
- [ ] After the WiiM goes to standby, the dongle is silent (LED off) and the
      amp times out to standby by itself.
- [ ] With the shell closed, a firm pull on either cable does not move the
      board.

## Timings you may want to change

All in `firmware/src/config.h`; rebuild with `make fw`.

| Name | Value | Meaning |
|---|---|---|
| `POLL_MS` | 2000 | How often the amp is re-checked once all is well |
| `WAKE_POLL_MS` | 500 | How often while it is not |
| `REPLY_TIMEOUT_MS` | 1000 | How long a reply is waited for (the protocol allows the amp 3 s) |
| `SETTLE_MS` | 1500 | Pause between the amp reporting "on" and the first input query |
