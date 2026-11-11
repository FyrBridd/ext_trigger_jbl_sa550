# Cables

What to buy for the two ends of the dongle, and the check that the board's
wire holes suit them. Researched 2026-11-10. Dimensions marked **[DS]** are
from the manufacturer's drawing or specification; **[typical]** are the usual
figures for that kind of cable, where the maker publishes none; **[derived]**
are worked out. Stock and prices were read from DigiKey UK that day and will
move. I assumed a UK buyer; say if that is wrong.

## What to buy

| For | Part | DigiKey UK price | What it is |
|---|---|---|---|
| Trigger end | Tensility **053-0279R** | £2.85 | 3.5 mm mono plug on 1.83 m of two-core cable. The free end comes stripped and tinned. |
| Amp end | StarTech **MXT1001MBK** | £6.13 | 1 m serial cable, DB9 male to DB9 female, wired straight through. Cut the male end off and keep the female end. |

Links:
- https://www.digikey.co.uk/en/products/detail/tensility-international-corp/053-0279R/701166
- https://www.startech.com/en-gb/cables/mxt1001mbk

Both are stocked by DigiKey UK, whose delivery charge on a small order
(£22 under £65 when checked) is more than the parts. The StarTech cable is
also sold by most computer suppliers. The trigger cable is the harder one to
find elsewhere; any 3.5 mm mono or stereo lead with separate insulated cores
of about 1 mm will do in its place, but check it against the table below.

### Why not a loose cable and a solder-cup connector

An earlier version of this page recommended a solder-cup DB9 with Tensility
30-01424 three-core cable. The owner found that cable is now sold only in
5 m lengths, so the ready-made StarTech cable is used instead.

## Wire sizes, and the holes on the board

| | Trigger cable 053-0279R | Serial cable MXT1001MBK |
|---|---|---|
| Conductor | 24 AWG, 11 × 0.16 mm [DS] | 28 AWG [DS]; usually 7 × 0.127 mm [typical] |
| Bare conductor diameter | about 0.64 mm [derived] | about 0.38 mm [derived] |
| One insulated core | 1.0 ± 0.08 mm [DS] | **not published**; 0.95 ± 0.10 mm [typical] |
| Number of cores | 2, plus a spiral screen | 9 expected, plus foil and a drain wire |
| Outer jacket | 3.7 ± 0.2 mm [DS] | 4.8 mm [DS] |

| Hole on the board | Size | Wire through it | Clearance on diameter |
|---|---|---|---|
| Strain relief, trigger end | 1.5 mm | 0.92–1.08 mm core | 0.37–0.63 mm |
| Strain relief, amp end | 1.5 mm | 0.85–1.05 mm core [typical] | 0.40–0.70 mm |
| Solder pad, trigger end | 1.0 mm | about 0.70 mm tinned conductor | 0.22 mm or more |
| Solder pad, amp end | 1.0 mm | about 0.45 mm tinned conductor | 0.47 mm or more |

The clearances allow for JLCPCB making an unplated hole up to 0.05 mm small
and a plated one up to 0.08 mm small.

**The holes already on the board suit both cables, so the board does not
change.** Two honest caveats:

- **The amp-end fit is on the loose side.** The serial cable's wires are
  thinner than the trigger cable's, so they have about half a millimetre of
  room in the solder holes. They solder perfectly well like that; the joint
  just needs holding still while it cools. I left those holes at 1.0 mm so
  that a 24 AWG cable can still be used there later.
- **The serial cable's core size is not a published figure.** If its cores
  turned out fatter than usual they would still pass: anything up to 1.25 mm
  goes through the strain-relief holes. Measure one core with calipers when
  the cable arrives, before soldering.

The strain-relief holes are a first line of defence only: a wire threaded
down through one hole and up through the next cannot be pulled straight out.
The shell's collars, clamped on the cable jackets, are what take a real pull.

The fit is checked automatically: `hardware/design/cables.py` holds these
figures, and a test fails if a hole is too small for them.

A wire these holes would **not** suit: ordinary 22 AWG hook-up wire, which
is about 1.6 mm over its insulation and will not pass a 1.5 mm hole.

The jacket diameters, 3.7 mm and 4.8 mm, are what the enclosure's cable
collars are sized to (`docs/enclosure.md`). Check both with calipers when
the cables arrive, before the shell is ordered.

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

**Serial cable.** StarTech does not publish its core colours, so find the
three wires with a meter, from the female plug's pins to the cut ends.

| DB9 female pin | Board pad | Carries |
|---|---|---|
| 2 | `T` | Dongle to amp |
| 3 | `R` | Amp to dongle |
| 5 | `G` (amp end) | Ground |
| 1, 4, 6, 7, 8, 9 | — | Not used. Cut these six back to different lengths so no two bare ends can touch. |
| Drain wire and foil | — | Trim back; do not connect. |

Pins 2 and 3 swap if step A3 of the bring-up guide shows the amp transmits
on pin 2.

## What I could not confirm

- The serial cable's core insulation diameter and core colours.
- That the serial cable has all nine cores; the specification does not say.
  Only pins 2, 3 and 5 matter, and a cable sold as a serial extension will
  have those.
- The bare conductor diameters, which no document states; they follow from
  the gauge.
- Prices at CPC, Farnell and RS: their pages refused automated access.
- Anything about fit in the hand. The clearances are arithmetic, not a trial.
