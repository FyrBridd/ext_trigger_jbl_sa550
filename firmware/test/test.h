#ifndef TEST_H
#define TEST_H
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
static int t_fail, t_run;
#define CHECK(c) do { t_run++; if (!(c)) { t_fail++; printf("  FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)
#define CHECK_EQ(a, b) do { long _a = (long)(a), _b = (long)(b); t_run++; \
  if (_a != _b) { t_fail++; printf("  FAIL %s:%d: %s == %s (%ld vs %ld)\n", __FILE__, __LINE__, #a, #b, _a, _b); } } while (0)
/* parse "21 01 00" into bytes; returns count */
static inline uint8_t hex(const char *s, uint8_t *out) { uint8_t n = 0; unsigned v;
  while (sscanf(s, "%x", &v) == 1) { out[n++] = (uint8_t)v; while (*s && *s != ' ') s++; while (*s == ' ') s++; } return n; }
#define CHECK_HEX(buf, n, str) do { uint8_t _e[64]; uint8_t _n = hex(str, _e); CHECK_EQ(n, _n); CHECK(memcmp(buf, _e, _n) == 0); } while (0)
#define RUN(fn) do { printf("%s\n", #fn); fn(); } while (0)
#define TEST_MAIN_END() do { printf("%d checks, %d failed\n", t_run, t_fail); return t_fail ? 1 : 0; } while (0)
#endif
