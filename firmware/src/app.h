/* The application: ties the serial port, the frame parser, the controller and
 * the LED together. main() calls app_init() once and then app_step() forever. */
#ifndef APP_H
#define APP_H

void app_init(void);
void app_step(void);

#endif
