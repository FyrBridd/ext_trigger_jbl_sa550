# Hardware design calculations

Board revision r1, 2026-11-10. Each item gives the formula, the inputs and
where they came from, and the result against its limit.

Sources are marked: **[DS]** a value the independent datasheet review
confirmed from a fetched datasheet (`docs/hardware-datasheet-review.md`);
**[spec]** the design document; **[board]** measured from the generated board
file; **[mem]** a typical datasheet figure quoted from memory and not
re-checked against a fetched datasheet. Nothing here has been measured on
hardware.

## Summary

| # | Quantity | Result | Limit | Margin |
|---|---|---|---|---|
| 1 | Supply current, worst case | 15 mA | 220 mA trigger rating | 14× |
| 2 | Regulator input voltage at 15 mA | 10.2 V | 3.4 V minimum | 6.8 V |
| 2 | Lowest trigger voltage that still works | 5.2 V | 12 V nominal | 6.8 V |
| 3 | Regulator dissipation, worst case | 0.10 W | 0.5 W (SOT-89) | 5× |
| 4 | Inrush peak at plug-in | 117 mA | 220 mA trigger rating | 1.9× |
| 5 | R1 dissipation | 23 mW | 100 mW | 4× |
| 6 | Worst-case clamp voltage at the regulator | 24.1 V | 30 V | 5.9 V |
| 6 | Worst-case clamp voltage across C1 | 24.1 V | 25 V | 0.9 V (see note) |
| 7 | Reverse voltage across D1 | 12 V | 40 V | 3.3× |
| 8 | LED current | 1.3 mA | 20 mA pin limit | 15× |
| 9 | Serial timing error, worst case | about ±2 % | ±2 % recommended | none to spare (see item 9) |
| 10 | RS232 output swing | ±5.0 V minimum | ±3 V needed | 2 V |
| 12 | Track current capacity, 0.4 mm | 1.2 A | 0.12 A peak | 10× |

## 1. Supply current against the trigger's rating

`I_total = I_controller + I_driver + I_driver_load + I_LED + I_regulator`

| Load | Typical | Worst case | Source |
|---|---|---|---|
| ATtiny412, running at 3.33 MHz, 3.3 V | 1.5 mA | 3 mA | [mem] |
| SP3232EEY, no load | 0.3 mA | 1.0 mA | [mem] |
| One RS232 output into the amp's receiver (3–7 kΩ at about 5.4 V, drawn through the charge pump, so doubled at the supply) | 2.2 mA | 4 mA | [mem] |
| LED, on continuously | 1.3 mA | 1.5 mA | item 8 |
| HT7533-1 quiescent | 0.003 mA | 0.005 mA | [mem] |
| R3 pull-up, only while a byte is being sent | 0 mA | 0.33 mA | 3.3 V / 10 kΩ |
| Allowance | | 5 mA | |
| **Total** | **5.3 mA** | **15 mA** | |

The trigger output is rated 220 mA [spec, WiiM]. The dongle uses about 7 %
of it in the worst case.

## 2. Voltage at the regulator input

`V_IN = V_trigger − I × R1 − V_F(D1)`

- R1 = 100 Ω [spec]; D1 forward drop about 0.3 V at 15 mA [mem].
- At 12 V and 15 mA: `12 − 1.5 − 0.3 = 10.2 V`.
- The HT7533-1 needs its input above `3.3 V + dropout`; dropout is about
  0.1 V at this current [mem]. Margin: 6.8 V.
- Turned round, the trigger can sag to `3.4 + 0.3 + 1.5 = 5.2 V` at 15 mA
  before the 3.3 V rail drops.

## 3. Regulator dissipation

`P = (V_IN − 3.3 V) × I`

- Worst case: `(10.2 − 3.3) × 0.015 = 0.10 W`.
- Typical (5.3 mA, so V_IN = 11.2 V): `7.9 × 0.0053 = 0.04 W`.
- SOT-89 is good for about 0.5 W [mem], roughly 200 °C/W, so the worst case
  is a rise of about 20 °C.
- Maximum input 30 V and 70 mA guaranteed output (100 mA typical) [DS].

## 4. Inrush at plug-in

`I_peak = (V_trigger − V_F) / R1 = (12 − 0.3) / 100 = 117 mA`

- This is the instant C1 (10 µF) starts charging from empty.
- It decays with time constant `R1 × C1`. C1 loses capacitance with voltage
  across it (item 11), so about `100 Ω × 4–10 µF = 0.4–1 ms`.
- 117 mA is inside the 220 mA rating. This is why R1 is 100 Ω and not the
  22 Ω first proposed (22 Ω gives 530 mA).

## 5. R1 dissipation

`P = I² × R = 0.015² × 100 = 23 mW` against a 100 mW 0603 rating [mem].

## 6. Over-voltage clamp

- D2, SMF15CA: 15 V stand-off, 16.7 V minimum breakdown, 24.4 V maximum
  clamp at its 8.2 A test current [DS]. At 12 V it does nothing.
