#include "proto.h"

enum { S_HUNT, S_ZONE, S_CMD, S_ANSWER, S_LEN, S_DATA, S_END };

uint8_t proto_build(uint8_t *buf, uint8_t cmd, const uint8_t *data, uint8_t len)
{
    uint8_t n = 0;
    buf[n++] = PROTO_START;
    buf[n++] = PROTO_ZONE;
    buf[n++] = cmd;
    buf[n++] = len;
    for (uint8_t i = 0; i < len; i++) {
        buf[n++] = data[i];
    }
    buf[n++] = PROTO_END;
    return n;
}

void proto_parser_init(proto_parser_t *p)
{
    p->state = S_HUNT;
    p->got = 0;
}

bool proto_parser_busy(const proto_parser_t *p)
{
    return p->state != S_HUNT;
}

bool proto_parser_feed(proto_parser_t *p, uint8_t byte, proto_frame_t *out)
{
    switch (p->state) {
    case S_HUNT:
        if (byte == PROTO_START) {
            p->state = S_ZONE;
        }
        break;
    case S_ZONE:
        p->frame.zone = byte;
        p->state = S_CMD;
        break;
    case S_CMD:
        p->frame.cmd = byte;
        p->state = S_ANSWER;
        break;
    case S_ANSWER:
        p->frame.answer = byte;
        p->state = S_LEN;
        break;
    case S_LEN:
        /* The frame's extent comes from this byte, never from looking for 0D:
         * data bytes may equal 21 or 0D. */
        if (byte > PROTO_MAX_DATA) {
            p->state = S_HUNT;      /* longer than anything we use: drop it */
            break;
        }
        p->frame.len = byte;
        p->got = 0;
        p->state = byte ? S_DATA : S_END;
        break;
    case S_DATA:
        p->frame.data[p->got++] = byte;
        if (p->got == p->frame.len) {
            p->state = S_END;
        }
        break;
    case S_END:
        p->state = S_HUNT;
        if (byte == PROTO_END) {
            *out = p->frame;
            return true;
        }
        break;                      /* wrong end byte: drop the frame */
    }
    return false;
}
