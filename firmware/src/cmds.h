/* The bytes for each thing the controller can ask the amp to do. */
#ifndef CMDS_H
#define CMDS_H

#include <stdint.h>

#include "ctrl.h"

#define CMDS_MAX_LEN 8

/* Write the command frame for `what` into buf (CMDS_MAX_LEN bytes); returns its
 * length, or 0 for SEND_NONE. Build options CFG_POWER_RC5 and CFG_INPUT_RC5
 * swap in the simulated remote-control codes. */
uint8_t cmds_build(ctrl_send_t what, uint8_t *buf);

#endif
