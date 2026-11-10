import pathlib, subprocess
from tools import decode_eeprom as d

GOLD = pathlib.Path("firmware/build/host/dbglog_golden.bin")

def setup_module():
    subprocess.run(["make", "-C", "firmware", "test"], check=True, capture_output=True)

def test_decodes_golden_log():
    log = d.decode(GOLD.read_bytes())
    assert log["boots"] == 1
    assert log["power_query"] == {"timeouts": 1, "records": []}
    assert log["power_on"]["records"] == [{"cmd": 0x00, "answer": 0x00, "data": [0x01]}]
    assert log["input_query"]["records"] == [{"cmd": 0x1D, "answer": 0x00, "data": [0x15]}]
    assert log["unsolicited"]["records"] == [{"cmd": 0x1D, "answer": 0x00, "data": [0x06]}]
    assert log["select_stb"]["records"] == [{"cmd": 0x1D, "answer": 0x85, "data": []}]

def test_blank_eeprom_is_reported_not_decoded():
    assert d.decode(bytes([0xFF]) * 128) == {"error": "no log found (EEPROM blank or not a debug build)"}

def test_intel_hex_at_microchip_offset(tmp_path):
    raw = GOLD.read_bytes()
    assert d.load(d.to_ihex(raw, base=0x810000, path=tmp_path / "e.hex")) == raw

def test_text_names_error_answers():
    assert "0x85 (command invalid at this time)" in d.render(d.decode(GOLD.read_bytes()))
