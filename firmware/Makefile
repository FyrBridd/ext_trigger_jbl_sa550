# Firmware build. Run through the dev container:  tools/dev make -C firmware <target>
#
#   test   build and run every host test (no hardware needed)
#   avr    build every firmware variant for the ATtiny412 (added in a later task)

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

$(HOST):
	mkdir -p $@

test: $(HOST_TESTS)
	@set -e; for t in $(HOST_TESTS); do echo "== $$t"; ./$$t; done

clean:
	rm -rf build
