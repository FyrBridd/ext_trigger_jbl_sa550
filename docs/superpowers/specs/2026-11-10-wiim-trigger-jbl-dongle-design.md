# WiiM trigger to JBL SA550 serial dongle — design

Date: 2026-11-10
Status: draft for approval

Throughout this document, **[decided]** marks something the owner said or
agreed, **[call]** marks a choice made by the author that the owner has not
explicitly agreed, and **[verify]** marks something not yet confirmed that the
builder must check before relying on it.

## 1. Intent

A WiiM Ultra streamer feeds a JBL SA550 Classic amplifier on the amp's STB
input. The WiiM has a 12 V trigger output; the SA550 has no trigger input, only
an RS232 control port. The owner wants the amp to come on, on the right input,
whenever the WiiM is active, without touching the amp.

The product is a small inline dongle on a cable: 12 V trigger in at one end,
RS232 out at the other. It is powered entirely by the trigger line. While it
has power it keeps the amp switched on and on the STB input.

One unit is being built, for the owner's own use **[call: quantity]**. It will
live hidden behind the equipment.

## 2. Goals, non-goals, anti-goals

**Goals**

- When the trigger goes high, the amp wakes from standby and ends up on STB.
- While the trigger stays high, the amp is pulled back to "on, STB" within a
  few seconds if someone turns it off or changes input. **[decided]** The owner
  accepts that other inputs are unusable while the WiiM is active.
- Powered only from the trigger line.
- Assembled by JLCPCB, using basic parts wherever possible, and only parts
  that are in stock (section 9).
- Firmware can be reflashed in place, without soldering, so the protocol can
  be tuned against the real amp after the boards arrive.
- The whole project (schematic, board, firmware, enclosure) is produced and
  checked from the headless Linux box.

**Non-goals**

- Switching the amp off. The amp's own auto-standby does that. **[decided]**
- Volume, direct mode, or any other setting. The amp is already in direct
  mode with fixed volume. **[decided]**
- Any input other than STB, any configuration interface, any other amplifier.
- Galvanic isolation between the WiiM and the amp.
- Proving the serial commands before ordering boards. **[decided]** The
  commands only affect firmware, and firmware is tuned on the real hardware.

**Anti-goals** (failures even if it technically works)

- Needing to desolder anything to change the firmware.
- Sending commands so often, or so blindly, that the amp clicks, mutes, or
  flickers its display during normal listening.
- Making the UPDI programming pin unusable (for example by fusing it as GPIO
  or reset).
- Ordering a board whose parts turn out to be out of stock.

## 3. What is known, and how well

### 3.1 WiiM Ultra trigger output

Source: WiiM FAQ and manual, plus forum reports.

- 3.5 mm jack; both mono (TS) and stereo (TRS) plugs are listed as compatible.
- 12 V nominal, rated 220 mA.
- Goes high when playback starts or the unit leaves standby; goes low when the
  unit enters standby.
- Polarity is not officially stated. Tip positive is the convention.
  **[verify]** with a multimeter before soldering.
- Forum-reported quirks: a brief pulse during WiiM reboots, and spurious
  trigger-on from standby on recent firmware. Either wakes the amp. Once the
  trigger drops again the amp times itself out. Accepted.
- **Consequence of "keep it awake" [decided]:** for as long as the trigger is
  high, the amp cannot stay in standby. If nothing is playing, the amp's
  auto-standby may fire, and the dongle will wake it again within seconds.
  The amp only goes to standby for good after the WiiM drops its trigger.
  There is no give-up rule.

### 3.2 JBL SA550 RS232 port

No SA550 protocol document exists. The owner states it is the same as the
SA750. The SA750 document (SH320E issue 1) and the Arcam SA10/SA20 document
(SH277E) agree on everything below, and the SA550 appears to be derived from
the SA10/SA20. Treat all of it as well-supported inference until seen on the
real amp.

- 38,400 baud, 8 data bits, no parity, 1 stop bit, no flow control.
- Only DB9 pins 2, 3 and 5 are used. Pin 5 is ground.
- The documents specify a null-modem cable to a PC, which implies the amp
  receives on pin 2 and transmits on pin 3, and that the amp's socket is male.
  **[verify]** with a meter or scope: the amp's transmit pin idles at a
  negative voltage relative to pin 5.
