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

/* True for WAKE_POLL_MS after we send power-on or select. A frame in that time
 * showing the old state is the amp acknowledging the command with its state at
 * that moment, not news. */
static bool acknowledging(const ctrl_t *c, uint16_t now)
{
    return c->set_pending && !due(now, c->set_at + WAKE_POLL_MS);
}

/* A frame, not asked for, showed the amp in the wrong state. */
static void wrong_state_seen(ctrl_t *c, uint16_t now)
{
    if (acknowledging(c, now)) {
        /* The re-check is already scheduled. Reacting again here would send
         * commands as fast as the amp answers. */
        return;
    }
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
    c->set_pending = false;
    c->last_set = SEND_NONE;
    schedule(c, SEND_POWER_QUERY, now, STARTUP_MS);
}

/* The amp is confirmed on: what comes next? */
static void after_power_on_confirmed(ctrl_t *c, uint16_t now, bool first_time)
{
    uint16_t delay = first_time ? SETTLE_MS : 0;
#if CFG_INPUT_QUERY
    schedule(c, SEND_INPUT_QUERY, now, delay);
#else
    if (first_time || c->input != YES) {
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
    if (good) {
        /* Not the reply to a pending query: a status report, the acknowledgement
         * of our power-on, or a reply that came after its timeout. Any of them is
         * the amp telling the truth about its state. */
        c->power = on ? YES : NO;
        if (!on) {
            c->confirmed_on = false;
            wrong_state_seen(c, now);
        } else if (!c->confirmed_on && c->phase == PH_WAIT) {
            c->confirmed_on = true;
            after_power_on_confirmed(c, now, true);
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

#if !CFG_INPUT_QUERY
/* Builds that never query the input take a select as done. If the amp refuses
 * it, that must be undone, or the wrong input would be shown as success. */
static void select_refused(ctrl_t *c, uint16_t now)
{
    c->input = NO;
    if (c->phase == PH_WAIT && c->next == SEND_POWER_QUERY) {
        c->at = now + WAKE_POLL_MS;      /* the next cycle will select again */
    }
}
#endif

void ctrl_on_frame(ctrl_t *c, const proto_frame_t *f, uint16_t now)
{
    c->answering = true;
#if !CFG_INPUT_QUERY
    if (c->set_pending && c->last_set == SEND_SELECT_STB && f->answer != PROTO_ANSWER_OK
        && (f->cmd == PROTO_CMD_INPUT || f->cmd == PROTO_CMD_RC5)) {
        select_refused(c, now);
        return;
    }
#endif
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
        c->set_pending = false;
        c->phase = PH_AWAIT_POWER;
        /* patient with an amp that is on, quick to notice one that is waking */
        c->at = now + (c->confirmed_on ? REPLY_TIMEOUT_MS : WAKE_REPLY_TIMEOUT_MS);
        break;
    case SEND_INPUT_QUERY:
        c->recheck = false;
        c->phase = PH_AWAIT_INPUT;
        c->at = now + REPLY_TIMEOUT_MS;
        break;
    case SEND_POWER_ON:
        c->set_pending = true;
        c->last_set = SEND_POWER_ON;
        c->set_at = now;
        schedule(c, SEND_POWER_QUERY, now, WAKE_POLL_MS);
        break;
    case SEND_SELECT_STB:
        c->set_pending = true;
        c->last_set = SEND_SELECT_STB;
        c->set_at = now;
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
