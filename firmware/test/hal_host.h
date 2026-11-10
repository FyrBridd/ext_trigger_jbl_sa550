/* Fake hardware for host tests: a virtual clock, byte pipes to the simulated
 * amp, a recorded LED and a fake EEPROM. */
#ifndef HAL_HOST_H
#define HAL_HOST_H

#include <stdbool.h>
#include <stdint.h>

#include "ctrl.h"
#include "sim_amp.h"

extern sim_amp_t amp;

void host_reset(void);              /* time zero, amp back to its defaults */
void host_run_ms(uint32_t ms);      /* advance the clock, calling app_step() every millisecond */
bool host_led_is_on(void);
ctrl_led_t host_led_mode(void);     /* what the LED has been doing over the last second */
uint8_t *host_eeprom(void);         /* 128 bytes */
uint32_t host_trace_count(void);    /* debug trace bytes emitted so far */

#endif
