# Everything runs inside the dev container; see tools/dev.
DEV := tools/dev
PY  := $(DEV) python -W ignore -m

.PHONY: env-test hw hw-test route stock
env-test:
	$(DEV) pytest tools/tests -q

# Regenerate footprints, schematic, board and fabrication files, in that order.
hw:
	$(PY) hardware.design.gen_footprints
	$(PY) hardware.design.export_fab

hw-test:
	$(DEV) pytest hardware/tests -q

# Re-run the autorouter. Only after changing the circuit, placement or hand-routed tracks.
route:
	tools/route

# Check every part on the bill of materials is in stock at JLCPCB. Run on the day of ordering.
stock:
	$(DEV) python tools/jlc_stock.py --bom hardware/fab/bom.csv --report hardware/fab/stock-report.md

# Firmware: host tests (no hardware), and the ATtiny412 builds into firmware/release/.
.PHONY: fw-test fw
fw-test:
	$(DEV) make -C firmware test
	$(DEV) pytest tools/tests -q

fw:
	$(DEV) make -C firmware avr
