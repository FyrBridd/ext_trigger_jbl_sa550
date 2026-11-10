/* Timings and build options. Every value can be overridden with -D on the
 * compiler command line; the timings are expected to be tuned on the real amp. */
#ifndef CONFIG_H
#define CONFIG_H

/* --- timings, milliseconds --- */
#ifndef STARTUP_MS
#define STARTUP_MS 50            /* wait for the serial driver's charge pump */
#endif
#ifndef POLL_MS
#define POLL_MS 2000             /* re-check interval once the amp is on and on STB */
#endif
#ifndef WAKE_POLL_MS
#define WAKE_POLL_MS 500         /* re-check interval while it is not */
#endif
#ifndef REPLY_TIMEOUT_MS
#define REPLY_TIMEOUT_MS 3000    /* how long to wait for a reply once the amp is known to be on:
                                    the protocol allows the amp 3 s */
#endif
#ifndef WAKE_REPLY_TIMEOUT_MS
#define WAKE_REPLY_TIMEOUT_MS 1000   /* how long to wait for a power reply while the amp is not
                                        known to be on; short, so a waking amp is noticed quickly.
                                        Acting early here only costs one more power-on command. */
#endif
#ifndef SETTLE_MS
#define SETTLE_MS 1500           /* pause after the amp first reports on */
#endif
#ifndef PARSER_GAP_MS
#define PARSER_GAP_MS 50         /* silence that abandons a half-received frame */
#endif

/* --- protocol --- */
#ifndef INPUT_STB
#define INPUT_STB 0x05           /* the STB input's code */
#endif

/* --- build variants --- */
#ifndef CFG_POWER_RC5
#define CFG_POWER_RC5 0          /* 1 = send power-on as a simulated remote-control code */
#endif
#ifndef CFG_INPUT_RC5
#define CFG_INPUT_RC5 0          /* 1 = send select-STB as a simulated remote-control code */
#endif
#ifndef CFG_INPUT_QUERY
#define CFG_INPUT_QUERY 1        /* 0 = never query the input; select STB once after waking */
#endif
#ifndef CFG_DEBUG
#define CFG_DEBUG 0              /* 1 = live trace on PA1 and a reply log in EEPROM */
#endif

#endif
