#include "dbglog.h"

#include "hal.h"

#define NONE 0xFF

static uint8_t current = NONE;   /* bucket of the last command sent */
static bool answered;            /* a frame has been credited to it */

static uint8_t bucket_addr(uint8_t bucket)
{
    return (uint8_t)(DBGLOG_BASE + DBGLOG_BUCKET_SIZE * bucket);
}

static void bump(uint8_t addr)   /* add one, stopping at 255 */
{
    uint8_t v = hal_ee_read(addr);
    if (v < 255) {
        hal_ee_update(addr, (uint8_t)(v + 1));
    }
}

void dbglog_init(void)
{
    if (hal_ee_read(0) != DBGLOG_MAGIC || hal_ee_read(1) != DBGLOG_VERSION) {
        hal_ee_update(0, DBGLOG_MAGIC);
        hal_ee_update(1, DBGLOG_VERSION);
        hal_ee_update(2, 0);
        hal_ee_update(3, 0);
        for (uint8_t k = 0; k < DBGLOG_BUCKETS; k++) {
            hal_ee_update(bucket_addr(k), 0);
            hal_ee_update((uint8_t)(bucket_addr(k) + 1), 0);
        }
    }
    bump(2);
    current = NONE;
    answered = false;
}

void dbglog_sent(ctrl_send_t what)
{
    if (current != NONE && !answered) {
        bump(bucket_addr(current));              /* the last command got no frame at all */
    }
    current = (uint8_t)(what - 1);               /* SEND_POWER_QUERY is 1 */
    answered = false;
}

static void store(uint8_t bucket, const uint8_t *record)
{
    uint8_t base = bucket_addr(bucket);
    uint8_t count = hal_ee_read((uint8_t)(base + 1));
    for (uint8_t i = 0; i < count; i++) {        /* already have this one? */
        uint8_t at = (uint8_t)(base + 2 + DBGLOG_RECORD_SIZE * i);
        uint8_t same = 0;
        for (uint8_t j = 0; j < DBGLOG_RECORD_SIZE; j++) {
            same += hal_ee_read((uint8_t)(at + j)) == record[j];
        }
        if (same == DBGLOG_RECORD_SIZE) {
            return;
        }
    }
    if (count >= DBGLOG_RECORDS) {
        return;
    }
    uint8_t at = (uint8_t)(base + 2 + DBGLOG_RECORD_SIZE * count);
    for (uint8_t j = 0; j < DBGLOG_RECORD_SIZE; j++) {
        hal_ee_update((uint8_t)(at + j), record[j]);
    }
    hal_ee_update((uint8_t)(base + 1), (uint8_t)(count + 1));
}

void dbglog_frame(const proto_frame_t *f)
{
    uint8_t record[DBGLOG_RECORD_SIZE] = { f->cmd, f->answer, f->len, 0, 0, 0 };
    for (uint8_t i = 0; i < 3 && i < f->len; i++) {
        record[3 + i] = f->data[i];
    }
    /* the first frame after a command is taken as its reply; anything more,
     * or anything before the first command, was not asked for */
    if (current != NONE && !answered) {
        answered = true;
        store(current, record);
    } else {
        store(DBGLOG_UNSOLICITED, record);
    }
}