- True RS232 voltage levels are assumed. The port supplies no power.
- SA550 owner's manual, page 13: "RS232 Stdby — Enables RS232 operation when
  the amplifier is in standby. Default is Off." **The owner must switch this
  on**, or the dongle cannot wake the amp.
- SA550 owner's manual: auto-standby after 20 minutes without audio by
  default.

Frame format (all values hexadecimal):

- Command: `21 <zone> <command> <length> <data...> 0D`
- Response: `21 <zone> <command> <answer> <length> <data...> 0D`
- Zone is `01`. Answer `00` means success; `82`–`86` are errors (`85` is
  "command invalid at this time").
- The amp answers within 3 seconds, and may also send unsolicited frames when
  its state changes from the front panel or remote.
- The SA750 document's worked examples contain errors. Parse by the length
  byte, never by a fixed frame size.

Commands the firmware uses:

| Purpose | Bytes | Expected reply |
|---|---|---|
| Query power | `21 01 00 01 F0 0D` | `21 01 00 00 01 <00 standby / 01 on> 0D` |
| Power on | `21 01 00 01 01 0D` | as above, data `01` |
| Query input | `21 01 1D 01 F0 0D` | `21 01 1D 00 01 <input> 0D` |
| Select STB | `21 01 1D 01 05 0D` | as above, data `05` |

On the SA750 the input reply's high nibble flags processor mode (`15` is STB
in processor mode), so compare only the low nibble with `5`.

**[decided]** The owner's fixed volume comes from processor mode on the STB
input. The expected healthy reply is therefore `15`. The firmware never
changes processor mode; it selects STB with the plain code `05`, and bring-up
confirms the amp keeps processor mode when selected that way.

Fallback commands, if the direct ones are rejected on the SA550 (simulated
remote-control codes):

| Purpose | Bytes |
|---|---|
| Power on | `21 01 08 02 10 7B 0D` (may need sending twice) |
| Select STB | `21 01 08 02 10 64 0D` |

Useful probes during bring-up: model query `21 01 5E 01 F0 0D`, and the
ASCII string `AMX\r`.

Research files, including the downloaded PDFs, are in the session scratchpad
and are not in the repository. The builder should save the three source PDFs'
URLs (section 12) in `docs/research.md` with the findings above.

## 4. System overview

```
WiiM trigger jack                                         SA550 DB9 (male)
  3.5 mm plug ──cable──┐                          ┌──cable── DB9 female plug
                       │                          │
            ┌──────────┴──────────────────────────┴─────────┐
            │ +12V ─ R ─ TVS ─ diode ─ 3.3 V regulator      │
            │                     │                         │
            │              ATtiny412 ── SP3232 ── TX, RX    │
            │                │    │                         │
            │              LED   programming footprint      │
            └───────────────────────────────────────────────┘
                    board inside a two-part printed shell
```

Two off-the-shelf cables are each cut, and the cut ends soldered to the board
**[decided]**. Because the wires are hand-soldered, transmit and receive can
be swapped at the pads if the pin inference in 3.2 is wrong, and the cable
type (null-modem or straight) does not matter.

## 5. Electronics

### 5.1 Circuit

Power path, in order from the trigger pad:

1. **R1, 100 Ω series resistor.** Limits inrush into the input capacitor to
   about 120 mA, inside the trigger's 220 mA rating, and gives the TVS
   something to work against. It drops about 1.5 V at 15 mA.
2. **D2, SMF15CA TVS to ground.** Clamps spikes below the regulator's 30 V
   limit. **[call]** Cheap insurance; a "preferred extended" part.
3. **D1, B5819W series Schottky.** Reverse-polarity protection in the
   supply wire.
   **D4, a second B5819W, in the return wire** between the trigger's ground
   pad and the board's ground **[decided 2026-11-11]**. Without it, swapped
   trigger wires would put the WiiM's +12 V on the board's ground, which is
   shared with the amp and, through the audio cable, with the WiiM, and so
   short the WiiM's trigger output. With both diodes a miswire is harmless
   to the dongle and to the WiiM.
4. **C1, 10 µF 25 V.** Input capacitor.
5. **U1, HT7533-1, 3.3 V regulator** (30 V maximum input, 100 mA), with
   **C2, 10 µF** on its output.

