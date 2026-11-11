import shutil
import subprocess


def run(*a):
    return subprocess.run(a, capture_output=True, text=True, check=True).stdout


def test_kicad_cli_is_10():
    assert run("kicad-cli", "version").strip().startswith("10.0.")


def test_python_modules():
    import importlib.metadata

    import kicad_sch_api  # noqa: F401  (must import cleanly)
    import pcbnew

    assert pcbnew.Version().startswith("10.0.")
    # the package's own __version__ attribute is stale (says 0.5.1); ask the installer
    assert importlib.metadata.version("kicad-sch-api") == "0.5.5"


def test_avr_gcc_knows_attiny412(tmp_path):
    src = tmp_path / "m.c"
    src.write_text("#include <avr/io.h>\nint main(void){PORTA.DIRSET=PIN3_bm;for(;;){}}\n")
    run("avr-gcc", "-mmcu=attiny412", "-Os", "-o", str(tmp_path / "m.elf"), str(src))


def test_host_gcc_and_make():
    assert shutil.which("gcc") and shutil.which("make")


def test_cadquery_builds_a_solid():
    import importlib.metadata

    import cadquery as cq

    assert importlib.metadata.version("cadquery") == "2.8.0"
    assert abs(cq.Workplane("XY").box(1, 2, 3).val().Volume() - 6.0) < 1e-9


def test_drawing_tools_present():
    import matplotlib  # noqa: F401

    assert shutil.which("rsvg-convert") and shutil.which("pdfinfo")
