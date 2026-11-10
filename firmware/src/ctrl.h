/* The controller: decides what to ask or tell the amp, and when. */
#ifndef CTRL_H
#define CTRL_H

#include <stdbool.h>
#include <stdint.h>

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

#endif