Expected load is under 15 mA against the trigger's 220 mA rating; regulator
dissipation is about 0.1 W.

Controller: **U2, ATtiny412-SSNR** (SOIC-8) **[decided: Microchip, because the
owner has an ICD 5]**, with a 100 nF decoupling capacitor.

| Pin | Port | Use |
|---|---|---|
| 1 | VDD | 3.3 V |
| 2 | PA6 | USART transmit, to U3 T1IN |
| 3 | PA7 | USART receive, from U3 R1OUT |
| 4 | PA1 | debug trace output (logic level), to a test pad |
| 5 | PA2 | spare, to a test pad |
| 6 | PA0 | UPDI, to the programming footprint only |
| 7 | PA3 | status LED |
| 8 | GND | ground |

The clock is the internal oscillator at its default 3.33 MHz; no crystal.

Serial driver: **U3, SP3232EEY** (TSSOP-16) with five 100 nF capacitors (two
charge-pump, V+, V−, supply decoupling), running from 3.3 V.

- Channel 1 carries transmit and receive. Receive is wired so that the
  firmware can read the amp's state **[decided]**.
- Channel 2 is unused: tie T2IN to ground, leave R2IN and R2OUT open.
- **R3, 10 kΩ pull-up on T1IN**, so the line to the amp stays idle while the
  controller is in reset or being programmed. **[call]**
- With no amp connected, the receiver's internal pull-down makes the
  controller see an idle line.

Status: **D3, red 0603 LED** with **R2, 1 kΩ**, driven from PA3. **[call:
the LED itself; the owner agreed to it]**

### 5.2 Connections to the outside

- **Trigger end:** two wire pads, `+12V` and `GND`.
- **Amp end:** three wire pads, `TX` (dongle output, to DB9 pin 2), `RX`
  (dongle input, from DB9 pin 3), `GND` (DB9 pin 5). The serial cable's shield
  and unused cores are trimmed back and not connected. **[call]**
- Each wire pad is a plated through-hole. Between each pad and the board end
  is an unplated strain-relief hole **[decided]**: the wire goes down through
  the strain-relief hole, along the underside, and up through its pad to be
  soldered on top. Starting sizes: 1.0 mm drill pads on 2.54 mm pitch, 1.5 mm
  strain-relief holes. The builder adjusts these to the real wire.
- Silkscreen labels every wire pad, and marks DB9 pin numbers at the amp end.

### 5.3 Programming and test access

- A **Tag-Connect TC2030-NL footprint** (six pads, three alignment holes, no
  parts fitted) is the programming port **[decided: the owner has a
  TC2030-MCP-NL cable, whose RJ12 plug goes straight into the ICD 5]**. Pad
  assignment follows that cable's Microchip ICSP order. The builder re-checks
  it against the Tag-Connect datasheet before layout. **[verify]**

  | Pad | Cable signal | Board connection |
  |---|---|---|
  | 1 | MCLR / VPP | not connected |
  | 2 | VDD | 3.3 V |
  | 3 | GND | ground |
  | 4 | PGD | UPDI (PA0) |
  | 5 | PGC | not connected |
  | 6 | AUX | not connected |

  Pads 1, 5 and 6 stay unconnected **[call]** because what the ICD 5 drives
  on them in UPDI mode is not confirmed, and pad 1 can carry a 12 V pulse.
- The underside behind the footprint is kept clear so the cable can be held
  or clipped in place.
- Test pads, about 1 mm, for: 3.3 V, ground, the protected 12 V rail, logic
  transmit, logic receive, UPDI, PA1 and PA2. These let a scope probe reach
  every signal, and allow a different programmer to be wired on if ever
  needed.
- **Considered and rejected [call]: an 8-pin connector for the ICD 5's
  built-in debug UART.** The owner suggested it. The ICD 5 user's guide puts
  the target's transmit line on jack pin 8, and states that a 6-pin plug loses
  pins 1 and 8, so the TC2030-MCP-NL cannot carry it. Reaching it needs an
  RJ45 or an 8-way header on the board, which would roughly double the size
  of the dongle. Section 7.2 gives two ways to see the amp's replies without
  it.

### 5.4 Board

