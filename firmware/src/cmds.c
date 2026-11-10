#include "cmds.h"

#include "config.h"
#include "proto.h"

/* Simulated remote-control (RC5) codes: system 16, then the command. */
#define RC5_SYSTEM 0x10
#define RC5_POWER_ON 0x7B
#define RC5_STB 0x64

static uint8_t one(uint8_t *buf, uint8_t cmd, uint8_t value)
{
    return proto_build(buf, cmd, &value, 1);
}

#if CFG_POWER_RC5 || CFG_INPUT_RC5
static uint8_t rc5(uint8_t *buf, uint8_t code)
{
    const uint8_t data[2] = { RC5_SYSTEM, code };
    return proto_build(buf, PROTO_CMD_RC5, data, 2);
}
#endif

uint8_t cmds_build(ctrl_send_t what, uint8_t *buf)
{
    switch (what) {
    case SEND_POWER_QUERY:
        return one(buf, PROTO_CMD_POWER, PROTO_QUERY);
    case SEND_INPUT_QUERY:
        return one(buf, PROTO_CMD_INPUT, PROTO_QUERY);
    case SEND_POWER_ON:
#if CFG_POWER_RC5
        return rc5(buf, RC5_POWER_ON);
#else
        return one(buf, PROTO_CMD_POWER, 0x01);
#endif
    case SEND_SELECT_STB:
#if CFG_INPUT_RC5
        return rc5(buf, RC5_STB);
#else
        return one(buf, PROTO_CMD_INPUT, INPUT_STB);
#endif
    case SEND_NONE:
    default:
        return 0;
    }
}
