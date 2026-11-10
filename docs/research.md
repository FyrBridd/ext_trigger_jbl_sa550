# Research notes: the amp's serial protocol and the WiiM's trigger

Gathered 2026-11-10 from published documents. **Nothing here has been tried
on the owner's SA550.** Each fact says where it comes from:

- **[SA550]** the JBL SA550 Classic owner's manual.
- **[SA750]** JBL's RS232 document for the SA750 (SH320E issue 1).
- **[SA10]** Arcam's RS232 document for the SA10 and SA20 (SH277E issue B),
  used as a cross-check: the SA550 appears to be derived from those amps.
- **[inferred]** worked out from the above, not stated in any of them.

No RS232 protocol document for the SA550 itself was found. The owner states
that it uses the SA750's protocol.

## The amp's RS232 port

| Fact | Source |
|---|---|
| The SA550 has a rear "RS232" port. | [SA550] |
| "RS232 Stdby — Enables RS232 operation when the amplifier is in standby. Default is Off." **It must be switched on in the amp's menu, or the dongle cannot wake the amp.** | [SA550] p. 13 |
| Auto-standby after 20 minutes with no audio and no user interaction, by default. | [SA550] |
| 38,400 baud, 8 data bits, no parity, 1 stop bit, no flow control. | [SA750] p. 3, [SA10] |
| Only DB9 pins 2, 3 and 5 are used; pin 5 is ground. | [SA750] p. 3 |
| The cable to a PC is a null-modem cable with a female DB9 at each end. | [SA750] p. 3, [SA10] |
| So the amp's socket is male, it receives on pin 2 and transmits on pin 3. | [inferred] |
| True RS232 voltage levels; the port supplies no power. | [inferred] |

Check before trusting the pin inference: with "RS232 Stdby" on, the amp's
transmit pin idles at a negative voltage against pin 5.

## Frame format

All values are hexadecimal. [SA750] pp. 3–4, same in [SA10].

- Command, to the amp: `21 <zone> <command> <length> <data...> 0D`
- Response, from the amp: `21 <zone> <command> <answer> <length> <data...> 0D`
- Zone `01` is the main zone.
- `<length>` counts the data bytes only.
- The amp answers every command within 3 seconds, and may also send frames
  on its own when its state is changed from the front panel or remote.
- The SA750 document's worked examples contain mistakes (a data length that
  disagrees with its table, a value described wrongly). The firmware sizes
  each frame from its length byte and never from a fixed layout.

Answer codes:

| Code | Meaning |
|---|---|
| `00` | Success; the data is the current state |
| `82` | Zone invalid |
| `83` | Command not recognised |
| `84` | Parameter not recognised |
| `85` | Command invalid at this time |
| `86` | Invalid data length |

## Commands the firmware uses

| Purpose | Bytes | Reply when it works | Source |
|---|---|---|---|
| Ask the power state | `21 01 00 01 F0 0D` | `21 01 00 00 01 xx 0D`, `xx` = `00` standby, `01` on | [SA750], [SA10] |
| Switch on | `21 01 00 01 01 0D` | as above with `01` | [SA750] table; no worked example |
| Ask the input | `21 01 1D 01 F0 0D` | `21 01 1D 00 01 xx 0D` | [SA750], [SA10] |
| Select STB | `21 01 1D 01 05 0D` | as above with `05` or `15` | [SA750], [SA10] |

Input codes: `01` Phono, `02` AUX, `03` PVR, `04` AV, `05` STB, `06` CD,
`07` BD, `08` SAT. [SA750], [SA10]. The SA550's manual confirms it has an
input named STB; that its code is `05` is [inferred].

In the input reply, the high half of the byte is `1` when the input is in
processor mode (fixed gain), so `15` means "STB, processor mode". [SA750].
The owner uses processor mode on STB, so `15` is the expected healthy reply.
The firmware compares only the low half with `5`.

## Fallback commands

If the SA550 rejects the direct commands, the protocol can also simulate
remote-control buttons. [SA750]; the Home Assistant Arcam integration uses
these for power on SA-series amps.

| Purpose | Bytes | Note |
|---|---|---|
| Power on | `21 01 08 02 10 7B 0D` | Reports say it sometimes needs sending twice. |
| Select STB | `21 01 08 02 10 64 0D` | |

The reply echoes the command with an answer byte, usually followed by a
status frame for what changed.

Useful probes when exploring by hand: `21 01 5E 01 F0 0D` asks the model
name; the ASCII text `AMX` followed by a carriage return asks for an
identification string.

## The WiiM Ultra's trigger output

| Fact | Source |
|---|---|
| 3.5 mm jack; mono and stereo plugs both work. | WiiM FAQ |
| 12 V, "rated at 220 mA". | WiiM FAQ |
| Goes high when playback starts or the unit leaves standby; low when it enters standby. | WiiM FAQ, manual |
| Polarity is not stated. Tip positive is the convention. | not confirmed |
| A brief pulse during WiiM reboots, and occasional spurious trigger-on from standby on recent firmware, are reported. | WiiM forum |

Because the trigger rises when playback starts, the amp will miss the first
second or two of the first track unless the WiiM is woken first.

## Sources

- JBL SA750 RS232 protocol, SH320E issue 1:
  https://global.jbl.com/on/demandware.static/-/Sites-masterCatalog_Harman/default/dw0bea52b6/pdfs/SH320E_RS232_SA750_iss1.pdf
- JBL SA550 Classic owner's manual:
  https://mm.jbl.com/on/demandware.static/-/Sites-masterCatalog_Harman/default/dw2b14c090/pdfs/JBL%20SA550%20Classic%20Owner's%20Manual%20EN.pdf
- Arcam SA10/SA20 RS232 protocol, SH277E issue B:
  https://www.arcam.co.uk/ugc/tor/SA10/Custom%20Installation%20Notes/SH277E_RS232_SA10_SA20_B.pdf
- WiiM 12 V trigger FAQ:
  https://faq.wiimhome.com/en/support/solutions/articles/72000602073-how-to-use-the-12v-trigger-on-wiim-pro-wiim-pro-plus-or-wiim-ultra-
- Home Assistant Arcam integration: https://www.home-assistant.io/integrations/arcam_fmj/
