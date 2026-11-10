# WiiM trigger to JBL SA550 serial dongle

A small inline board, powered by a WiiM Ultra's 12 V trigger output, that keeps
a JBL SA550 Classic amplifier switched on and on its STB input over RS232.

- Design: `docs/superpowers/specs/2026-11-10-wiim-trigger-jbl-dongle-design.md`
- Plans: `docs/superpowers/plans/`

All tools (KiCad 10, the AVR compiler, the tests) run in a Docker container.
Run every command through the wrapper, for example:

    tools/dev pytest tools/tests -q
