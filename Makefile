# Everything runs inside the dev container; see tools/dev.
DEV := tools/dev

.PHONY: env-test hw-test
env-test:
	$(DEV) pytest tools/tests -q

hw-test:
	$(DEV) pytest hardware/tests -q
