#include "sim_amp.h"

#include <string.h>

/* Command frames have no answer byte, so this is its own small parser and not
 * proto.c's response parser. */

static void out_byte(sim_amp_t *a, uint8_t byte, uint32_t at)
{
    a->out[a->out_tail].byte = byte;
    a->out[a->out_tail].at = at;
    a->out_tail = (uint16_t)((a->out_tail + 1) % SIM_OUT_MAX);
}

static void send(sim_amp_t *a, uint8_t cmd, uint8_t answer, const uint8_t *data, uint8_t len)
{
    uint32_t at = a->now + a->reply_delay_ms;
    out_byte(a, 0x21, at);
    out_byte(a, 0x01, at);
    out_byte(a, cmd, at);
    out_byte(a, answer, at);
    out_byte(a, len, at);
    for (uint8_t i = 0; i < len; i++) {
        out_byte(a, data[i], at);
    }
    out_byte(a, 0x0D, at);
}

static void send_power(sim_amp_t *a)
{
    uint8_t d = a->on ? 1 : 0;
    send(a, 0x00, 0x00, &d, 1);
}

static void send_input(sim_amp_t *a)
{
    uint8_t d = (uint8_t)(a->input | (a->processor_mode ? 0x10 : 0x00));
    send(a, 0x1D, 0x00, &d, 1);
}

void sim_amp_init(sim_amp_t *a)
{
    memset(a, 0, sizeof *a);
    a->rs232_in_standby = true;
    a->announce = true;
    a->processor_mode = true;
    a->boot_ms = 3000;
    a->reply_delay_ms = 20;
    a->input = 0x06;
}

static bool can_answer(const sim_amp_t *a)
{
    if (a->booting) {
        return a->ack_state;
    }
    return a->on || a->rs232_in_standby;
}

static void power_on_command(sim_amp_t *a)
{
    a->n_power_on++;
    if (a->on) {
        send_power(a);
    } else if (a->rs232_in_standby) {
        if (!a->booting) {
            a->booting = true;             /* silent until it has started up, unless ack_state */
            a->boot_done_at = a->now + a->boot_ms;
        }
        if (a->ack_state) {
            send_power(a);                 /* "standby": the state right now */
        }
    }
}

/* returns the answer code */
static uint8_t input_command(sim_amp_t *a, bool is_query, uint8_t input)
{
    if (is_query) {
        a->n_input_query++;
    } else {
        a->n_select++;
    }
    if (!a->on || a->now < a->busy_until) {
        return 0x85;                       /* command invalid at this time */
    }
    if (!is_query && !a->select_ignored) {
        a->input = input;
    }
    return 0x00;
}

static void handle(sim_amp_t *a, uint8_t cmd, const uint8_t *data, uint8_t len)
{
    if (cmd == 0x00 && len == 1) {
        if (data[0] == 0xF0) {
            a->n_power_query++;
            if (can_answer(a)) {
                send_power(a);
            }
        } else if (data[0] == 0x01) {
            power_on_command(a);
        }
    } else if (cmd == 0x1D && len == 1) {
        bool is_query = data[0] == 0xF0;
        bool answering = can_answer(a);
        uint8_t answer = input_command(a, is_query, data[0] & 0x0F);
        if (!answering) {
            return;
        }
        if (answer == 0x00) {
            send_input(a);
        } else {
            send(a, 0x1D, answer, 0, 0);
        }
    } else if (cmd == 0x08 && len == 2 && data[0] == 0x10) {   /* simulated remote control */
        bool answering = can_answer(a);
        if (data[1] == 0x7B) {
            bool was_on = a->on;
            power_on_command(a);           /* replies with a power frame itself if already on */
            if (answering && !was_on) {
                return;                    /* starting up: silent */
            }
            if (answering) {
                send(a, 0x08, 0x00, data, 2);
            }
        } else if (data[1] == 0x64) {
            uint8_t answer = input_command(a, false, 0x05);
            if (answering) {
                send(a, 0x08, answer, data, 2);
                if (answer == 0x00) {
                    send_input(a);
                }
            }
        }
    }
}

void sim_amp_rx_byte(sim_amp_t *a, uint8_t byte)
{
    if (a->disconnected) {
        return;
    }
    if (a->cmd_n == 0 && byte != 0x21) {
        return;
    }
    a->cmd[a->cmd_n++] = byte;
    if (a->cmd_n >= 4) {
        uint8_t len = a->cmd[3];
        if (len > 8) {
            a->cmd_n = 0;
        } else if (a->cmd_n == (uint8_t)(len + 5)) {
            if (byte == 0x0D) {
                handle(a, a->cmd[2], &a->cmd[4], len);
            }
            a->cmd_n = 0;
        }
    }
}

bool sim_amp_tx_byte(sim_amp_t *a, uint8_t *byte)
{
    if (a->out_head == a->out_tail || a->out[a->out_head].at > a->now) {
        return false;
    }
    *byte = a->out[a->out_head].byte;
    a->out_head = (uint16_t)((a->out_head + 1) % SIM_OUT_MAX);
    return !a->disconnected;
}

void sim_amp_tick(sim_amp_t *a, uint32_t now_ms)
{
    a->now = now_ms;
    if (a->booting && a->now >= a->boot_done_at) {
        a->booting = false;
        a->on = true;
        a->busy_until = a->now + a->input_busy_ms;
    }
}

void sim_amp_front_panel_input(sim_amp_t *a, uint8_t input)
{
    a->input = input;
    if (a->announce && a->on) {
        send_input(a);
    }
}

void sim_amp_front_panel_standby(sim_amp_t *a)
{
    a->on = false;
    a->booting = false;
    if (a->announce) {
        send_power(a);
    }
}

void sim_amp_front_panel_on(sim_amp_t *a)
{
    a->on = true;
    a->booting = false;
    a->busy_until = a->now + a->input_busy_ms;
    if (a->announce) {
        send_power(a);
    }
}

void sim_amp_inject(sim_amp_t *a, const uint8_t *bytes, uint8_t n)
{
    for (uint8_t i = 0; i < n; i++) {
        out_byte(a, bytes[i], a->now);
    }
}