- What the regulator and C1 see is one diode drop less: 24.1 V.
- Regulator: 30 V operating maximum [DS]. Margin 5.9 V.
- C1: 25 V rating [DS]. Margin 0.9 V on paper.
- That worst case needs 8.2 A through the TVS, which R1 makes impossible:
  the source would have to be `24.4 + 8.2 × 100 = 844 V`. For a realistic
  surge, say 30 V, the TVS carries `(30 − 18) / 100 = 0.12 A` and clamps
  near its breakdown, 17–19 V. So C1's real margin is about 6 V.

## 7. Reverse polarity

- With the trigger wires swapped, D1 blocks. It sees 12 V reverse against a
  40 V rating [DS]. D2 is bidirectional and does not conduct at 12 V.
- **This protects the dongle only.** The board's ground is also joined to the
  amp's ground by the serial cable, and the amp's ground reaches the WiiM's
  ground through the audio cable. With swapped trigger wires the WiiM's 12 V
  output would be shorted to its own ground through that path, without
  passing through R1 or D1. Check polarity with a meter before soldering, and
  power up the first time with the serial cable unplugged.

## 8. LED current

`I = (3.3 − V_F) / R2 = (3.3 − 2.0) / 1000 = 1.3 mA`

V_F about 2.0 V for the red KT-0603R [mem]. An ATtiny412 pin can source well
over 10 mA [mem]. 1.3 mA is dim but visible; the LED sits inside the shell
behind a 2 mm hole.

## 9. Serial timing

`BAUD register = 64 × F_CPU / (16 × baud) = 64 × 3,333,333 / (16 × 38,400) = 347.2`, written as 347

- Rounding the divisor costs almost nothing: with 347 the rate is
  `64 × 3,333,333 / (16 × 347) = 38,424 baud`, +0.06 %.
- The oscillator is what matters. From the ATtiny412 datasheet [DS]: the
  internal oscillator is within ±3 % at 25 °C and 3 V, and ±4 % over 0 to
  70 °C, if nothing is done. Using the per-chip error value stored at the
  factory, it is within ±2 % over 0 to 70 °C.
- The same datasheet recommends that a receiver's clock be within ±2 % for
  8-bit frames [DS].
- So with the factory correction the worst case just meets the
  recommendation, with nothing to spare; without it the link would not be
  reliable. The firmware applies the correction (`SIGROW.OSC20ERR3V`) when it
  sets the baud rate. **That correction is required, not a nicety.**
- At room temperature in a living room the error should be well inside ±2 %,
  but this has not been measured. Bring-up step B4 measures the bit time.
- The amp's clock is assumed to be crystal-accurate.
- 3.33 MHz is well inside what the ATtiny412 may run at from 3.3 V [DS].

## 10. RS232 levels

- SP3232EEY output swing at 3.3 V supply: ±5.0 V minimum, ±5.4 V typical
  into 3 kΩ [mem]. An RS232 receiver needs ±3 V.
- Its receiver accepts ±15 V in, switches at about 1.2 V and 1.5 V, and has
  a 5 kΩ pull-down, so an open input reads as an idle line [DS].
- Charge-pump capacitors: 0.1 µF is the datasheet value at 3.3 V [DS].

## 11. Capacitor voltages

| Capacitor | Sees | Rated | Note |
|---|---|---|---|
| C1, 10 µF 0805 X5R | up to 11.7 V | 25 V | Capacitance falls with DC voltage; expect roughly a third to a half left at 12 V [mem]. Enough for the regulator's input. |
| C2, 10 µF 0805 X5R | 3.3 V | 25 V | Little loss at 3.3 V. |
| C4–C7, 100 nF 0603 X7R | up to about 6.6 V | 50 V | Charge-pump voltages are about ±5.5 V. |
| C3, C8, 100 nF 0603 X7R | 3.3 V | 50 V | |

**Open point: regulator stability.** Holtek's datasheet shows 10 µF on the
output but gives no ESR range and does not say whether a ceramic capacitor is
acceptable. The HT75xx family is widely used with ceramics, but this board
has not been tested. Scope the 3.3 V rail at bring-up; if it rings, fit a
tantalum 10 µF in the C2 position.

## 12. Tracks

IPC-2221, outer layer, 35 µm copper, 10 °C rise: `I = 0.048 × ΔT^0.44 × A^0.725` (A in square mils)

| Width | Carries | Used for | Most it carries here |
|---|---|---|---|
| 0.4 mm | 1.2 A | trigger input, VIN, 3.3 V, ground | 0.12 A inrush |
| 0.25 mm | 0.9 A | signals | a few mA |

Voltage drop on the 3.3 V net: 54.7 mm of 0.4 mm track in total [board],
about 67 mΩ if it were all in series, so under 1 mV at 15 mA.

Clearances: 0.2 mm between different nets, 0.25 mm around holes, 0.3 mm
copper to board edge, against JLCPCB's 0.127 mm minimum spacing [mem].

## 13. What these calculations do not cover

- Anything measured. No board exists yet.
- The trigger output's real behaviour under load; only its 220 mA rating is
  published.
- Electromagnetic emissions or immunity. The board is low-speed (38,400 baud)
  and sits inside an audio system's ground; no testing is planned.
