# Enclosure

## Screws

The shell needs four screws. They cut their own thread in the lower half.

**Buy:** thread-forming screw for plastics, 2.2 mm × 8 mm, Pozi pan head.
The one the shell is sized for is Westfield Fasteners **WF67956**,
"2.2mm x 8mm Pozi Pan Thread Forming Screw for Plastics in BZP":
<https://www.westfieldfasteners.co.uk/Thread-Forming-Screws/Pozi-Pan-Thread-Forming-Screw-for-Plastics-2.2mmx8-BZP.html>

The page showed £1.57 excluding VAT on 2026-11-11 but did not say for how
many, or whether it was in stock. Check before ordering. Cromwell and
Boltworld list the same size.

**Screwdriver:** Pozidriv size 1 (PZ1).

| Figure | The screw | The shell | Source |
|---|---|---|---|
| Thread diameter | 2.2 mm | 2.6 mm clearance hole in the upper half | Westfield data sheet, table 1 |
| Head diameter | 3.9 mm | 5.2 mm counterbore; heads up to 4.2 mm fit | table 1 |
| Head height | 1.5 mm | head sits 3.0 mm above the split, below the outside surface | table 1 |
| Recess | PZ1 | the counterbore admits a PZ1 driver's 4.5 mm blade even if it prints 0.3 mm small | table 1; Wera 355 PZ 1 × 80 |
| Pilot hole in nylon | 0.75 × thread = 1.65 mm (PA 6 and PA 6.6) | modelled 1.8 mm, 5.5 mm deep | data sheet, table 2 |
| Plastic round the hole | boss 1.85 × thread = 4.1 mm across, so a 1.2 mm wall | 1.6 mm or more everywhere | table 2 |
| Thread engagement | at least 2 × thread = 4.4 mm | 4.4 mm | data sheet, "useful principles" |
| Mouth of the hole | chamfered or counterbored to the thread's diameter | 2.4 mm across, 0.6 mm deep | data sheet, "useful principles" |

Data sheet: <https://www.westfieldfasteners.co.uk/Standards/ThreadForming-PoziPan30.html>.
A second table of hole sizes for this type of screw gives the same 1.65 mm
for PA 6 and PA 6.6:
<https://cdn.shopify.com/s/files/1/0056/7856/3437/files/MetPTholesize.pdf>.

**The pilot size is untried.** Neither table lists PA 12, which is what
JLC3DP prints; PA 6 is the nearest. The hole is modelled at 1.8 mm, not
1.65 mm, because JLC3DP says its holes come out small and does not say by
how much. The first print settles it:

- If a screw turns without tightening, the holes are too big. Change
  `PILOT_D` in `enclosure/params.py` to 1.6.
- If a screw is very stiff, or the plastic beside it whitens or bulges, the
  holes are too small. Change `PILOT_D` to 2.0.

A screw that fits is one with a 2.2 mm thread, 8 mm long, and a head no
bigger than 4.2 mm across and 1.7 mm high. An ordinary self-tapping screw of
that size (DIN 7981, No. 2) would also go in, but its coarser thread loads
the plastic more; use the plastics type if you can get it.