- Two layers, 1.6 mm, all parts on the top side, ground pour on the bottom.
- Target outline about 12 × 38 mm; hard limits 14 mm wide, 45 mm long, and
  JLCPCB's 10 × 10 mm minimum for economic assembly.
- Passives are 0603 (0805 for the 10 µF capacitors). Nothing smaller.
- Keep parts at least 1 mm from the board edge.
- Fabrication target: JLCPCB economic assembly, single-sided, 5 boards with 2
  assembled (the minimums).

### 5.5 Known electrical risk

The dongle joins the WiiM's ground to the amp's ground through a second path,
alongside the audio cable. This is how ordinary trigger cables behave and is
unlikely to cause hum. If it does, the remedy is an isolated revision; that is
out of scope here.

Because of D4, the dongle's supply return current (5 to 15 mA) flows through
that ground path whenever the amp is connected, instead of sharing it with the
trigger cable. The estimated effect on the audio ground is tens of microvolts;
see `docs/hardware-calculations.md`, item 7.

## 6. Bill of materials and stock

Stock and status were read from JLCPCB's parts API on 2026-11-10. "Basic"
parts carry no fee; each "extended" part adds a one-off loading fee per order
(about $3, from memory **[verify]**).

| Ref | Part | LCSC | Package | Status | Stock |
|---|---|---|---|---|---|
| U2 | ATtiny412-SSNR | C1337190 | SOIC-8 | Extended | 2,167 |
| U3 | SP3232EEY-L/TR | C13482 | TSSOP-16 | Basic | 256,189 |
| U1 | HT7533-1 | C14289 | SOT-89 | Basic | 229,965 |
| D1, D4 | B5819W | C8598 | SOD-123 | Basic | 728,473 |
| D2 | SMF15CA | C19077510 | SOD-123FL | Preferred extended | 8,220,203 |
| D3 | KT-0603R (red LED) | C2286 | 0603 | Basic | 6,247,584 |
| C1, C2 | 10 µF 25 V | C15850 | 0805 | Basic | 8,504,725 |
| C3–C8 | 100 nF 50 V | C14663 | 0603 | Basic | 36,675,703 |
| R1 | 100 Ω | C22775 | 0603 | Basic | 8,862,541 |
| R2 | 1 kΩ | C21190 | 0603 | Basic | 25,437,850 |
| R3 | 10 kΩ | C25804 | 0603 | Basic | 45,529,990 |

The only part with thin stock is the controller. Mitigations:

- **Pin-compatible alternates** on the same footprint, both extended and in
  stock on the same date:
  - ATtiny402-SSNR, C616056, 1,871 in stock. Same 4 KB flash and 256 B RAM.
  - ATtiny202-SSNR, C2052951, 3,711 in stock. Only 2 KB flash and 128 B RAM.
- **Firmware size budget:** it must fit the ATtiny412 and ATtiny402. Fitting
  the ATtiny202 is desirable, not required.
- **Stock gate:** a script (section 9) re-checks every BOM line against
  JLCPCB before fabrication files are released.
- **Reserve early:** JLCPCB lets customers buy parts into a private parts
  library ahead of an order. If that is confirmed **[verify]**, the owner buys
  the controllers as soon as the schematic is frozen.

## 7. Firmware

### 7.1 Behaviour

**[decided]** unless marked.

1. Start as soon as power is present. No deliberate start-up delay beyond
   what the serial driver's charge pump needs (tens of milliseconds).
   **[call]** A delay would filter the WiiM's reboot pulse but slow every
   normal start.
2. Query the amp's power state. If it reports standby, or does not answer,
   send power-on. **[call: sending power-on when there is no answer]**
3. While waiting for the amp to come on, re-query about twice a second.
4. Once the amp reports on, wait a short settle time, then query the input.
   If it is not STB, select STB, and confirm by querying again.
5. Once the amp is on and on STB, re-check power and input every 2 seconds
   for as long as the dongle has power. Send a power-on or select command only
   when a check shows it is needed.
6. Also act on unsolicited frames: if the amp announces a power or input
   change, re-check immediately instead of waiting for the next poll.
   **[call]**
7. Never send power-off. Never touch volume, direct mode, or anything else.
8. No explicit heartbeat command. The regular queries, and re-waking the amp
   if it does go to standby, already give "keep it awake". **[call]**

When the trigger drops, the dongle simply loses power. A frame cut off
mid-send is harmless; the amp discards it.

