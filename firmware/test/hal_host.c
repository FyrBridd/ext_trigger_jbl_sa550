#include "hal_host.h"

#include <string.h>

#include "app.h"
#include "hal.h"

sim_amp_t amp;

static uint32_t now_ms;
static uint8_t rx[256];             /* bytes waiting for the dongle to read */
static uint16_t rx_head, rx_tail;
static bool led;
static bool led_history[1000];      /* LED state at each of the last 1000 ms */
static uint8_t eeprom[128];
static uint32_t trace_count;

void host_reset(void)
{
    now_ms = 0;
    rx_head = rx_tail = 0;
    led = false;
    memset(led_history, 0, sizeof led_history);
    trace_count = 0;
    sim_amp_init(&amp);
}

void host_run_ms(uint32_t ms)
{
    for (uint32_t i = 0; i < ms; i++) {
        now_ms++;
        sim_amp_tick(&amp, now_ms);
        uint8_t byte;
        while (sim_amp_tx_byte(&amp, &byte)) {
            rx[rx_tail] = byte;
            rx_tail = (uint16_t)((rx_tail + 1) % sizeof rx);
        }
        app_step();
        led_history[now_ms % 1000] = led;
    }
}

bool host_led_is_on(void)
{
    return led;
}

ctrl_led_t host_led_mode(void)
{
    int on = 0, changes = 0;
    for (int i = 0; i < 1000; i++) {
        /* walk the last second in time order */
        bool a = led_history[(now_ms + 1 + (uint32_t)i) % 1000];
        bool b = led_history[(now_ms + 2 + (uint32_t)i) % 1000];
        on += a;
        if (i < 999 && a != b) {
            changes++;
        }
    }
    if (on == 1000) {
        return LED_SOLID;
    }
    return changes >= 6 ? LED_FAST : LED_SLOW;   /* fast: a period under 300 ms */
}

uint8_t *host_eeprom(void)
{
    return eeprom;
}

uint32_t host_trace_count(void)
{
    return trace_count;
}

/* --- the hal.h interface --- */

void hal_init(void) {}

uint16_t hal_millis(void)
{
    return (uint16_t)now_ms;
}

bool hal_uart_getc(uint8_t *b)
{
    if (rx_head == rx_tail) {
        return false;
    }
    *b = rx[rx_head];
    rx_head = (uint16_t)((rx_head + 1) % sizeof rx);
    return true;
}

void hal_uart_write(const uint8_t *buf, uint8_t n)
{
    for (uint8_t i = 0; i < n; i++) {
        sim_amp_rx_byte(&amp, buf[i]);
    }
}

void hal_led(bool on)
{
    led = on;
}

void hal_wdt_kick(void) {}

void hal_dbg_putc(uint8_t b)
{
    (void)b;
    trace_count++;
}

uint8_t hal_ee_read(uint8_t addr)
{
    return eeprom[addr & 0x7F];
}

void hal_ee_update(uint8_t addr, uint8_t v)
{
    eeprom[addr & 0x7F] = v;
}
