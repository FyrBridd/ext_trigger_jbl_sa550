#include "test.h"
#include "proto.h"

static proto_parser_t p; static proto_frame_t f;
/* feed a hex string; return how many frames completed; last one left in f */
static int feed(const char *s)
{
    uint8_t b[64];
    uint8_t n = hex(s, b);
    int got = 0;
    for (uint8_t i = 0; i < n; i++) {
        got += proto_parser_feed(&p, b[i], &f);
    }
    return got;
}

static void test_build_commands(void) {
  uint8_t b[16], d;
  d = 0xF0; CHECK_HEX(b, proto_build(b, 0x00, &d, 1), "21 01 00 01 F0 0D");
  d = 0x05; CHECK_HEX(b, proto_build(b, 0x1D, &d, 1), "21 01 1D 01 05 0D");
  uint8_t rc5[2] = {0x10, 0x7B}; CHECK_HEX(b, proto_build(b, 0x08, rc5, 2), "21 01 08 02 10 7B 0D");
}
static void test_parse_power_reply(void) {
  proto_parser_init(&p);
  CHECK_EQ(feed("21 01 00 00 01 01 0D"), 1);
  CHECK_EQ(f.zone, 1); CHECK_EQ(f.cmd, 0x00); CHECK_EQ(f.answer, 0x00); CHECK_EQ(f.len, 1); CHECK_EQ(f.data[0], 0x01);
  CHECK(!proto_parser_busy(&p));
}
static void test_parse_error_answer_and_zero_length(void) {
  proto_parser_init(&p);
  CHECK_EQ(feed("21 01 1D 85 00 0D"), 1); CHECK_EQ(f.answer, 0x85); CHECK_EQ(f.len, 0);
}
static void test_data_bytes_that_look_like_framing(void) {
  proto_parser_init(&p);
  CHECK_EQ(feed("21 01 08 00 02 0D 21 0D"), 1);
  CHECK_EQ(f.cmd, 0x08); CHECK_EQ(f.len, 2); CHECK_EQ(f.data[0], 0x0D); CHECK_EQ(f.data[1], 0x21);
}
static void test_back_to_back_frames(void) {
  proto_parser_init(&p);
  CHECK_EQ(feed("21 01 00 00 01 01 0D 21 01 1D 00 01 15 0D"), 2);
  CHECK_EQ(f.cmd, 0x1D); CHECK_EQ(f.data[0], 0x15);
}
static void test_garbage_and_truncated_frames(void) {
  proto_parser_init(&p);
  CHECK_EQ(feed("FF 00 0D 37"), 0);                       /* noise only */
  CHECK_EQ(feed("21 01 00 00 01 01 0D"), 1);              /* still locks on */
  CHECK_EQ(feed("21 01 00 00 01 01 55"), 0);              /* wrong end byte: dropped */
  CHECK_EQ(feed("21 01 1D 00 01 05 0D"), 1); CHECK_EQ(f.cmd, 0x1D);
  CHECK_EQ(feed("21 01 5E 00 09 41 42 43"), 0);           /* length 9 > PROTO_MAX_DATA: dropped */
  CHECK_EQ(feed("21 01 00 00 01 00 0D"), 1); CHECK_EQ(f.data[0], 0x00);
  CHECK_EQ(feed("21 01 00"), 0); CHECK(proto_parser_busy(&p));   /* truncated */
  proto_parser_init(&p);                                         /* what the gap timeout does */
  CHECK_EQ(feed("21 01 00 00 01 01 0D"), 1);
}
int main(void) {
  RUN(test_build_commands); RUN(test_parse_power_reply); RUN(test_parse_error_answer_and_zero_length);
  RUN(test_data_bytes_that_look_like_framing); RUN(test_back_to_back_frames); RUN(test_garbage_and_truncated_frames);
  TEST_MAIN_END();
}
