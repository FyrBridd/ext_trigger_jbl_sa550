/* hal.h for the ATtiny412. The only file that touches hardware registers.
 *
 * Pins:  PA6 serial out (USART0 TxD) -> RS232 driver -> amp
 *        PA7 serial in  (USART0 RxD) <- RS232 driver <- amp
 *        PA3 status LED, high = on
 *        PA1 debug trace output (debug builds only)
 *        PA0 UPDI programming pin: never touched
 *
 * Clock: the internal 20 MHz oscillator divided by 6, the reset default, so
 * F_CPU is 3,333,333 Hz. Serial is 38,400 baud, 8 data bits, no parity, 1 stop. */
#include "hal.h"

#include <avr/interrupt.h>
#include <avr/io.h>
#include <avr/wdt.h>

#include "config.h"

#if CFG_DEBUG
#include <avr/eeprom.h>
#endif

#define BAUD_RATE 38400UL

#define RX_SIZE 16   /* must be a power of two */
static volatile uint8_t rx_buf[RX_SIZE];
static volatile uint8_t rx_head;   /* written by the interrupt */
static uint8_t rx_tail;            /* read by the main loop */

static volatile uint16_t ms;

ISR(USART0_RXC_vect)
{
    uint8_t status = USART0.RXDATAH;   /* must be read before the data */
    uint8_t byte = USART0.RXDATAL;
    if (status & (USART_FERR_bm | USART_BUFOVF_bm)) {
        return;                        /* a damaged byte: the parser resyncs without it */
    }
    uint8_t next = (uint8_t)((rx_head + 1) & (RX_SIZE - 1));
    if (next != rx_tail) {             /* drop the byte if the buffer is full */
        rx_buf[rx_head] = byte;
        rx_head = next;
    }
}

ISR(TCB0_INT_vect)
{
    ms++;
    TCB0.INTFLAGS = TCB_CAPT_bm;
}

void hal_init(void)
{
    /* LED off, serial output idle (high) before the pin is driven */
    PORTA.OUTCLR = PIN3_bm;
    PORTA.OUTSET = PIN6_bm;
    PORTA.DIRSET = PIN3_bm | PIN6_bm;

    /* Serial port. BAUD register = 64 * F_CPU / (16 * baud), then corrected by
     * the oscillator error the factory measured for this chip at 3 V. */
    int32_t baud = (int32_t)((4UL * F_CPU) / BAUD_RATE);
    baud += (baud * (int8_t)SIGROW.OSC20ERR3V) / 1024;
    USART0.BAUD = (uint16_t)baud;
    USART0.CTRLC = USART_CHSIZE_8BIT_gc;
    USART0.CTRLA = USART_RXCIE_bm;
    USART0.CTRLB = USART_RXEN_bm | USART_TXEN_bm;

    /* 1 ms tick */
    TCB0.CCMP = (uint16_t)(F_CPU / 1000UL - 1);
    TCB0.INTCTRL = TCB_CAPT_bm;
    TCB0.CTRLB = TCB_CNTMODE_INT_gc;
    TCB0.CTRLA = TCB_CLKSEL_CLKDIV1_gc | TCB_ENABLE_bm;

#if CFG_DEBUG
    /* debug trace: PA1 idles high; TCA0 counts out one bit time */
    PORTA.OUTSET = PIN1_bm;
    PORTA.DIRSET = PIN1_bm;
    TCA0.SINGLE.PER = (uint16_t)((F_CPU + BAUD_RATE / 2) / BAUD_RATE - 1);
    TCA0.SINGLE.CTRLA = TCA_SINGLE_CLKSEL_DIV1_gc | TCA_SINGLE_ENABLE_bm;
#endif
}

uint16_t hal_millis(void)
{
    uint8_t sreg = SREG;
    cli();
    uint16_t now = ms;
    SREG = sreg;
    return now;
}

bool hal_uart_getc(uint8_t *b)
{
    if (rx_tail == rx_head) {
        return false;
    }
    *b = rx_buf[rx_tail];
    rx_tail = (uint8_t)((rx_tail + 1) & (RX_SIZE - 1));
    return true;
}

void hal_uart_write(const uint8_t *buf, uint8_t n)
{
    for (uint8_t i = 0; i < n; i++) {
        while (!(USART0.STATUS & USART_DREIF_bm)) {
        }
        USART0.TXDATAL = buf[i];
    }
}

void hal_led(bool on)
{
    if (on) {
        PORTA.OUTSET = PIN3_bm;
    } else {
        PORTA.OUTCLR = PIN3_bm;
    }
}

void hal_wdt_kick(void)
{
    wdt_reset();
}

#if CFG_DEBUG
/* One byte out of PA1 at 38,400 baud, bit-banged against TCA0. Interrupts are
 * off for the 260 us it takes; the serial port's own two-byte receive buffer
 * covers that, and the millisecond tick is at worst served late. */
void hal_dbg_putc(uint8_t b)
{
    uint16_t bits = ((uint16_t)b << 1) | 0x0200;   /* start bit, 8 data bits LSB first, stop bit */
    uint8_t sreg = SREG;
    cli();
    TCA0.SINGLE.CNT = 0;
    TCA0.SINGLE.INTFLAGS = TCA_SINGLE_OVF_bm;
    for (uint8_t i = 0; i < 10; i++) {
        if (bits & 1) {
            PORTA.OUTSET = PIN1_bm;
        } else {
            PORTA.OUTCLR = PIN1_bm;
        }
        bits >>= 1;
        while (!(TCA0.SINGLE.INTFLAGS & TCA_SINGLE_OVF_bm)) {
        }
        TCA0.SINGLE.INTFLAGS = TCA_SINGLE_OVF_bm;
    }
    SREG = sreg;
}

uint8_t hal_ee_read(uint8_t addr)
{
    return eeprom_read_byte((const uint8_t *)(uint16_t)addr);
}

void hal_ee_update(uint8_t addr, uint8_t v)
{
    eeprom_update_byte((uint8_t *)(uint16_t)addr, v);
}
#endif