All timings (poll interval, reply timeout, settle time, retry counts) are
named constants in one header, because they will be tuned on the real amp.
Starting values: poll 2 s; reply timeout 3 s once the amp is known to be on
(the protocol allows the amp 3 s) and 1 s while it is not; settle 1.5 s.

Status LED **[call]**:

| Pattern | Meaning |
|---|---|
| Fast blink | No answer from the amp |
| Slow blink | Amp answering; waking it or changing input |
| Solid | Amp on and on STB |

### 7.2 Structure

- Plain C built with avr-gcc; no Arduino framework. **[call]**
- Split so the logic can be tested on the Linux box without hardware:
  - **Protocol:** builds command frames and parses a byte stream into frames.
    Tolerates garbage, partial frames, unsolicited frames and error answers.
    Pure C, no hardware access.
  - **Controller:** the state machine in 7.1, driven by "frame received" and
    "time passed" events. Pure C, no hardware access.
  - **Hardware layer:** USART, a millisecond tick, the LED, the watchdog.
    The only part that touches registers.
- Host-side unit tests cover the protocol parser and the controller, using a
  simulated amp that can be told to be in standby, on the wrong input, silent,
  slow, or returning errors.
- Compile-time options select the fallback command set from 3.2.
- **Debug build [call]:** the LED alone cannot tell a normal answer from an
  error answer, so a compile-time option adds two ways to see what the amp
  actually said. The release build has neither.
  - **Live trace:** every byte received from the amp, and a marker for each
    command sent, is copied out of PA1 as logic-level serial. Read it with the
    scope's serial decode on the PA1 test pad.
  - **Stored log:** the first replies to each kind of command are saved in
    the controller's EEPROM (128 bytes on the ATtiny412), and read back
    through the ICD 5 afterwards. This works when the dongle has to be flashed
    in one place and tried at the amp in another.
- Robustness:
  - Watchdog timer enabled.
  - Brown-out detection enabled, so the controller resets cleanly as the
    trigger rail collapses.
  - Baud rate set with the factory oscillator-error calibration for 3 V.
- Fuses are documented in the repository and must leave PA0 as UPDI.

### 7.3 Building and flashing

- The firmware builds on the headless box (Ubuntu 26.04). The box has Docker
  without needing sudo, and no passwordless sudo, so the toolchain runs in a
  container. **[call]** Ubuntu's own `gcc-avr` and `avr-libc` packages already
  support the ATtiny412; no Microchip device pack is needed.
- The ICD 5 officially supports programming and debugging the ATtiny412 over
  UPDI (Microchip device support table).
- **Cable chain, nothing to buy:** the TC2030-MCP-NL's RJ12 plug goes
  straight into the ICD 5's jack, and its spring pins press onto the board's
  footprint. In UPDI mode the ICD 5 uses its PGD line for UPDI data, plus
  target voltage and ground.
- **Power while programming:** normally the board is powered from the trigger
  (or a 12 V bench supply) and the ICD 5 only senses the voltage. The ICD 5
  can also supply 3.3 V itself; whether back-feeding the regulator's output
  that way is acceptable is **[verify]**.
- Flashing route, in order of preference:
  1. **ICD 5 on the headless box**, driven by MPLAB IPE's command-line tool
     (`ipecmd`, part of MPLAB X v6.35, a 1.1 GB install). This is the only
     command-line tool that drives an ICD 5; pymcuprog and avrdude do not.
     It is untested here, and there is a known installer problem on recent
     Ubuntu. **[verify]** Installing it, or letting a container reach the USB
     device, may need the owner's sudo password once.
  2. **ICD 5 on the owner's desktop** with MPLAB IPE, using `.hex` files built
     on the box.
  3. **A 3.3 V USB-serial adapter with SerialUPDI** (pymcuprog), wired to the
     UPDI, 3.3 V and ground test pads. This needs one 1 kΩ resistor and works
     with open-source tools from the headless box. Last resort only; the
     owner does not have an adapter.
- The repository documents the exact commands that were found to work.
- **Written bring-up procedure [decided]:** as well as supporting a live
  flash-and-watch loop with the box beside the amp, the repository includes a
  step-by-step guide the owner can follow alone. It comes with ready-built
  `.hex` files for each command variant (direct commands, the fallback
  remote-control codes, and debug versions of each), so alternatives can be
  tried at the amp without rebuilding. Each step says what to expect on the
  LED and what to read back from the stored log.

