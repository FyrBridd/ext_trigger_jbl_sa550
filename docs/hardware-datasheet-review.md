# Hardware datasheet review

Independent review of `hardware/design/circuit.py` and section 5 of the design
document against manufacturer datasheets fetched on 2026-11-10, and against
KiCad 10.0.8's stock libraries in the dev container.

## Summary

**Verdict: no FAIL. `circuit.py` needs no change.** Every pin number in
`PIN_FUNCTIONS` and `NETS` for U1, U2, U3, D1, D2 and D3 agrees with the
datasheet function for the exact package, the KiCad symbols and footprints
agree with the datasheets (one numbering difference on D3, below), and no part
is taken outside its ratings.

Items that are not a plain PASS:

| # | Result | Item | What to do |
|---|---|---|---|
| 1 | CONCERN | **D3 pin numbering.** The Kento datasheet numbers the LED's anode ① and cathode ②. KiCad and `circuit.py` use pad 1 = cathode. The nets are correct by function (cathode to GND), so nothing changes in `circuit.py`, but nobody should "correct" it to the datasheet's numbers, and the placement rotation cannot be taken from the datasheet numbering. | In JLCPCB's placement preview, check that the LED's cathode end sits on pad 1, the GND pad at the silkscreen-marked end. By the datasheet's drawing (p. 2), the cathode end carries the green corner mark on the top face, and on the underside the narrow end of the green arrow points to it. |
| 2 | CONCERN | **Reversed trigger wiring, system level (not a datasheet finding).** D1's 40 V rating is ample, but D1 only protects the dongle. Board GND is also tied to the amp's ground through the serial cable, and the amp's ground reaches the WiiM's ground through the audio cable (design section 5.5). With the trigger wires swapped, the WiiM's +12 V lands on that shared ground and the trigger output is shorted without passing through R1 or D1. | Treat the polarity `[verify]` in design section 3.1 as mandatory, and do the first power-up with the serial cable unplugged. |
| 3 | COULD NOT VERIFY | **U1 stability with a 10 µF ceramic output capacitor.** The HT75xx-1 datasheet gives no ESR range and no statement about capacitor type. Its application circuit shows 10 µF on input and output, drawn as polarised capacitors. | At bring-up, scope the 3.3 V rail at no load and during a load step (the serial driver starting up is enough). If it rings or oscillates, fit a tantalum or electrolytic 10 µF in the C2 position, or add a small series resistance. |
| 4 | COULD NOT VERIFY | **U1 tab connection.** The datasheet draws the SOT-89 tab but does not say what it is connected to. KiCad's footprint makes the tab part of pad 2, so the board puts it on VIN. That is right for a SOT-89, whose tab and centre lead are one piece of metal, but this comes from package construction, not from the Holtek datasheet. | Keep the tab copper on VIN and clear of the ground pour. A meter check between tab and centre pin on a loose part settles it. |

Lesser notes, all on PASS rows: the regulator's 100 mA is a typical figure
(70 mA guaranteed); C1's 25 V rating clears the TVS's 24.4 V worst-case clamp
by only 0.6 V on paper, though R1 keeps real clamp currents far below the
8.2 A at which that figure applies; D2 is bidirectional and has no cathode
mark, so there is nothing to check for it in the placement preview; the serial
baud rate depends on the firmware applying the factory oscillator correction,
which the firmware plan already does.

### Addendum, 2026-11-11: D4 added after this review

A second B5819W, D4, was added in the trigger's return wire (cathode to the
trigger's ground pad, anode to board ground). It is the same part, symbol
and footprint as D1, so the D1 rows below (pinout, cathode pad, 40 V reverse
rating) apply to it unchanged. Its connections are checked by
`test_reversed_trigger_wires_have_no_path_to_anything`. It was added by the
design's author and has not had a separate independent review.

## Checks

Page numbers are PDF page numbers of the documents listed under Sources.

### U1 — Holtek HT7533-1, SOT-89 (C14289)

