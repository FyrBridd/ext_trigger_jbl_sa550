/* Controller state machine. See ctrl.h, and section 7.1 of the design document.
 *
 * One cycle is: ask the power state; if not on, send power-on and try again
 * shortly; once on, ask the input; if not STB, select STB. In steady state the
 * cycle repeats every POLL_MS and sends nothing but the two queries. */
#include "ctrl.h"

#include "config.h"

enum { PH_WAIT, PH_AWAIT_POWER, PH_AWAIT_INPUT };
enum { UNKNOWN, NO, YES };   /* for power (on?) and input (is it STB?) */

static bool due(uint16_t now, uint16_t at)
{
    return (int16_t)(now - at) >= 0;   /* correct across the counter wrapping */
}

/* Send `what` once `delay` ms have passed. A pending recheck cuts short the
 * wait before the next cycle. */
static void schedule(ctrl_t *c, ctrl_send_t what, uint16_t now, uint16_t delay)
{
    if (what == SEND_POWER_QUERY && c->recheck) {
        delay = 0;
    }
    c->phase = PH_WAIT;
    c->next = what;
    c->at = now + delay;
}

/* A frame, not asked for, showed the amp in the wrong state. */
static void wrong_state_seen(ctrl_t *c, uint16_t now)
{
    c->recheck = true;
    if (c->phase == PH_WAIT && c->next == SEND_POWER_QUERY) {
        c->at = now;
    }
}

void ctrl_init(ctrl_t *c, uint16_t now)
{
    c->power = UNKNOWN;
    c->input = UNKNOWN;
    c->confirmed_on = false;
    c->answering = true;
    c->recheck = false;
    schedule(c, SEND_POWER_QUERY, now, STARTUP_MS);
}

/* The amp is confirmed on: what comes next? */
static void after_power_on_confirmed(ctrl_t *c, uint16_t now, bool first_time)
{
    uint16_t delay = first_time ? SETTLE_MS : 0;
#if CFG_INPUT_QUERY
    schedule(c, SEND_INPUT_QUERY, now, delay);
#else
    if (first_time || c->input == NO) {
        schedule(c, SEND_SELECT_STB, now, delay);
    } else {
        schedule(c, SEND_POWER_QUERY, now, POLL_MS);
    }
#endif
}

static void on_power_frame(ctrl_t *c, const proto_frame_t *f, uint16_t now)
{
    bool good = f->answer == PROTO_ANSWER_OK && f->len >= 1;
    bool on = good && f->data[0] == 0x01;

    if (c->phase == PH_AWAIT_POWER) {           /* the reply to our query */
        bool first_time = !c->confirmed_on;
        c->power = on ? YES : NO;
        c->confirmed_on = on;
        if (on) {
            after_power_on_confirmed(c, now, first_time);
        } else {
            schedule(c, SEND_POWER_ON, now, 0);
        }
        return;
    }
    if (good) {                                  /* not asked for: a status report */
        c->power = on ? YES : NO;
        if (!on) {
            c->confirmed_on = false;
            wrong_state_seen(c, now);
        }
    }
}

static void on_input_frame(ctrl_t *c, const proto_frame_t *f, uint16_t now)
{
    bool good = f->answer == PROTO_ANSWER_OK && f->len >= 1;
    /* the high nibble flags processor mode; only the low nibble is the input */
    bool right = good && (f->data[0] & 0x0F) == INPUT_STB;

    if (c->phase == PH_AWAIT_INPUT) {            /* the reply to our query */
        if (right) {
            c->input = YES;
            schedule(c, SEND_POWER_QUERY, now, POLL_MS);
        } else if (good) {
            c->input = NO;
            schedule(c, SEND_SELECT_STB, now, 0);
        } else {
            /* an error answer: never select blind, just look again shortly */
            c->input = UNKNOWN;
            schedule(c, SEND_POWER_QUERY, now, WAKE_POLL_MS);
        }
        return;
    }
    if (good) {                                  /* not asked for: a status report */
        c->input = right ? YES : NO;
        if (!right) {
            wrong_state_seen(c, now);
        }
    }
}

void ctrl_on_frame(ctrl_t *c, const proto_frame_t *f, uint16_t now)
{
    c->answering = true;
    if (f->cmd == PROTO_CMD_POWER) {
        on_power_frame(c, f, now);
    } else if (f->cmd == PROTO_CMD_INPUT) {
        on_input_frame(c, f, now);
    }
    /* frames for any other command do not end a wait */
}

ctrl_send_t ctrl_step(ctrl_t *c, uint16_t now)
{
    if (!due(now, c->at)) {
        return SEND_NONE;
    }

    if (c->phase == PH_AWAIT_POWER) {            /* no reply to the power query */
        c->answering = false;
        c->power = UNKNOWN;
        c->confirmed_on = false;
        schedule(c, SEND_POWER_ON, now, 0);      /* try waking it anyway */
    } else if (c->phase == PH_AWAIT_INPUT) {     /* no reply to the input query */
        c->input = UNKNOWN;
        schedule(c, SEND_POWER_QUERY, now, WAKE_POLL_MS);
        if (!due(now, c->at)) {
            return SEND_NONE;
        }
    }

    ctrl_send_t what = (ctrl_send_t)c->next;
    switch (what) {
    case SEND_POWER_QUERY:
        c->recheck = false;
        c->phase = PH_AWAIT_POWER;
        c->at = now + REPLY_TIMEOUT_MS;
        break;
    case SEND_INPUT_QUERY:
        c->recheck = false;
        c->phase = PH_AWAIT_INPUT;
        c->at = now + REPLY_TIMEOUT_MS;
        break;
    case SEND_POWER_ON:
        schedule(c, SEND_POWER_QUERY, now, WAKE_POLL_MS);
        break;
    case SEND_SELECT_STB:
#if CFG_INPUT_QUERY
        schedule(c, SEND_POWER_QUERY, now, WAKE_POLL_MS);
#else
        c->input = YES;                           /* cannot ask, so take it as done */
        c->recheck = false;
        schedule(c, SEND_POWER_QUERY, now, POLL_MS);
#endif
        break;
    case SEND_NONE:
    default:
        break;
    }
    return what;
}

ctrl_led_t ctrl_led(const ctrl_t *c)
{
    if (!c->answering) {
        return LED_FAST;
    }
    if (c->power == YES && c->input == YES) {
        return LED_SOLID;
    }
    return LED_SLOW;
}
