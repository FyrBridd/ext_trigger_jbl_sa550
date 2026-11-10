"""The cables the board's wire holes are sized for.

Figures are from the manufacturers' drawings (read 2026-11-10) unless marked.
The wire-pad footprint is checked against them by the tests, and the enclosure
will take its collar sizes from the jacket diameters.
See docs/cables.md for what to buy and how the wires map to the pads.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Cable:
    name: str
    part: str
    source: str
    conductor: str
    conductor_dia_max: float     # bare stranded conductor, mm (derived, with allowance for tinned ends)
    insulation_dia_max: float    # one insulated core, mm, at the top of its tolerance
    jacket_dia: float            # outer jacket, mm, nominal
    jacket_tolerance: float


# Trigger end: 3.5 mm mono plug on 1.83 m of two-core cable, free end stripped and tinned.
TRIGGER = Cable(
    name="WiiM trigger cable",
    part="Tensility 053-0279R",
    source="https://tensility.s3.us-west-2.amazonaws.com/uploads/pdffiles/053-0279R.pdf",
    conductor="24 AWG, 11 x 0.16 mm",
    conductor_dia_max=0.70,      # about 0.64 mm bare; 0.70 allows for the factory-tinned end
    insulation_dia_max=1.08,     # 1.0 +/- 0.08 mm
    jacket_dia=3.7, jacket_tolerance=0.2,
)

# Amp end: three-core screened cable, soldered to a DB9 female solder-cup connector.
SERIAL = Cable(
    name="amp serial cable",
    part="Tensility 30-01424",
    source="https://tensility.s3.us-west-2.amazonaws.com/uploads/pdffiles/30-01424.pdf",
    conductor="24 AWG, 41 x 0.08 mm",
    conductor_dia_max=0.70,      # about 0.62 mm bare; 0.70 allows for tinning by hand
    insulation_dia_max=1.20,     # 1.1 +/- 0.10 mm
    jacket_dia=4.1, jacket_tolerance=0.2,
)

CABLES = (TRIGGER, SERIAL)

# How much bigger than the wire a hole must be, on diameter, at the hole's smallest.
STRAIN_HOLE_CLEARANCE = 0.2     # the insulated wire has to thread through by hand
SOLDER_HOLE_CLEARANCE = 0.15    # room for solder to flow round the conductor

# JLCPCB's hole tolerances: an unplated hole may be 0.05 mm small, a plated one 0.08 mm.
UNPLATED_HOLE_UNDERSIZE = 0.05
PLATED_HOLE_UNDERSIZE = 0.08


def fits_strain_hole(cable: Cable, drill: float) -> bool:
    return drill - UNPLATED_HOLE_UNDERSIZE - cable.insulation_dia_max >= STRAIN_HOLE_CLEARANCE


def fits_solder_hole(cable: Cable, drill: float) -> bool:
    return drill - PLATED_HOLE_UNDERSIZE - cable.conductor_dia_max >= SOLDER_HOLE_CLEARANCE
