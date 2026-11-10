from tools import check_fuses as cf

GOOD = bytes([0x0A, 0x44, 0x02, 0xFF, 0x00, 0xF6, 0x07, 0x00, 0x00])

def hexfile(tmp_path, fuses, base=0x820000):
    p = tmp_path / "f.hex"; cf.write_test_hex(p, {0x0000: bytes(16), base: fuses}); return p

def test_good_fuses_pass(tmp_path):
    assert cf.check(hexfile(tmp_path, GOOD)) == []

def test_updi_disabled_is_rejected(tmp_path):
    bad = bytearray(GOOD); bad[5] = 0xF2            # RSTPINCFG = GPIO
    assert any("UPDI" in e for e in cf.check(hexfile(tmp_path, bytes(bad))))

def test_wrong_watchdog_or_brownout_rejected(tmp_path):
    bad = bytearray(GOOD); bad[0] = 0x00; bad[1] = 0x00
    errs = cf.check(hexfile(tmp_path, bytes(bad)))
    assert any("WDTCFG" in e for e in errs) and any("BODCFG" in e for e in errs)

def test_missing_fuse_records_rejected(tmp_path):
    p = tmp_path / "n.hex"; cf.write_test_hex(p, {0x0000: bytes(16)})
    assert cf.check(p) == ["no fuse records at 0x820000"]
