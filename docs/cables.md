# Cables

What to buy for the two ends of the dongle, and the check that the board's
wire holes suit them. Researched 2026-11-10. Dimensions marked **[DS]** are
from the manufacturer's drawing; **[derived]** are worked out from it. Stock
and prices were read from DigiKey UK that day and will move. I assumed a UK
buyer; say if that is wrong.

## What to buy

All four lines are stocked by DigiKey UK, about £7.50 of parts before VAT.
DigiKey's delivery charge on a small order is much more than the parts
(£22 under £65 when checked), so it is worth adding them to another order.

| For | Part | DigiKey price | What it is |
|---|---|---|---|
| Trigger end | Tensility **053-0279R** | £2.85 | 3.5 mm mono plug on 1.83 m of two-core cable. The free end comes stripped and tinned. |
| Amp end, cable | Tensility **30-01424**, 1 m | £3.37 per metre | Three cores (red, black, white) with a foil screen and drain wire. |
| Amp end, connector | MH Connectors **MHDB9SS** | £0.31 | DB9 female with solder cups. |
| Amp end, hood | MH Connectors **MHDPPK9-DE-K** | £0.99 | Hood with cable clamp and thumbscrews; takes cable up to 8 mm. |

Links:
- https://www.digikey.co.uk/en/products/detail/tensility-international-corp/053-0279R/701166
- https://www.digikey.co.uk/en/products/detail/tensility-international-corp/30-01424/13151644
- https://www.digikey.co.uk/en/products/detail/mh-connectors/MHDB9SS/16983851
- https://www.digikey.co.uk/en/products/detail/mh-connectors/MHDPPK9-DE-K/16984027

### Why the amp end is a connector and loose cable, not a cut serial cable

You proposed cutting an off-the-shelf serial cable. I recommend this instead,
for three reasons:

- **Known wire size.** No moulded DB9 cable I found publishes the diameter
  of its individual cores, which is the figure the strain-relief holes
  depend on.
- **Same wire both ends.** This cable is 24 AWG, like the trigger cable, so
  one hole size suits every wire. Moulded serial cables are 28 or 30 AWG.
- **Less to trim, thinner cable.** Three cores and a drain, not nine, in a
  4.1 mm jacket against about 5 mm.

The cost is three more solder joints, in the DB9's solder cups.

If you would still rather cut a ready-made cable, the StarTech
**MXT1001MBK** (1 m, DB9 male to female, 28 AWG, 4.8 mm jacket, £6.13) is
the one to use. Its cores are thinner than the holes are sized for, so they
fit, but loosely: expect about 0.9–1.0 mm cores in 1.5 mm strain-relief
holes. Its core colours are not published; buzz them out.

## Wire sizes, and the holes on the board

| | Trigger cable 053-0279R | Serial cable 30-01424 | Source |
|---|---|---|---|
| Conductor | 24 AWG, 11 × 0.16 mm | 24 AWG, 41 × 0.08 mm | [DS] |
| Bare conductor diameter | about 0.64 mm | about 0.62 mm | [derived] |
| One insulated core | 1.0 ± 0.08 mm | 1.1 ± 0.10 mm | [DS] |
| Outer jacket | 3.7 ± 0.2 mm | 4.1 ± 0.2 mm | [DS] |

| Hole on the board | Size | Smallest it may be made | Largest thing through it | Clearance |
|---|---|---|---|---|
| Strain relief (unplated) | 1.5 mm | 1.45 mm | 1.20 mm insulated core | 0.25 mm |
| Solder pad (plated) | 1.0 mm | 0.92 mm | about 0.70 mm tinned conductor | 0.22 mm |

So the holes already on the board suit these cables, and nothing on the board
changes. The fit is now checked automatically: `hardware/design/cables.py`
holds the cable figures, and a test fails if a hole is too small for them
(or so large that a wire would slop about in its strain-relief hole).

A wire it would **not** suit: ordinary 22 AWG hook-up wire, which is about
1.6 mm over its insulation and will not pass a 1.5 mm hole.

The jacket diameters, 3.7 mm and 4.1 mm, are what the enclosure's cable
collars will be sized to. With these cables bought, the enclosure can be
designed from the drawings without waiting for measurements, though a
caliper check when they arrive is still worth doing.

## Which wire goes where

**Trigger cable.** The drawing gives red as the plug's tip and black as its
sleeve.

| Wire | Plug | Board pad |
|---|---|---|
| Red | Tip, +12 V | `+` |
| Black | Sleeve, ground | `G` (trigger end) |
| Spiral screen | Not connected at the plug | Trim back; do not connect |

Check with a meter that black really is the sleeve: the drawing labels it
"ring", though the plug is mono and has none. And check the WiiM's polarity
first (`docs/bring-up.md`, step A1).

**Serial cable.** The colours are yours to choose, since you solder both
ends. This is the convention the documents assume:

| Wire | DB9 solder cup | Board pad | Carries |
|---|---|---|---|
| Red | Pin 2 | `T` | Dongle to amp |
| White | Pin 3 | `R` | Amp to dongle |
| Black | Pin 5 | `G` (amp end) | Ground |
| Drain wire and foil | Not connected | Trim back at both ends | — |

Pins 2 and 3 swap if step A3 of the bring-up guide shows the amp transmits
on pin 2.

## What I could not confirm

- Prices at CPC, Farnell and RS: their pages refused automated access.
- Whether DigiKey charges a cutting fee on cable sold by the metre.
- The bare conductor diameters, which no drawing states; they are derived
  from the strand counts.
- Anything about fit in the hand. The clearances are arithmetic, not a trial.
