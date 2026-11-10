/* Whole-loop scenarios for the builds that never query the input (CFG_INPUT_QUERY=0). */
#include "test.h"
#include "hal_host.h"
#include "app.h"

static void boot(void)
{
    host_reset();
    app_init();
}

static void scenario_noquery_wake_selects_stb_once(void)
{
    boot();
    host_run_ms(8000);
    CHECK(amp.on);
    CHECK_EQ(amp.input, 0x05);
    CHECK_EQ(amp.n_select, 1);
    CHECK_EQ(amp.n_input_query, 0);
    CHECK_EQ(host_led_mode(), LED_SOLID);
}

static void scenario_noquery_rejected_select_is_retried(void)
{
    boot();
    amp.input_busy_ms = 4000;            /* the amp answers select with 85 for a while after starting */
    host_run_ms(14000);
    CHECK(amp.on);
    CHECK_EQ(amp.input, 0x05);
    CHECK(amp.n_select >= 2);
    CHECK_EQ(host_led_mode(), LED_SOLID);
}

static void scenario_noquery_announced_input_change_is_corrected(void)
{
    boot();
    host_run_ms(8000);
    sim_amp_front_panel_input(&amp, 0x06);
    host_run_ms(5000);
    CHECK_EQ(amp.input, 0x05);
    CHECK_EQ(amp.n_select, 2);
}

static void scenario_noquery_steady_state_sends_only_power_queries(void)
{
    boot();
    host_run_ms(8000);
    uint16_t power_ons = amp.n_power_on, selects = amp.n_select;
    host_run_ms(60000);
    CHECK_EQ(amp.n_power_on, power_ons);
    CHECK_EQ(amp.n_select, selects);
    CHECK_EQ(amp.n_input_query, 0);
}

int main(void)
{
    RUN(scenario_noquery_wake_selects_stb_once);
    RUN(scenario_noquery_rejected_select_is_retried);
    RUN(scenario_noquery_announced_input_change_is_corrected);
    RUN(scenario_noquery_steady_state_sends_only_power_queries);
    TEST_MAIN_END();
}