| Part | What was checked | Datasheet (URL and page/section) | Result | Notes |
|---|---|---|---|---|
| U1 | Pin functions in `PIN_FUNCTIONS` and `NETS` for the SOT-89 "-1" part | [HT75xx-1 Rev. 2.80][ht], p. 4 "Pin Assignment" (SOT89), p. 5 "Pin Descriptions" | PASS | Datasheet: pin 1 GND, pin 2 VIN, pin 3 VOUT; top view with the tab up reads GND, VIN, VOUT left to right. `circuit.py`: U1.1 GND, U1.2 VIN, U1.3 +3V3. The 2006 Rev. 1.50 copy shows the same order. |
| U1 | KiCad symbol `Regulator_Linear:HT75xx-1-SOT89` | same, p. 5 | PASS | Symbol pins: 1 GND, 2 VIN, 3 VOUT. |
| U1 | KiCad footprint `Package_TO_SOT_SMD:SOT-89-3` pad numbering and size | same, p. 4 and p. 16 "3-pin SOT89 Outline Dimensions" | PASS | Pads 1, 2, 3 on one side at 1.5 mm pitch (datasheet H = 1.50 BSC). With the leads pointing left, pad 1 is the top one, which is the datasheet's left-hand pin with the leads pointing down. Pad span 4.6 mm against the datasheet's overall dimension E (lead tips to tab tip) of 3.94 to 4.40 mm. |
| U1 | Which footprint pad is the tab, and the part's tab pin | same, p. 4 and p. 16 | COULD NOT VERIFY | Footprint: the tab is part of pad 2, a single custom pad running from x = −2.6 mm to +2.0 mm, so the tab is on VIN. Datasheet: the tab is drawn opposite the centre lead but not labelled. See summary item 4. |
| U1 | Maximum input voltage | same, p. 7 (VIN max 30 V), p. 4 "Absolute Maximum Ratings" (−0.3 V to 33 V) | PASS | Nominal input is about 12 − 1.5 (R1 at 15 mA) − 0.3 (D1) = 10.2 V. Rev. 1.50 of 2006 gave 24 V operating and 26 V absolute; the current revision and the LCSC listing give 30 V. |
| U1 | Worst-case TVS clamp at the regulator input | [SMF series Rev. 2.2][smf], p. 2 (SMF15CA: VC 24.4 V at 8.2 A); [HT75xx-1][ht], p. 4 and p. 7 | PASS | VIN ≤ 24.4 V minus D1's forward drop, against 30 V operating and 33 V absolute. It would also stay under the old 26 V absolute figure. |
| U1 | Maximum output current | [HT75xx-1][ht], p. 7 | PASS | 70 mA minimum, 100 mA typical at VIN = 5.3 V. The design document's "100 mA" is the typical figure. Load is under 15 mA. |
| U1 | Dropout | same, p. 7 | PASS | 25 mV typical, 55 mV maximum at 1 mA. No figure is given at higher current. Headroom here is about 6.9 V. |
| U1 | Dissipation | same, p. 4 "Thermal Information" | PASS | (10.2 − 3.3) V × 15 mA ≈ 0.10 W against 0.50 W for SOT89 at 25 °C; 200 °C/W gives about 21 °C rise. Matches the design document's "about 0.1 W". |
| U1 | Recommended input and output capacitors | same, p. 13 "Basic Circuit" | PASS | 10 µF on the input and 10 µF on the output, as C1 and C2. |
| U1 | Stability with a 10 µF low-ESR ceramic on the output | same, whole document | COULD NOT VERIFY | No ESR limit, no capacitor-type statement, and no capacitor conditions on the transient plots (pp. 11 to 12). See summary item 3. Not verified either: how much of C2's 10 µF remains under DC bias; the Samsung document has no bias curve. |

### U2 — Microchip ATtiny412-SSNR, SOIC-8 (C1337190)

