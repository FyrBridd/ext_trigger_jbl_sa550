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

/* bring the controller to steady state: on, STB, next poll pending */
static void steady(uint16_t t0)
{
    start(t0);
    CHECK_EQ(run(STARTUP_MS), SEND_POWER_QUERY);
    rx(0x00, 0, 1);
    CHECK_EQ(run(SETTLE_MS), SEND_INPUT_QUERY);
    rx(0x1D, 0, 0x15);
    CHECK_EQ(ctrl_led(&c), LED_SOLID);
}

static void test_startup_delay(void) {
  start(0); t = STARTUP_MS - 1; CHECK_EQ(step(), SEND_NONE); t = STARTUP_MS; CHECK_EQ(step(), SEND_POWER_QUERY);
  CHECK_EQ(ctrl_led(&c), LED_SLOW);
}
static void test_standby_then_power_on_then_requery(void) {
  start(0); run(STARTUP_MS); rx(0x00, 0, 0);
  CHECK_EQ(step(), SEND_POWER_ON); CHECK_EQ(step(), SEND_NONE);
  uint16_t t0 = t; CHECK_EQ(run(WAKE_POLL_MS + 5), SEND_POWER_QUERY); CHECK_EQ(t - t0, WAKE_POLL_MS);
  CHECK_EQ(ctrl_led(&c), LED_SLOW);
}
static void test_timeout_sends_power_on_and_blinks_fast(void) {
  /* while the amp is not known to be on, silence is acted on after the short timeout */
  start(0); run(STARTUP_MS); uint16_t t0 = t;
  CHECK_EQ(run(WAKE_REPLY_TIMEOUT_MS + 5), SEND_POWER_ON); CHECK_EQ(t - t0, WAKE_REPLY_TIMEOUT_MS);
  CHECK_EQ(ctrl_led(&c), LED_FAST);
  rx(0x00, 0, 0); CHECK_EQ(ctrl_led(&c), LED_SLOW);       /* any valid frame clears "not answering" */
}
static void test_power_error_answer_counts_as_not_on(void) {
  start(0); run(STARTUP_MS); rx(0x00, 0x85, 0); CHECK_EQ(step(), SEND_POWER_ON); CHECK_EQ(ctrl_led(&c), LED_SLOW);
}
static void test_settle_only_on_first_on(void) {
  start(0); run(STARTUP_MS); rx(0x00, 0, 1); uint16_t t0 = t;
  CHECK_EQ(run(SETTLE_MS + 5), SEND_INPUT_QUERY); CHECK_EQ(t - t0, SETTLE_MS);
  rx(0x1D, 0, 0x05); t0 = t;
  CHECK_EQ(run(POLL_MS + 5), SEND_POWER_QUERY); CHECK_EQ(t - t0, POLL_MS);
  rx(0x00, 0, 1); CHECK_EQ(step(), SEND_INPUT_QUERY);     /* already on: no settle */
}
static void test_processor_mode_reply_is_stb(void) { steady(0); CHECK_EQ(step(), SEND_NONE); }
static void test_wrong_input_selects_stb(void) {
  start(0); run(STARTUP_MS); rx(0x00, 0, 1); run(SETTLE_MS); rx(0x1D, 0, 0x06);
  CHECK_EQ(step(), SEND_SELECT_STB); CHECK_EQ(ctrl_led(&c), LED_SLOW);
  uint16_t t0 = t; CHECK_EQ(run(WAKE_POLL_MS + 5), SEND_POWER_QUERY); CHECK_EQ(t - t0, WAKE_POLL_MS);
}
static void test_input_error_or_timeout_never_selects_blind(void) {
  start(0); run(STARTUP_MS); rx(0x00, 0, 1); run(SETTLE_MS); rx(0x1D, 0x85, 0);
  uint16_t t0 = t; CHECK_EQ(run(WAKE_POLL_MS + 5), SEND_POWER_QUERY); CHECK_EQ(t - t0, WAKE_POLL_MS);
  rx(0x00, 0, 1); CHECK_EQ(step(), SEND_INPUT_QUERY);
  t0 = t; CHECK_EQ(run(REPLY_TIMEOUT_MS + WAKE_POLL_MS + 5), SEND_POWER_QUERY);   /* timeout path */
  CHECK_EQ(t - t0, REPLY_TIMEOUT_MS + WAKE_POLL_MS);
}
static void test_unsolicited_wrong_input_triggers_recheck(void) {
  steady(0); t += 100; rx(0x1D, 0, 0x06); CHECK_EQ(step(), SEND_POWER_QUERY); CHECK_EQ(ctrl_led(&c), LED_SLOW);
}
static void test_unsolicited_standby_triggers_recheck(void) {
  steady(0); t += 100; rx(0x00, 0, 0); CHECK_EQ(step(), SEND_POWER_QUERY);
}
static void test_unsolicited_good_state_changes_nothing(void) {
  steady(0); t += 100; rx(0x1D, 0, 0x15); rx(0x00, 0, 1); CHECK_EQ(step(), SEND_NONE); CHECK_EQ(ctrl_led(&c), LED_SOLID);
}
static void test_unsolicited_frame_while_awaiting(void) {
  steady(0); CHECK_EQ(run(POLL_MS + 5), SEND_POWER_QUERY);
  rx(0x1D, 0, 0x06);                       /* front panel change lands before the power reply */
  CHECK_EQ(step(), SEND_NONE);             /* still awaiting the power reply */
  rx(0x00, 0, 1); CHECK_EQ(step(), SEND_INPUT_QUERY);
  rx(0x1D, 0, 0x06); CHECK_EQ(step(), SEND_SELECT_STB);
}
static void test_wraparound(void) {
  steady(65000);                           /* startup, settle and first poll all straddle the wrap */
  uint16_t t0 = t; CHECK_EQ(run(POLL_MS + 5), SEND_POWER_QUERY); CHECK_EQ((uint16_t)(t - t0), POLL_MS);
  t0 = t; CHECK_EQ(run(REPLY_TIMEOUT_MS + 5), SEND_POWER_ON); CHECK_EQ((uint16_t)(t - t0), REPLY_TIMEOUT_MS);
}
/* --- found by the whole-branch review --- */

