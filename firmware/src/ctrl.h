/* The controller: decides what to ask or tell the amp, and when. */
#ifndef CTRL_H
#define CTRL_H

#include <stdbool.h>
#include <stdint.h>

#include "proto.h"

/* What the controller wants sent next. */
typedef enum {
    SEND_NONE = 0,
    SEND_POWER_QUERY,
    SEND_POWER_ON,
    SEND_INPUT_QUERY,
    SEND_SELECT_STB
} ctrl_send_t;

/* What the status LED should show. */
typedef enum {
    LED_FAST = 0,   /* no answer from the amp */
    LED_SLOW,       /* amp answering; waking it or changing input */
    LED_SOLID       /* amp on and on STB */
} ctrl_led_t;

typedef struct ctrl {
    uint8_t phase;        /* waiting for a time, or for a reply */
    uint8_t next;         /* ctrl_send_t to send when the wait ends */
    uint16_t at;          /* when to send `next`, or the reply deadline */
    uint8_t power;        /* latest known power state */
    uint8_t input;        /* latest known input state */
    bool confirmed_on;    /* the last power *query* said "on" */
    bool answering;       /* false from a power query timing out until any valid frame */
    bool recheck;         /* a frame showed a wrong state: start the next cycle at once */
    bool set_pending;     /* power-on or select sent, and no power query since */
    uint8_t last_set;     /* which of the two it was (ctrl_send_t) */
    uint16_t set_at;      /* when it was sent */
} ctrl_t;

/* `now` everywhere is a free-running 16-bit millisecond counter; it wraps. */

void ctrl_init(ctrl_t *c, uint16_t now);

/* Tell the controller about a frame received from the amp. */
void ctrl_on_frame(ctrl_t *c, const proto_frame_t *f, uint16_t now);

/* Call every loop pass. Returns at most one command to send now. */
ctrl_send_t ctrl_step(ctrl_t *c, uint16_t now);

ctrl_led_t ctrl_led(const ctrl_t *c);

#endif
