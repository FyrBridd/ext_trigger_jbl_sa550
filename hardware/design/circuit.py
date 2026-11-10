"""The dongle's circuit: parts and nets. This file is the single source of truth.

The schematic and the board are generated from it; tests compare both back to it.
Pin numbers are package pin numbers. See the design document, sections 5 and 6.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Part:
    ref: str
    value: str
    symbol: str      # KiCad library symbol, "Library:Name"
    footprint: str   # KiCad footprint, "Library:Name"
    lcsc: str | None  # JLCPCB part number; None for things JLCPCB does not fit
    assemble: bool


R0603 = "Resistor_SMD:R_0603_1608Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
TESTPAD = "TestPoint:TestPoint_Pad_D1.0mm"

# What each test pad is for; also its silkscreen label.
TEST_PADS = {
    "TP1": "VIN", "TP2": "3V3", "TP3": "GND", "TP4": "TXL",
    "TP5": "RXL", "TP6": "UPDI", "TP7": "PA1", "TP8": "PA2",
}

_parts = [
    Part("U1", "HT7533-1", "Regulator_Linear:HT75xx-1-SOT89", "Package_TO_SOT_SMD:SOT-89-3", "C14289", True),
    Part("U2", "ATtiny412-SSNR", "MCU_Microchip_ATtiny:ATtiny412-SS", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "C1337190", True),
    Part("U3", "SP3232EEY", "Interface_UART:MAX3232", "Package_SO:TSSOP-16_4.4x5mm_P0.65mm", "C13482", True),
    Part("D1", "B5819W", "Device:D_Schottky", "Diode_SMD:D_SOD-123", "C8598", True),
    Part("D2", "SMF15CA", "Device:D_TVS", "Diode_SMD:D_SOD-123F", "C19077510", True),
    Part("D3", "RED", "Device:LED", "LED_SMD:LED_0603_1608Metric", "C2286", True),
    Part("C1", "10u 25V", "Device:C", C0805, "C15850", True),
    Part("C2", "10u 25V", "Device:C", C0805, "C15850", True),
    *[Part(f"C{i}", "100n 50V", "Device:C", C0603, "C14663", True) for i in range(3, 9)],
    Part("R1", "100R", "Device:R", R0603, "C22775", True),
    Part("R2", "1k", "Device:R", R0603, "C21190", True),
    Part("R3", "10k", "Device:R", R0603, "C25804", True),
    Part("J1", "TRIGGER", "Connector_Generic:Conn_01x02", "dongle:WirePads_1x02_Strain", None, False),
    Part("J2", "RS232", "Connector_Generic:Conn_01x03", "dongle:WirePads_1x03_Strain", None, False),
    Part("J3", "TC2030", "Connector_Generic:Conn_01x06", "dongle:TC2030-MCP-NL", None, False),
    *[Part(ref, label, "Connector:TestPoint", TESTPAD, None, False) for ref, label in TEST_PADS.items()],
]
PARTS: dict[str, Part] = {p.ref: p for p in _parts}

NETS: dict[str, list[tuple[str, str]]] = {
    # Trigger input and 3.3 V supply
    "TRIG_IN": [("J1", "1"), ("R1", "1")],
    "TRIG_R": [("R1", "2"), ("D2", "1"), ("D1", "2")],            # D1.2 is the anode
    "VIN": [("D1", "1"), ("C1", "1"), ("U1", "2"), ("TP1", "1")],  # D1.1 is the cathode
    "+3V3": [("U1", "3"), ("C2", "1"), ("C3", "1"), ("U2", "1"), ("U3", "16"),
             ("C8", "1"), ("R3", "1"), ("J3", "2"), ("TP2", "1")],
    "GND": [("J1", "2"), ("D2", "2"), ("C1", "2"), ("U1", "1"), ("C2", "2"), ("C3", "2"),
            ("U2", "8"), ("U3", "15"), ("U3", "10"), ("C8", "2"), ("C6", "2"), ("C7", "1"),
            ("D3", "1"), ("J2", "3"), ("J3", "3"), ("TP3", "1")],  # D3.1 is the cathode
    # Controller to serial driver (logic level)
    "UART_TX": [("U2", "2"), ("U3", "11"), ("R3", "2"), ("TP4", "1")],
    "UART_RX": [("U2", "3"), ("U3", "12"), ("TP5", "1")],
    # RS232 side, to the amplifier
    "RS232_TX": [("U3", "14"), ("J2", "1")],
    "RS232_RX": [("U3", "13"), ("J2", "2")],
    # Programming, debug and spare
    "UPDI": [("U2", "6"), ("J3", "4"), ("TP6", "1")],
    "DBG": [("U2", "4"), ("TP7", "1")],
    "SPARE": [("U2", "5"), ("TP8", "1")],
    # Status LED
    "LED_DRV": [("U2", "7"), ("R2", "1")],
    "LED_A": [("R2", "2"), ("D3", "2")],                           # D3.2 is the anode
    # Serial driver charge pump
    "C1P": [("U3", "1"), ("C4", "1")],
    "C1M": [("U3", "3"), ("C4", "2")],
    "C2P": [("U3", "4"), ("C5", "1")],
    "C2M": [("U3", "5"), ("C5", "2")],
    "VPOS": [("U3", "2"), ("C6", "1")],
    "VNEG": [("U3", "6"), ("C7", "2")],
}

# Pins deliberately left unconnected.
NO_CONNECT: list[tuple[str, str]] = [
    ("U3", "7"), ("U3", "8"), ("U3", "9"),   # unused second RS232 channel
    ("J3", "1"), ("J3", "5"), ("J3", "6"),   # programming cable MCLR/VPP, PGC, AUX
]

# Datasheet function of every IC pin, for review against the datasheets.
PIN_FUNCTIONS: dict[tuple[str, str], str] = {
    ("U1", "1"): "GND", ("U1", "2"): "VIN", ("U1", "3"): "VOUT",
    ("U2", "1"): "VDD", ("U2", "2"): "PA6/TXD", ("U2", "3"): "PA7/RXD", ("U2", "4"): "PA1",
    ("U2", "5"): "PA2", ("U2", "6"): "PA0/UPDI", ("U2", "7"): "PA3", ("U2", "8"): "GND",
    ("U3", "1"): "C1+", ("U3", "2"): "V+", ("U3", "3"): "C1-", ("U3", "4"): "C2+",
    ("U3", "5"): "C2-", ("U3", "6"): "V-", ("U3", "7"): "T2OUT", ("U3", "8"): "R2IN",
    ("U3", "9"): "R2OUT", ("U3", "10"): "T2IN", ("U3", "11"): "T1IN", ("U3", "12"): "R1OUT",
    ("U3", "13"): "R1IN", ("U3", "14"): "T1OUT", ("U3", "15"): "GND", ("U3", "16"): "VCC",
}
