#include "app.h"

#include "cmds.h"
#include "config.h"
#include "ctrl.h"
#if CFG_DEBUG
#include "dbglog.h"
#endif
#include "hal.h"
#include "proto.h"

/* Debug trace: a command we send is announced as this marker and then its
 * ctrl_send_t value; every byte received from the amp is copied as it is. */
#define TRACE_SENT_MARKER 0xFE

static proto_parser_t parser;
static ctrl_t ctrl;
static uint16_t last_rx;

void app_init(void)
{
    uint16_t now = hal_millis();
    proto_parser_init(&parser);
    ctrl_init(&ctrl, now);
    last_rx = now;
#if CFG_DEBUG
    dbglog_init();
#endif
}

static void show(ctrl_led_t mode, uint16_t now)
{
    /* Blink periods are powers of two (1.02 s and 0.26 s) so they need no
     * division and stay regular when the 16-bit counter wraps. */
    switch (mode) {
    case LED_SOLID:
        hal_led(true);
        break;
    case LED_SLOW:
        hal_led((now & 0x200) == 0);
        break;
    case LED_FAST:
    default:
        hal_led((now & 0x080) == 0);
        break;
    }
}

void app_step(void)
{
    hal_wdt_kick();
    uint16_t now = hal_millis();

    uint8_t byte;
    proto_frame_t frame;
    while (hal_uart_getc(&byte)) {
        last_rx = now;
#if CFG_DEBUG
        hal_dbg_putc(byte);
#endif
        if (proto_parser_feed(&parser, byte, &frame)) {
#if CFG_DEBUG
            dbglog_frame(&frame);
#endif
            ctrl_on_frame(&ctrl, &frame, now);
        }
    }
    /* a frame that stops arriving half-way must not swallow the next one */
    if (proto_parser_busy(&parser) && (uint16_t)(now - last_rx) >= PARSER_GAP_MS) {
        proto_parser_init(&parser);
    }

    ctrl_send_t what = ctrl_step(&ctrl, now);
    if (what != SEND_NONE) {
        uint8_t buf[CMDS_MAX_LEN];
        uint8_t n = cmds_build(what, buf);
#if CFG_DEBUG
        hal_dbg_putc(TRACE_SENT_MARKER);
        hal_dbg_putc((uint8_t)what);
        dbglog_sent(what);
#endif
        hal_uart_write(buf, n);
    }

    show(ctrl_led(&ctrl), now);
}
