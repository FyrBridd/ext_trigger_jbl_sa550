# Firmware build. Run through the dev container:  tools/dev make -C firmware <target>
#
#   test   build and run every host test (no hardware needed)
#   avr    build every firmware variant for the ATtiny412 into release/, with size and fuse checks

CFLAGS_COMMON := -std=c11 -Wall -Wextra -Werror
HOST_CC := gcc
HOST_CFLAGS := $(CFLAGS_COMMON) -O1 -g -Isrc -Itest
HOST := build/host

.PHONY: test clean
.DEFAULT_GOAL := test

# host test binaries: name, sources, extra flags
# $(call host_test,<binary name>,<source files>,<extra flags>)
define host_test
$(HOST)/$(1): $(2) $(wildcard src/*.h test/*.h) | $(HOST)
	$(HOST_CC) $(HOST_CFLAGS) $(3) -o $$@ $(2)
HOST_TESTS += $(HOST)/$(1)
endef

$(eval $(call host_test,test_proto,test/test_proto.c src/proto.c,))
$(eval $(call host_test,test_cmds,test/test_cmds.c src/cmds.c src/proto.c,))
$(eval $(call host_test,test_ctrl,test/test_ctrl.c src/ctrl.c,))
$(eval $(call host_test,test_ctrl_noquery,test/test_ctrl_noquery.c src/ctrl.c,-DCFG_INPUT_QUERY=0))
APP_SRC := test/sim_amp.c test/hal_host.c src/app.c src/ctrl.c src/cmds.c src/proto.c
$(eval $(call host_test,test_app,test/test_app.c $(APP_SRC),))
$(eval $(call host_test,test_app_rc5,test/test_app.c $(APP_SRC),-DCFG_POWER_RC5=1 -DCFG_INPUT_RC5=1))
$(eval $(call host_test,test_dbglog,test/test_dbglog.c src/dbglog.c $(APP_SRC),-DCFG_DEBUG=1))
$(eval $(call host_test,test_app_debug,test/test_app.c src/dbglog.c $(APP_SRC),-DCFG_DEBUG=1))
$(eval $(call host_test,test_cmds_rc5,test/test_cmds.c src/cmds.c src/proto.c,-DCFG_POWER_RC5=1 -DCFG_INPUT_RC5=1))

$(HOST):
	mkdir -p $@

test: $(HOST_TESTS)
	@set -e; for t in $(HOST_TESTS); do echo "== $$t"; ./$$t; done

# --- firmware for the ATtiny412 -------------------------------------------------
#
# Variants: release/dongle-p{d|r}-i{d|r}-q{1|0}[-dbg].hex
#   p  power-on command: d direct, r simulated remote-control code
#   i  select-STB command: d direct, r simulated remote-control code
#   q  1 query the input before selecting, 0 never query it
#   -dbg  debug build: live trace on PA1 and a reply log in the EEPROM

AVR_CC := avr-gcc
AVR_CFLAGS := $(CFLAGS_COMMON) -mmcu=attiny412 -Os -flto -ffunction-sections -fdata-sections \
              -Wl,--gc-sections -DF_CPU=3333333UL -Isrc
AVR_SRC := src/main.c src/hal_avr.c src/app.c src/ctrl.c src/cmds.c src/proto.c src/dbglog.c
AVR := build/avr
REL := release

# $(call avr_variant,<name>,<flags>)
define avr_variant
$(AVR)/$(1).elf: $(AVR_SRC) $(wildcard src/*.h) | $(AVR)
	$(AVR_CC) $(AVR_CFLAGS) $(2) -o $$@ $(AVR_SRC)
$(REL)/$(1).hex: $(AVR)/$(1).elf | $(REL)
	avr-objcopy -O ihex -R .eeprom -R .lock -R .signature -R .user_signatures $$< $$@
AVR_ELFS += $(AVR)/$(1).elf
AVR_HEXES += $(REL)/$(1).hex
endef

$(foreach p,d r,$(foreach i,d r,$(foreach q,1 0,\
  $(eval $(call avr_variant,dongle-p$(p)-i$(i)-q$(q),-DCFG_POWER_RC5=$(if $(filter r,$(p)),1,0) -DCFG_INPUT_RC5=$(if $(filter r,$(i)),1,0) -DCFG_INPUT_QUERY=$(q)))\
  $(eval $(call avr_variant,dongle-p$(p)-i$(i)-q$(q)-dbg,-DCFG_POWER_RC5=$(if $(filter r,$(p)),1,0) -DCFG_INPUT_RC5=$(if $(filter r,$(i)),1,0) -DCFG_INPUT_QUERY=$(q) -DCFG_DEBUG=1)))))

$(AVR) $(REL):
	mkdir -p $@

.PHONY: avr
avr: $(AVR_HEXES)
	python ../tools/fw_sizes.py --out $(REL)/SIZES.md $(AVR_ELFS)
	python ../tools/check_fuses.py $(AVR_HEXES)
	@echo "built $(words $(AVR_HEXES)) firmware files into $(REL)/"

clean:
	rm -rf build
