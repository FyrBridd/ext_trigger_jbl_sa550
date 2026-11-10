#include "test.h"
#include "hal_host.h"
#include "app.h"

/* host_reset also puts the simulated amp back to its defaults */
static void boot(void)
{
    host_reset();
    app_init();
}

static void scenario_wake_from_standby(void) {
  boot(); host_run_ms(7000);                              /* 3 s boot + 1.5 s settle + margin */
  CHECK(amp.on); CHECK_EQ(amp.input, 0x05); CHECK_EQ(host_led_mode(), LED_SOLID);
  CHECK(amp.n_power_on >= 1); CHECK_EQ(amp.n_select, 1);
}
static void scenario_steady_state_sends_only_queries(void) {
  boot(); amp.on = true; amp.input = 0x05; host_run_ms(60000);
  CHECK_EQ(amp.n_power_on, 0); CHECK_EQ(amp.n_select, 0); CHECK_EQ(host_led_mode(), LED_SOLID);
  CHECK(amp.n_power_query >= 25 && amp.n_power_query <= 35);      /* about one per 2 s */
}
static void scenario_input_changed_at_front_panel(void) {
  boot(); amp.on = true; amp.input = 0x05; host_run_ms(10000);
  sim_amp_front_panel_input(&amp, 0x06); host_run_ms(5000);
  CHECK_EQ(amp.input, 0x05); CHECK_EQ(amp.n_select, 1);
}
static void scenario_input_changed_without_announcement(void) {
  boot(); amp.on = true; amp.input = 0x05; amp.announce = false; host_run_ms(10000);
  sim_amp_front_panel_input(&amp, 0x06); host_run_ms(5000);
  CHECK_EQ(amp.input, 0x05);
}
static void scenario_standby_at_front_panel(void) {
  boot(); amp.on = true; amp.input = 0x05; amp.announce = false; host_run_ms(10000);
  sim_amp_front_panel_standby(&amp); host_run_ms(2500);
  CHECK(amp.n_power_on >= 1);                             /* command sent within one poll */
  host_run_ms(6000); CHECK(amp.on); CHECK_EQ(amp.input, 0x05);
}
static void scenario_amp_disconnected(void) {
  boot(); amp.disconnected = true; host_run_ms(30000);
  CHECK_EQ(host_led_mode(), LED_FAST); CHECK_EQ(amp.n_select, 0);
}
static void scenario_silent_then_switched_on_by_hand(void) {
  boot(); amp.rs232_in_standby = false; host_run_ms(20000);
  CHECK(!amp.on); CHECK_EQ(host_led_mode(), LED_FAST);
  sim_amp_front_panel_on(&amp); host_run_ms(8000);
  CHECK_EQ(amp.input, 0x05); CHECK_EQ(host_led_mode(), LED_SOLID);
}
static void scenario_input_busy_after_boot(void) {
  boot(); amp.input_busy_ms = 4000; host_run_ms(12000);
  CHECK(amp.on); CHECK_EQ(amp.input, 0x05); CHECK_EQ(amp.n_select, 1);
}
static void scenario_noise_on_the_line(void) {
  boot(); const uint8_t junk[] = {0xFF, 0x21, 0x01, 0x00, 0x00, 0x00, 0x21, 0x0D, 0x37};
  for (int i = 0; i < 20; i++) { sim_amp_inject(&amp, junk, sizeof junk); host_run_ms(700); }
  host_run_ms(8000); CHECK(amp.on); CHECK_EQ(amp.input, 0x05); CHECK_EQ(host_led_mode(), LED_SOLID);
}
static void scenario_long_run_crosses_wrap(void) {
  boot(); amp.on = true; amp.input = 0x05;
  for (int i = 0; i < 7; i++) { host_run_ms(30000); sim_amp_front_panel_input(&amp, 0x02); host_run_ms(5000); CHECK_EQ(amp.input, 0x05); }
  CHECK_EQ(amp.n_power_on, 0); CHECK_EQ(amp.n_select, 7);   /* 245 s: the counter wraps three times */
}
int main(void)
{
    RUN(scenario_wake_from_standby);
    RUN(scenario_steady_state_sends_only_queries);
    RUN(scenario_input_changed_at_front_panel);
    RUN(scenario_input_changed_without_announcement);
    RUN(scenario_standby_at_front_panel);
    RUN(scenario_amp_disconnected);
    RUN(scenario_silent_then_switched_on_by_hand);
    RUN(scenario_input_busy_after_boot);
    RUN(scenario_noise_on_the_line);
    RUN(scenario_long_run_crosses_wrap);
    TEST_MAIN_END();
}
