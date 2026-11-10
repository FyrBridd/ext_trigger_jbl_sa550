/* The amp's serial frame format (JBL SA750 / Arcam SA-series RS232 protocol).
 *
 *   command:   21 <zone> <cmd> <len> <data x len> 0D
 *   response:  21 <zone> <cmd> <answer> <len> <data x len> 0D
 *
 * No hardware access here; this file is tested on the host. */
#ifndef PROTO_H
#define PROTO_H

#include <stdbool.h>
#include <stdint.h>

#define PROTO_START 0x21
#define PROTO_END 0x0D
#define PROTO_ZONE 0x01
#define PROTO_MAX_DATA 8

#define PROTO_CMD_POWER 0x00
#define PROTO_CMD_RC5 0x08
#define PROTO_CMD_INPUT 0x1D
#define PROTO_QUERY 0xF0        /* data byte that asks for the current state */
#define PROTO_ANSWER_OK 0x00

typedef struct {
    uint8_t zone, cmd, answer, len;
    uint8_t data[PROTO_MAX_DATA];
} proto_frame_t;

typedef struct proto_parser {
    uint8_t state;      /* which field the next byte belongs to */
    uint8_t got;        /* data bytes received so far */
    proto_frame_t frame;
} proto_parser_t;

/* Write a command frame into buf (which must hold len + 5 bytes); returns its length. */
uint8_t proto_build(uint8_t *buf, uint8_t cmd, const uint8_t *data, uint8_t len);

void proto_parser_init(proto_parser_t *p);

/* Give the parser one received byte. Returns true exactly when that byte
 * completes a valid response frame, which is copied to *out. */
bool proto_parser_feed(proto_parser_t *p, uint8_t byte, proto_frame_t *out);

/* True when part-way through a frame. */
bool proto_parser_busy(const proto_parser_t *p);

#endif
