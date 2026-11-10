/* A simulated amplifier for host tests: it understands the commands the dongle
 * sends and behaves the way the protocol documents describe, with switches for
 * the awkward cases. */
#ifndef SIM_AMP_H
#define SIM_AMP_H

#include <stdbool.h>
#include <stdint.h>

#define SIM_OUT_MAX 256

typedef struct {
    /* settings */
    bool rs232_in_standby;      /* false: completely silent while in standby */
    bool announce;              /* true: sends unsolicited frames on front-panel changes */
    bool processor_mode;        /* true: input replies have 0x10 set */
    uint16_t boot_ms;           /* silent for this long after a power-on command */
    uint16_t reply_delay_ms;    /* default 20 */
    uint16_t input_busy_ms;     /* answers input commands with 0x85 for this long after boot */
    bool disconnected;          /* true: receives nothing, sends nothing */
    bool ack_state;             /* true: answers power-on at once with its current state, and
                                   keeps answering (as "standby") while it starts up */
    bool select_ignored;        /* true: acknowledges select-STB but stays on its input */
    /* state */
    bool on;
    uint8_t input;
    /* counters of commands received, by meaning (an RC5 power-on counts as a power-on) */
    uint16_t n_power_query, n_power_on, n_input_query, n_select;

    /* internals */
    uint32_t now;
    bool booting;
    uint32_t boot_done_at, busy_until;
    uint8_t cmd[16];
    uint8_t cmd_n;
    struct { uint8_t byte; uint32_t at; } out[SIM_OUT_MAX];
    uint16_t out_head, out_tail;
} sim_amp_t;

/* off, input 0x06, rs232_in_standby, announce, processor_mode, boot 3000 ms */
void sim_amp_init(sim_amp_t *a);

void sim_amp_front_panel_input(sim_amp_t *a, uint8_t input);
void sim_amp_front_panel_standby(sim_amp_t *a);
void sim_amp_front_panel_on(sim_amp_t *a);                            /* at once, no boot delay */
void sim_amp_inject(sim_amp_t *a, const uint8_t *bytes, uint8_t n);   /* raw bytes onto the line toward the dongle */

/* plumbing, used by hal_host */
void sim_amp_tick(sim_amp_t *a, uint32_t now_ms);
void sim_amp_rx_byte(sim_amp_t *a, uint8_t byte);    /* a byte from the dongle */
bool sim_amp_tx_byte(sim_amp_t *a, uint8_t *byte);   /* a byte for the dongle, if one is due */

#endif
