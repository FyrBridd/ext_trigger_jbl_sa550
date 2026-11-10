#include "test.h"
#include "proto.h"
#include "ctrl.h"
#include "config.h"

static ctrl_t c;
static uint16_t t;

static proto_frame_t fr(uint8_t cmd, uint8_t answer, uint8_t d0)
{
    proto_frame_t f = { .zone = 1, .cmd = cmd, .answer = answer, .len = 1, .data = { d0 } };
    return f;
}

/* the amp sends a frame */
static void rx(uint8_t cmd, uint8_t answer, uint8_t d0)
{
    proto_frame_t f = fr(cmd, answer, d0);
    ctrl_on_frame(&c, &f, t);
}

static ctrl_send_t step(void)
{
    return ctrl_step(&c, t);
}

/* advance 1 ms at a time until a command comes out or ms have passed; returns it (or SEND_NONE) */
static ctrl_send_t run(uint16_t ms)
{
    for (uint16_t i = 0; i < ms; i++) {
        ctrl_send_t s = step();
        if (s) {
            return s;
        }
        t++;
    }
    return step();
}

static void start(uint16_t t0)
{
    t = t0;
    ctrl_init(&c, t);
}

static void test_noquery_selects_once_after_wake(void) {
  start(0); run(STARTUP_MS); rx(0x00, 0, 1);
  CHECK_EQ(run(SETTLE_MS + 5), SEND_SELECT_STB); CHECK_EQ(ctrl_led(&c), LED_SOLID);
  CHECK_EQ(run(POLL_MS + 5), SEND_POWER_QUERY); rx(0x00, 0, 1);
  CHECK_EQ(run(POLL_MS - 5), SEND_NONE);                 /* already on: nothing more */
}
static void test_noquery_reselects_after_unsolicited_wrong_input(void) {
  start(0); run(STARTUP_MS); rx(0x00, 0, 1); run(SETTLE_MS + 5);
  t += 100; rx(0x1D, 0, 0x06); CHECK_EQ(step(), SEND_POWER_QUERY); rx(0x00, 0, 1); CHECK_EQ(step(), SEND_SELECT_STB);
}

int main(void)
{
    RUN(test_noquery_selects_once_after_wake);
    RUN(test_noquery_reselects_after_unsolicited_wrong_input);
    TEST_MAIN_END();
}
