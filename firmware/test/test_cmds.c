#include "test.h"
#include "config.h"
#include "ctrl.h"
#include "cmds.h"

static uint8_t b[8];

static void test_queries(void)
{
    CHECK_HEX(b, cmds_build(SEND_POWER_QUERY, b), "21 01 00 01 F0 0D");
    CHECK_HEX(b, cmds_build(SEND_INPUT_QUERY, b), "21 01 1D 01 F0 0D");
}

static void test_power_on(void)
{
#if CFG_POWER_RC5
    CHECK_HEX(b, cmds_build(SEND_POWER_ON, b), "21 01 08 02 10 7B 0D");
#else
    CHECK_HEX(b, cmds_build(SEND_POWER_ON, b), "21 01 00 01 01 0D");
#endif
}

static void test_select_stb(void)
{
#if CFG_INPUT_RC5
    CHECK_HEX(b, cmds_build(SEND_SELECT_STB, b), "21 01 08 02 10 64 0D");
#else
    CHECK_HEX(b, cmds_build(SEND_SELECT_STB, b), "21 01 1D 01 05 0D");
#endif
}

static void test_none_sends_nothing(void)
{
    CHECK_EQ(cmds_build(SEND_NONE, b), 0);
}

int main(void)
{
    RUN(test_queries);
    RUN(test_power_on);
    RUN(test_select_stb);
    RUN(test_none_sends_nothing);
    TEST_MAIN_END();
}
