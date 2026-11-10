/* Entry point and fuse settings for the ATtiny412. */
#include <avr/interrupt.h>
#include <avr/io.h>

#include "app.h"
#include "hal.h"

/* Fuses travel in the hex file at address 0x820000. They are explained in
 * firmware/FUSES.md and checked on every build by tools/check_fuses.py.
 * NEVER change SYSCFG0 bits 3:2: anything but UPDI there locks the programmer out. */
FUSES = {
    .WDTCFG = 0x0A,                                   /* watchdog always on, 4 s */
    .BODCFG = LVL_BODLEVEL2_gc | ACTIVE_ENABLED_gc,   /* brown-out detector on while running, 2.6 V */
    .OSCCFG = FREQSEL_20MHZ_gc,                       /* 20 MHz oscillator (default) */
    .TCD0CFG = 0x00,                                  /* default */
    .SYSCFG0 = 0xF6,                                  /* default: no CRC check, PA0 = UPDI, EEPROM erased with chip erase */
    .SYSCFG1 = SUT_64MS_gc,                           /* default start-up time */
    .APPEND = 0x00,                                   /* default */
    .BOOTEND = 0x00,                                  /* default */
};

int main(void)
{
    hal_init();
    sei();
    app_init();
    for (;;) {
        app_step();
    }
}
