#include "test.h"
#include "ctrl.h"
#include "dbglog.h"
#include "hal_host.h"
#include "proto.h"

static uint8_t *ee;

/* a blank (erased) EEPROM, then start the log */
static void fresh(void)
{
    host_reset();
    ee = host_eeprom();
    memset(ee, 0xFF, 128);
    dbglog_init();
}

static proto_frame_t fr(uint8_t cmd, uint8_t ans, uint8_t d0)
{
    proto_frame_t f = { 1, cmd, ans, 1, { d0 } };
    return f;
}

static void test_init_writes_header_and_counts_boots(void) {
  fresh(); CHECK_EQ(ee[0], 0xD5); CHECK_EQ(ee[1], 0x01); CHECK_EQ(ee[2], 1);
  for (int k = 0; k < 5; k++) { CHECK_EQ(ee[4 + 20 * k], 0); CHECK_EQ(ee[5 + 20 * k], 0); }
  dbglog_init(); CHECK_EQ(ee[2], 2);
}
static void test_first_frame_goes_to_the_sent_bucket(void) {
  fresh(); dbglog_sent(SEND_POWER_QUERY); proto_frame_t f = fr(0x00, 0, 1); dbglog_frame(&f);
  CHECK_EQ(ee[4 + 1], 1); CHECK_HEX(&ee[4 + 2], 6, "00 00 01 01 00 00");
}
static void test_second_frame_is_unsolicited(void) {
  fresh(); dbglog_sent(SEND_POWER_QUERY); proto_frame_t a = fr(0x00, 0, 1), b = fr(0x1D, 0, 0x15);
  dbglog_frame(&a); dbglog_frame(&b);
  CHECK_EQ(ee[4 + 80 + 1], 1); CHECK_HEX(&ee[4 + 80 + 2], 6, "1D 00 01 15 00 00");
}
static void test_duplicates_not_stored_and_three_record_limit(void) {
  fresh(); for (int i = 0; i < 6; i++) { dbglog_sent(SEND_INPUT_QUERY); proto_frame_t f = fr(0x1D, 0, (uint8_t)(i / 2)); dbglog_frame(&f); }
  CHECK_EQ(ee[4 + 40 + 1], 3);                              /* 0,0,1,1,2,2 -> three distinct */
  dbglog_sent(SEND_INPUT_QUERY); proto_frame_t g = fr(0x1D, 0, 9); dbglog_frame(&g); CHECK_EQ(ee[4 + 40 + 1], 3);
}
static void test_timeouts_counted_per_command(void) {
  fresh(); dbglog_sent(SEND_POWER_QUERY); dbglog_sent(SEND_POWER_ON); dbglog_sent(SEND_POWER_QUERY);
  CHECK_EQ(ee[4 + 0], 1); CHECK_EQ(ee[4 + 20], 1);
}
static void test_error_answer_is_recorded(void) {
  fresh(); dbglog_sent(SEND_SELECT_STB); proto_frame_t f = { 1, 0x1D, 0x85, 0, { 0 } }; dbglog_frame(&f);
  CHECK_HEX(&ee[4 + 60 + 2], 6, "1D 85 00 00 00 00");
}
/* A fixed sequence whose EEPROM image the Python decoder's tests read. */
static void write_golden_file(void)
{
    fresh();
    dbglog_sent(SEND_POWER_QUERY);
    dbglog_sent(SEND_POWER_ON);                 /* so: one power-query timeout */
    proto_frame_t on = fr(0x00, 0x00, 0x01);
    dbglog_frame(&on);
    dbglog_sent(SEND_INPUT_QUERY);
    proto_frame_t stb = fr(0x1D, 0x00, 0x15);
    dbglog_frame(&stb);
    proto_frame_t cd = fr(0x1D, 0x00, 0x06);
    dbglog_frame(&cd);                          /* second frame: unsolicited */
    dbglog_sent(SEND_SELECT_STB);
    proto_frame_t refused = { 1, 0x1D, 0x85, 0, { 0 } };
    dbglog_frame(&refused);

    FILE *f = fopen("build/host/dbglog_golden.bin", "wb");
    CHECK(f != NULL);
    if (f) {
        CHECK_EQ(fwrite(ee, 1, 128, f), 128);
        fclose(f);
    }
}

int main(void)
{
    RUN(test_init_writes_header_and_counts_boots);
    RUN(test_first_frame_goes_to_the_sent_bucket);
    RUN(test_second_frame_is_unsolicited);
    RUN(test_duplicates_not_stored_and_three_record_limit);
    RUN(test_timeouts_counted_per_command);
    RUN(test_error_answer_is_recorded);
    RUN(write_golden_file);
    TEST_MAIN_END();
}
