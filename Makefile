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
