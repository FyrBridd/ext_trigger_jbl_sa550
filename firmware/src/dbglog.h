/* Debug builds only: a small log, kept in the controller's EEPROM, of what the
 * amp answered to each kind of command. It lets the amp's replies be read back
 * through the programmer after trying the dongle at the amp, with no scope.
 * tools/decode_eeprom.py prints it.
 *
 * EEPROM layout (104 bytes used):
 *   0  magic D5        1  layout version 01
 *   2  boot count (stops at 255)       3  unused
 *   4 + 20*k  bucket k:  0 power query, 1 power on, 2 input query,
 *                        3 select STB, 4 frames nobody asked for
 * Each 20-byte bucket: byte 0 timeouts (stops at 255), byte 1 number of
 * records (0-3), then three 6-byte records: cmd, answer, len, data0-2.
 * A bucket keeps the first three *different* frames it sees. */
#ifndef DBGLOG_H
#define DBGLOG_H

#include "ctrl.h"
#include "proto.h"

#define DBGLOG_MAGIC 0xD5
#define DBGLOG_VERSION 0x01
#define DBGLOG_BASE 4
#define DBGLOG_BUCKETS 5
#define DBGLOG_BUCKET_SIZE 20
#define DBGLOG_RECORDS 3
#define DBGLOG_RECORD_SIZE 6
#define DBGLOG_UNSOLICITED 4

void dbglog_init(void);
void dbglog_sent(ctrl_send_t what);              /* we sent a command */
void dbglog_frame(const proto_frame_t *f);       /* the amp sent a frame */

#endif
