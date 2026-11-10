/* What the application needs from the hardware. Implemented by hal_avr.c for
 * the ATtiny412 and by test/hal_host.c for tests on the host. */
#ifndef HAL_H
#define HAL_H

#include <stdbool.h>
#include <stdint.h>

void hal_init(void);

/* Free-running millisecond counter; wraps every 65.5 s. */
uint16_t hal_millis(void);

/* One received byte, if any is waiting. */
bool hal_uart_getc(uint8_t *b);

void hal_uart_write(const uint8_t *buf, uint8_t n);

void hal_led(bool on);

void hal_wdt_kick(void);

/* Debug builds (CFG_DEBUG) only. */
void hal_dbg_putc(uint8_t b);                  /* one byte out of the debug trace pin */
uint8_t hal_ee_read(uint8_t addr);
void hal_ee_update(uint8_t addr, uint8_t v);   /* writes only if the value differs */

#endif