| Part | What was checked | Datasheet (URL and page/section) | Result | Notes |
|---|---|---|---|---|
| U2 | Pin functions in `PIN_FUNCTIONS` and `NETS` | [DS40002287A][tiny], p. 14 §4.1 "8-Pin SOIC", p. 18 Table 5-2 | PASS | 1 VDD, 2 PA6, 3 PA7, 4 PA1, 5 PA2, 6 PA0 (RESET/UPDI), 7 PA3, 8 GND. All eight match. |
| U2 | KiCad symbol `MCU_Microchip_ATtiny:ATtiny412-SS` | same, p. 14 | PASS | The symbol extends `ATtiny202-SS`: 1 VCC, 2 PA6, 3 PA7, 4 PA1, 5 PA2, 6 ~RESET/PA0, 7 PA3, 8 GND. |
| U2 | KiCad footprint `Package_SO:SOIC-8_3.9x4.9mm_P1.27mm` | same, p. 555 (SS = SOIC150), p. 557 §38.2 (narrow, 3.90 mm body) | PASS | Pads 1 to 4 down the left, 5 to 8 up the right, as the datasheet's top view. |
| U2 | USART0 default pins | same, p. 18 Table 5-2; p. 132 PORTMUX.CTRLB (reset 0x00) | PASS | Default TxD is PA6 (pin 2) and RxD is PA7 (pin 3). PA1 and PA2 are the alternate pair, used only if firmware sets PORTMUX.CTRLB bit 0. |
| U2 | PA0 is UPDI by default | same, p. 40 FUSE.SYSCFG0 (RSTPINCFG factory default 0x1 = UPDI); p. 465 | PASS | In UPDI mode the pin is an input with an internal pull-up, so J3 pad 4 and TP6 need no external parts. |
| U2 | Default clock | same, p. 38 FUSE.OSCCFG (factory default 0x02 = 20 MHz); p. 80 §10.3.3 | PASS | After any reset the main clock is the 16/20 MHz oscillator divided by 6, giving 3.3 MHz. |
| U2 | Maximum safe frequency at 3.3 V | same, p. 500 Table 35-3, p. 501 Figure 35-1 | PASS | 5 MHz allowed from 1.8 V, 10 MHz from 2.7 V, 20 MHz from 4.5 V, linear between. At 3.3 V that is 13.3 MHz (12.8 MHz at the regulator's 3.2 V minimum). 3.33 MHz is inside even the 1.8 V limit. |
| U2 | Supply voltage range | same, p. 500 Table 35-2 (1.8 V to 5.5 V), p. 499 Table 35-1 (absolute maximum 6 V); [HT75xx-1][ht], p. 7 | PASS | U1's output is 3.201 V to 3.399 V. The -SSNR code is 20 MHz, 1.8 V to 5.5 V, −40 °C to +105 °C (p. 554). |
| U2 | Oscillator accuracy for 38,400 baud | same, p. 505 Table 35-12; p. 81; p. 327 Table 24-4 | PASS | Uncorrected: ±3 % at 25 °C and 3 V, ±4 % over 0 to 70 °C. Using the factory-stored error: ±2 % over 0 to 70 °C. The USART's recommended receiver error for 8 data bits is ±2 %. The firmware plan already applies `SIGROW.OSC20ERR3V`; that correction is needed, not optional. |
| U2 | Transmit pin state in reset, and R3 | same, p. 137 §16.3.1 | PASS | After reset all outputs are tri-stated, so PA6 floats during reset and programming. R3 is needed and present. |

### U3 — MaxLinear SP3232EEY-L/TR, TSSOP-16 (C13482)

| Part | What was checked | Datasheet (URL and page/section) | Result | Notes |
|---|---|---|---|---|
| U3 | Pin functions in `PIN_FUNCTIONS` and `NETS` | [SP3222E/SP3232E REV 1.0.3][sp], p. 5 Table 1 (SP3232E column), p. 6 Figure 5 | PASS | 1 C1+, 2 V+, 3 C1−, 4 C2+, 5 C2−, 6 V−, 7 T2OUT, 8 R2IN, 9 R2OUT, 10 T2IN, 11 T1IN, 12 R1OUT, 13 R1IN, 14 T1OUT, 15 GND, 16 VCC. All sixteen match. |
| U3 | KiCad symbol `Interface_UART:MAX3232` | same, p. 5 | PASS | The symbol extends `MAX232` and has the same sixteen assignments; it names pins 2 and 6 VS+ and VS−. |
| U3 | KiCad footprint `Package_SO:TSSOP-16_4.4x5mm_P0.65mm` | same, p. 18 "TSSOP16" (JEDEC MO-153 AB: D 5.00, E1 4.40, e 0.65 mm); p. 20 | PASS | SP3232EEY-L/TR is the 16-pin TSSOP, −40 °C to +85 °C. |
| U3 | Charge-pump capacitor connections | same, p. 7 Figure 7 | PASS | C4 across C1+ and C1− (pins 1, 3); C5 across C2+ and C2− (pins 4, 5); C6 from V+ (pin 2) to GND; C7 from V− (pin 6) to GND; C8 from VCC to GND. The figure allows the V+ capacitor to return to VCC or GND. |
| U3 | 0.1 µF is the value at 3.3 V | same, p. 1 "Description"; p. 7 Figure 7; p. 10 | PASS | "requires only 0.1µF capacitors in 3.3V operation"; capacitors "can be as low as 0.1µF with a 16V breakdown voltage rating". The fitted parts are rated 50 V. |
| U3 | Unused driver input T2IN tied to GND | same, p. 9 "Drivers" | PASS | "Designers should connect unused inputs to VCC or GND." T2OUT then rests high and is left open. |
| U3 | Unused receiver input R2IN left open | same, p. 9 "Receivers" | PASS | An open input is pulled down internally and its output goes high. R2OUT is left open. |
| U3 | Receiver pull-down, and output with the input open | same, p. 3 (input resistance 3, 5, 7 kΩ); p. 9 | PASS | "an internal 5kΩ pulldown resistor to ground will commit the output of the receiver to a HIGH state." With no amp connected R1OUT is high, which the UART reads as idle, as the design document says. |
| U3 | Driver inputs have no pull-up; R3 | same, p. 9; p. 2 (input leakage ±1 µA, logic high ≥ 2.0 V at 3.3 V) | PASS | "The driver's inputs do not have pull-up resistors." R3 (10 kΩ to 3.3 V) holds T1IN high, so the inverting driver keeps T1OUT at the idle level. Leakage drops 10 mV across R3. |
| U3 | Ratings at 3.3 V | same, p. 2 "Absolute Maximum Ratings"; p. 3 | PASS | VCC 3.0 V to 5.5 V, absolute 6.0 V; U1 gives at least 3.2 V. Receiver inputs ±15 V operating, ±25 V absolute. Driver inputs to VCC + 0.3 V, on the same rail as U2. |

### D1 — B5819W, SOD-123 (C8598)

| Part | What was checked | Datasheet (URL and page/section) | Result | Notes |
|---|---|---|---|---|
| D1 | Polarity in `NETS` | [B5817W-5819W][b58], p. 1 | PASS | The datasheet does not number the terminals: "The marking bar indicates the cathode". `circuit.py`: D1.1 (cathode) on VIN, D1.2 (anode) on TRIG_R, so current flows TRIG_R to VIN. |
| D1 | KiCad symbol `Device:D_Schottky` and footprint `Diode_SMD:D_SOD-123` | same, p. 1 and p. 3 | PASS | Symbol: pin 1 K, pin 2 A. Footprint: pad 1 is the cathode (silkscreen bar at the pad 1 end; the fabrication-layer diode symbol has its bar towards pad 1). Suggested land 0.8 × 1.0 mm at 3.24 mm; KiCad 0.9 × 1.2 mm at 3.30 mm. |
| D1 | Reverse voltage with the trigger connected backwards | same, p. 1 (VRRM, VR 40 V) | PASS | 12 V steady. At most about 35 V if the TVS clamps a negative spike at −24.4 V while C1 still holds about 10.5 V. See summary item 2 for what D1 does not protect. |
| D1 | Forward current | same, p. 1 (IO 1 A, IFSM 9 A, VF ≤ 0.6 V at 1 A) | PASS | Load under 15 mA; inrush limited by R1 to 120 mA. |

### D2 — SMF15CA, SOD-123FL (C19077510)

| Part | What was checked | Datasheet (URL and page/section) | Result | Notes |
|---|---|---|---|---|
| D2 | Pins in `NETS` | [SMF series Rev. 2.2][smf], p. 2 (notes under the outline), p. 3 (suffix CA = bidirectional) | PASS | Bidirectional: no polarity and no cathode band ("Bidirectional devices without this marking"). D2.1 on TRIG_R and D2.2 on GND is correct either way round. |
| D2 | KiCad symbol `Device:D_TVS` and footprint `Diode_SMD:D_SOD-123F` | same, p. 2 "Package Outline Dimensions (SOD-123FL)" | PASS | Symbol pins A1, A2. Part: 3.60 to 3.90 mm over the leads, leads 0.90 to 1.10 mm wide and 0.40 to 0.90 mm long. Footprint: 1.1 × 1.1 mm pads at ±1.4 mm, 3.9 mm overall. |
| D2 | Stand-off against the 12 V trigger | same, p. 2 | PASS | VRWM 15 V, leakage ≤ 1 µA; breakdown 16.7 V to 18.5 V at 1 mA. |
| D2, C1 | Worst-case clamp against C1's 25 V rating | same, p. 2 (VC 24.4 V at 8.2 A, 10/1000 µs), p. 1 (ΔVBR 0.1 %/°C); [Samsung MLCC][sam], p. 21 | PASS | C1 sees at most 24.4 V less D1's drop. The margin is thin on paper (0.6 V, and the temperature coefficient removes it above roughly 50 °C at full pulse current), but 8.2 A through R1 would need over 800 V at the pad. At currents R1 allows, the clamp stays near the 18.5 V breakdown. |

### D3 — KT-0603R red LED, 0603 (C2286)

| Part | What was checked | Datasheet (URL and page/section) | Result | Notes |
|---|---|---|---|---|
| D3 | Pin numbering and polarity in `NETS` | [Kento 0603-0.6 red][led], p. 2 "Package Profile", p. 6 (tape polarity) | CONCERN | Datasheet: terminal ① is "+" (anode), ② is "−" (cathode). `circuit.py` follows KiCad instead: D3.1 (cathode) on GND, D3.2 (anode) on LED_A. Functionally correct. See summary item 1. |
| D3 | KiCad symbol `Device:LED` and footprint `LED_SMD:LED_0603_1608Metric` | same, p. 2 | PASS | Symbol: pin 1 K, pin 2 A. Footprint: pad 1 is the cathode (silkscreen closed at the pad 1 end, chamfered corner on the fabrication layer). Recommended lands are 0.70 mm apart; the footprint's pads are 0.70 mm apart. |
| D3, U2 | LED current through R2 from 3.3 V | same, p. 3 (IF 25 mA maximum, VF 1.8 V to 2.4 V at 20 mA, VR 5 V); [DS40002287A][tiny], p. 499 (pin ±40 mA), p. 507 | PASS | (3.3 − about 1.8) V / 1 kΩ ≈ 1.5 mA. It could not exceed 3.4 mA even with no LED drop. No reverse voltage is ever applied. |

### Capacitors

| Part | What was checked | Datasheet (URL and page/section) | Result | Notes |
|---|---|---|---|---|
| C1, C2 | Value and rating of CL21A106KAYNNNE | [Samsung MLCC][sam], p. 21 (CL21A106KAYNNN: 10 µF, 25 V, 10 %), pp. 4 to 5 (codes: A = X5R, A = 25 V) | PASS | C1 works at about 10 V, C2 at 3.3 V. Effective capacitance under DC bias was not checked; this document has no bias curve. |
| C3 to C8 | Value and rating of CC0603KRX7R9BB104 | [Yageo X7R V.26][yag], p. 2 (code 9 = 50 V, K = ±10 %), p. 5 (0603, 100 nF, 50 V) | PASS | The charge-pump capacitors see at most about 2 × VCC. |

### Design document section 5 and `circuit.py`, other statements

| Part | What was checked | Datasheet (URL and page/section) | Result | Notes |
|---|---|---|---|---|
| R1 | "Limits inrush … to about 120 mA", "drops about 1.5 V at 15 mA" | arithmetic only | PASS | 12 V / 100 Ω = 120 mA; 15 mA × 100 Ω = 1.5 V. R1's own datasheet was not fetched. |
| D2, U1 | "Clamps spikes below the regulator's 30 V limit" | [SMF][smf], p. 2; [HT75xx-1][ht], p. 7 | PASS | 24.4 V maximum against 30 V. |
| U1 | "(30 V maximum input, 100 mA)" | [HT75xx-1][ht], p. 7 | PASS | 30 V is correct. 100 mA is typical; 70 mA is guaranteed. |
| D1 | "Reverse-polarity protection" | [B5817W-5819W][b58], p. 1; [HT75xx-1][ht], p. 4 | CONCERN | True for the dongle only; see summary item 2. A smaller point: with the supply reversed, D1's leakage (limit 1 mA at 40 V, typically microamps at 12 V) pulls VIN a few hundred millivolts below ground until a junction inside U1 conducts, and U1's rating is −0.3 V. At microamp level this is harmless; noted for completeness. |
| U2 | Pin table; "internal oscillator at its default 3.33 MHz" | [DS40002287A][tiny], p. 18, p. 80 | PASS | As the U2 rows above. |
| U3 | "five 100 nF capacitors", "tie T2IN to ground, leave R2IN and R2OUT open", R3, idle line with no amp | [SP3232E][sp], pp. 1, 7, 9 | PASS | As the U3 rows above. |
| U2, J3 | Pad 1 of J3 (MCLR/VPP, may carry 12 V) left unconnected | [DS40002287A][tiny], p. 499 (RESET pin absolute maximum 13 V) | PASS | UPDI stays enabled by fuse, so the high-voltage override is never needed. |

## Not covered

- R1, R2 and R3: no datasheets fetched.
- J3: the TC2030-MCP-NL pad order and the ICD 5's UPDI signal assignment
  (recorded in `hardware/lib/README.md`) were not part of this review.
- The ATtiny412 silicon errata (DS80000933) were not read.
- The alternates ATtiny402-SSNR and ATtiny202-SSNR were only spot-checked
  against [DS40001969A][tiny0]: its pinout drawing (§4.1) matches the
  ATtiny412 on all eight pins and the default USART is on PA6 and PA7. That
  revision's multiplexing table lists PA1 and PA2 against swapped pin numbers,
  contradicting its own drawing; this would only affect the two spare test
  pads. Check a current revision before substituting.

## Sources

All fetched 2026-11-10. LCSC's product record for each part number gave the
datasheet link, except where noted.

- **U1** — Holtek, *HT75xx-1 100mA TinyPower LDO*, Rev. 2.80, April 10, 2024,
  18 pages. LCSC has no datasheet for C14289 (its `/datasheet/C14289.pdf`
  returns "Page Not Found") and Holtek's site refused automated access. This
  copy is the file JLCPCB's part record for C14289 links:
  <https://jlcpcb.com/api/file/downloadByFileSystemAccessId/8579707787284303872>.
  Compared with an older Rev. 1.50 (January 12, 2006) copy at
  <https://embedded.fel.cvut.cz/sites/default/files/kurzy/ETC/Literatura/HT7533_1_stabilizator_3_3V.pdf>:
  same pin order, lower voltage ratings.
- **U2** — Microchip, *ATtiny212/214/412/414/416*, DS40002287A, 2020, 585
  pages, from Microchip:
  <https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/DataSheets/ATtiny212-214-412-414-416-DataSheet-DS40002287A.pdf>.
  LCSC's link for C1337190
  (<https://datasheet.lcsc.com/datasheet/pdf/9cd3a7aa906d335e0e9e215226a82b43.pdf>)
  is the *Automotive* data sheet, which does not list the -SSNR code; it was
  used only to confirm the identical 8-pin pinout.
- **U3** — MaxLinear, *SP3222E / SP3232E*, REV 1.0.3, 2020, 21 pages:
  <https://datasheet.lcsc.com/datasheet/pdf/7926e2155f4694c0ed5e2b72d2f8c464.pdf>
- **D1** — Jiangsu Changjiang Electronics (JCET/CJ), *B5817W-5819W*, rev. D,
  March 2015, 4 pages. LCSC lists C8598 as "B5819W SL", brand JSCJ:
  <https://datasheet.lcsc.com/datasheet/pdf/4ac2c059be7c462694ab0715ce987a85.pdf>
- **D2** — R+O (Zhuhai Hongjiacheng Technology), *SMF Series 200W Surface
  Mount Transient Voltage Suppressors*, Rev. 2.2, 5 pages. LCSC lists
  C19077510 under the brand R+O:
  <https://datasheet.lcsc.com/datasheet/pdf/fa41ee376507916bceb7512729759974.pdf>
- **D3** — Hubei Kento Electronic, *Specification for approval, 0603-0.6
  red*, revision A.0, 2018-12-06, 11 pages. The document does not print the
  part number KT-0603R; LCSC's record for C2286 is what ties it to the part:
  <https://datasheet.lcsc.com/datasheet/pdf/011ec3e8cb1e825f6961d29bc4db4c7a.pdf>
- **C1, C2** — Samsung Electro-Mechanics, MLCC catalogue, 84 pages:
  <https://datasheet.lcsc.com/datasheet/pdf/02336ea48ea44ca18c72517dd3cb7b47.pdf>
- **C3 to C8** — Yageo, *Surface-Mount Ceramic Multilayer Capacitors, General
  Purpose & High Capacitance, Class 2, X7R*, V.26, November 19, 2024:
  <https://datasheet.lcsc.com/datasheet/pdf/23ccee80ee542e7cf156a772bb589942.pdf>
- **Alternates** — Microchip, *ATtiny202/402*, DS40001969A:
  <https://ww1.microchip.com/downloads/en/DeviceDoc/ATtiny202-402-AVR-MCU-with-Core-Independent-Peripherals_and-picoPower-40001969A.pdf>
- **KiCad** — stock libraries of KiCad 10.0.8 in the dev container, under
  `/usr/share/kicad/symbols` and `/usr/share/kicad/footprints`.

[ht]: https://jlcpcb.com/api/file/downloadByFileSystemAccessId/8579707787284303872
[tiny]: https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/DataSheets/ATtiny212-214-412-414-416-DataSheet-DS40002287A.pdf
[tiny0]: https://ww1.microchip.com/downloads/en/DeviceDoc/ATtiny202-402-AVR-MCU-with-Core-Independent-Peripherals_and-picoPower-40001969A.pdf
[sp]: https://datasheet.lcsc.com/datasheet/pdf/7926e2155f4694c0ed5e2b72d2f8c464.pdf
[b58]: https://datasheet.lcsc.com/datasheet/pdf/4ac2c059be7c462694ab0715ce987a85.pdf
[smf]: https://datasheet.lcsc.com/datasheet/pdf/fa41ee376507916bceb7512729759974.pdf
[led]: https://datasheet.lcsc.com/datasheet/pdf/011ec3e8cb1e825f6961d29bc4db4c7a.pdf
[sam]: https://datasheet.lcsc.com/datasheet/pdf/02336ea48ea44ca18c72517dd3cb7b47.pdf
[yag]: https://datasheet.lcsc.com/datasheet/pdf/23ccee80ee542e7cf156a772bb589942.pdf