## 8. Enclosure

- A cylinder split lengthwise into two half-shells, printed by JLC3DP
  **[decided]** in black MJF PA12 nylon **[call]**.
- Held together with small self-tapping screws **[decided between screws and
  clips; screws are the author's recommendation]**, so it can be reopened to
  reflash. Screw size, count and position are the builder's choice; M2 is the
  starting point.
- The board sits on ledges inside and cannot slide.
- A collar at each end grips its cable's outer jacket when the screws are
  tightened, so a pull on a cable never reaches the solder joints.
- A small hole over the LED.
- The programming footprint is reached by opening the shell.
- Appearance does not matter; protection does. **[decided]**
- Size as built: 20 mm diameter and 72.8 mm long (`docs/enclosure.md`). The
  first estimate was 17–18 × 60 mm; the board grew to 13 × 45 mm, and 20 mm
  is the least that leaves the wall the screws need. Smaller is better but
  not at the cost of wall strength.
- The model is parametric and generated by a script on the headless box,
  with the two cable jacket diameters as parameters. **[call]** The fit is
  checked against solids built from the board layout and part heights (the
  board's 3D model from KiCad has no parts on it).
- **Cables:** `docs/cables.md` names the two cables the board's holes are
  sized for, with jacket diameters of 3.7 mm and 4.8 mm from the makers'
  figures. The shell is designed to those and checked against the owner's
  caliper measurement when the cables arrive.
- JLC3DP's published rules for MJF and SLS nylon, which the model must meet:

  | Rule | Value |
  |---|---|
  | Wall thickness | at least 1.2 mm; more than 1.5 mm around screws |
  | Smallest hole | 1.5 mm diameter (so the LED hole is 2 mm) |
  | Clearance between the mating halves | 0.2–0.4 mm |
  | Tolerance | ±0.3 mm; holes tend to come out small |
  | Embossed or engraved text | at least 0.8 mm deep and wide |

- Because of the ±0.3 mm tolerance, the cable collars use crushable ribs and
  rely on screw pressure, not on an exact bore.
- Screws as built **[verify with the first print]**: four 2.2 × 8 mm
  thread-forming screws for plastics (named in `docs/enclosure.md`), into
  pilot holes modelled at 1.8 mm with at least 1.6 mm of plastic round them,
  through 2.6 mm clearance holes in the other half, heads in 5.2 mm
  counterbores that admit a PZ1 screwdriver.
- The two halves are uploaded as two separate files in one order.

## 9. Tooling and verification

- **EDA: KiCad 10** **[decided on the author's recommendation]**, run
  headless. The KiCad project files are the source of truth.
- Schematic and board are produced by Python scripts, never by hand-typing
  KiCad file syntax. The library used to generate them, and whether tracks are
  scripted or autorouted, are the builder's choice.
- Symbols and footprints for JLCPCB parts may be pulled with easyeda2kicad;
  every footprint is checked against its datasheet.
- Gates that must pass before anything is called done:
  - Electrical rules check with no errors.
  - Design rules check with no errors, including schematic-to-board parity.
  - A rendered image of the board and a PDF of the schematic, inspected.
  - Stock gate: every BOM line in stock at JLCPCB, at a quantity comfortably
    above the order. The check is a script in the repository, re-run on the
    day of ordering. It uses JLCPCB's unofficial parts API, which may change.
  - Firmware unit tests pass, and the build fits the flash budget.
- Outputs for JLCPCB: Gerbers, drill files, BOM and placement file in
  JLCPCB's column format, with part rotations checked.
- **Human review without KiCad [decided]:** everything the owner needs to
  review is a PDF or a Markdown file in the repository. Opening KiCad is
  optional. The review set is:
  - the schematic, as a PDF;
  - the board, as a PDF with one page per view (top copper and silkscreen,
    bottom copper, a dimensioned outline with hole positions), plus rendered
    images of both sides;
  - the design calculations, in Markdown (power budget, voltage drops,
    dissipation, inrush, LED current, serial timing error, ratings margins);
  - the datasheet pin review and the review checklist, in Markdown.
- The owner also uses JLCPCB's own preview on upload, before paying.

Suggested repository layout **[call]**:

```
docs/        design, research notes, bring-up guide
hardware/    KiCad project, generator scripts, libraries, fabrication outputs
firmware/    source, host tests, build files
enclosure/   model script and exported files
tools/       stock check, environment setup
```

## 10. Order of work

1. Set up the tools on the headless box.
2. Schematic, then board, with the gates above; owner's visual review.
3. Firmware and host tests, ready before boards arrive.
4. Owner buys the two cables and measures them; enclosure is finalised.
5. Stock gate; owner orders boards and shell.
6. Bring-up on the real hardware (section 11), tuning firmware as needed.

Steps 2, 3 and the first draft of 4 do not depend on each other.

## 11. Bring-up and acceptance

Checks the owner can make at any time before the boards arrive:

- Trigger polarity and voltage at the WiiM's jack.
- With "RS232 Stdby" on, which of DB9 pins 2 and 3 idles negative.
- Cable jacket diameters.

On the bench, in order:

1. Power the bare board from the trigger; confirm 3.3 V and a current far
   below the 220 mA limit.
2. Flash the firmware.
3. Scope the `TX` pad: RS232 levels, 38,400 baud, the power query repeating.
4. Connect the amp, with the debug build. Read the amp's replies on the
   live trace or from the stored log, then work through wake and input
   selection, falling back to the alternate commands if needed.
5. Before the first input-select test, turn the WiiM's output down or
   disconnect the speakers. Confirm that selecting STB over serial leaves
   processor mode on: the input query should answer `15`, and the volume
   should stay fixed.

The dongle is accepted when, on the real system:

- From standby, a rising trigger brings the amp on and to STB with no
  intervention, and the dongle adds no more than about a second to the amp's
  own start-up time.
- With the trigger high, switching the amp to another input or to standby is
  corrected within 5 seconds.
- In steady state there are no audible clicks, mutes or display flicker
  caused by the dongle.
- With the trigger low, the dongle sends nothing, and the amp times out to
  standby on its own.
- The shell closes, grips both cables, and a firm pull on either cable does
  not move the board.

## 12. Sources

- JBL SA750 RS232 protocol, SH320E issue 1:
  https://global.jbl.com/on/demandware.static/-/Sites-masterCatalog_Harman/default/dw0bea52b6/pdfs/SH320E_RS232_SA750_iss1.pdf
- JBL SA550 Classic owner's manual:
  https://mm.jbl.com/on/demandware.static/-/Sites-masterCatalog_Harman/default/dw2b14c090/pdfs/JBL%20SA550%20Classic%20Owner's%20Manual%20EN.pdf
- Arcam SA10/SA20 RS232 protocol, SH277E issue B:
  https://www.arcam.co.uk/ugc/tor/SA10/Custom%20Installation%20Notes/SH277E_RS232_SA10_SA20_B.pdf
- WiiM 12 V trigger FAQ:
  https://faq.wiimhome.com/en/support/solutions/articles/72000602073-how-to-use-the-12v-trigger-on-wiim-pro-wiim-pro-plus-or-wiim-ultra-
- KiCad 10 command-line documentation:
  https://docs.kicad.org/10.0/en/cli/cli.html
- JLCPCB assembly capabilities:
  https://jlcpcb.com/capabilities/pcb-assembly-capabilities
- MPLAB ICD 5 user's guide, pinouts:
  https://onlinedocs.microchip.com/oxy/GUID-1FB866E7-F8EE-4F6C-92ED-0F60E926A717-en-US-3/GUID-E6BF3C06-AD5E-428C-BA02-FCA445F48BC7.html
- Microchip device support table:
  https://packs.download.microchip.com/DeviceDoc/Device_Support.pdf
- Tag-Connect TC2030-MCP-NL:
  https://www.tag-connect.com/product/tc2030-mcp-nl-6-pin-no-legs-cable-with-rj12-modular-plug-for-microchip-icd
- pymcuprog (SerialUPDI): https://github.com/microchip-pic-avr-tools/pymcuprog
- JLC3DP design guideline:
  https://jlc3dp.com/help/article/3D-Printing-Design-Guideline

## 13. Open items

- Everything marked **[verify]** above. None of these blocks planning; each
  is checked at the step that depends on it.