static void test_ack_of_power_on_does_not_cause_a_storm(void) {
  /* an amp that answers our power-on with its current state (still standby) must
     not make us ask and command again at once */
  start(0); run(STARTUP_MS); rx(0x00, 0, 0);
  CHECK_EQ(step(), SEND_POWER_ON); uint16_t t0 = t;
  t += 20; rx(0x00, 0, 0);                                 /* the acknowledgement: "standby" */
  CHECK_EQ(step(), SEND_NONE);
  CHECK_EQ(run(WAKE_POLL_MS + 5), SEND_POWER_QUERY); CHECK_EQ(t - t0, WAKE_POLL_MS);
}
static void test_ack_of_select_showing_wrong_input_does_not_cause_a_storm(void) {
  start(0); run(STARTUP_MS); rx(0x00, 0, 1); run(SETTLE_MS); rx(0x1D, 0, 0x06);
  CHECK_EQ(step(), SEND_SELECT_STB); uint16_t t0 = t;
  t += 20; rx(0x1D, 0, 0x06);                              /* acknowledged, but the input did not change */
  CHECK_EQ(step(), SEND_NONE);
  CHECK_EQ(run(WAKE_POLL_MS + 5), SEND_POWER_QUERY); CHECK_EQ(t - t0, WAKE_POLL_MS);
}
static void test_on_frame_while_waking_confirms_on(void) {
  /* a late reply, or the amp's own "now on" report, moves us on to the input stage */
  start(0); run(STARTUP_MS); CHECK_EQ(run(WAKE_REPLY_TIMEOUT_MS + 5), SEND_POWER_ON);
  t += 100; rx(0x00, 0, 1); uint16_t t0 = t;
  CHECK_EQ(run(SETTLE_MS + 5), SEND_INPUT_QUERY); CHECK_EQ(t - t0, SETTLE_MS);
}
static void test_steady_state_allows_the_amp_three_seconds(void) {
  /* the protocol gives the amp 3 s to answer; once it is on we wait that long */
  steady(0); CHECK_EQ(run(POLL_MS + 5), SEND_POWER_QUERY);
  CHECK_EQ(run(2900), SEND_NONE);                          /* no power-on while the reply may still come */
  rx(0x00, 0, 1); CHECK_EQ(step(), SEND_INPUT_QUERY);
  CHECK_EQ(run(2900), SEND_NONE);
  rx(0x1D, 0, 0x15); CHECK_EQ(ctrl_led(&c), LED_SOLID);
}

int main(void)
{
    RUN(test_startup_delay);
    RUN(test_standby_then_power_on_then_requery);
    RUN(test_timeout_sends_power_on_and_blinks_fast);
    RUN(test_power_error_answer_counts_as_not_on);
    RUN(test_settle_only_on_first_on);
    RUN(test_processor_mode_reply_is_stb);
    RUN(test_wrong_input_selects_stb);
    RUN(test_input_error_or_timeout_never_selects_blind);
    RUN(test_unsolicited_wrong_input_triggers_recheck);
    RUN(test_unsolicited_standby_triggers_recheck);
    RUN(test_unsolicited_good_state_changes_nothing);
    RUN(test_unsolicited_frame_while_awaiting);
    RUN(test_wraparound);
    RUN(test_ack_of_power_on_does_not_cause_a_storm);
    RUN(test_ack_of_select_showing_wrong_input_does_not_cause_a_storm);
    RUN(test_on_frame_while_waking_confirms_on);
    RUN(test_steady_state_allows_the_amp_three_seconds);
    TEST_MAIN_END();
}
