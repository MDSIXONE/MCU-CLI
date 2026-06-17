/*
 * GARY CLI - Tianmengxing MSPM0G3507 LED Blink
 * Board: LCSC Tianmengxing MSPM0G3507
 * LED: PB22 (PINCM50)
 * UART: COM5 (UART0, PA10 TX, PA11 RX)
 * Interval: 5 seconds
 */

#include "ti_msp_dl_config.h"

#define BLINK_DELAY (CPUCLK_FREQ * 5)

static void uartWriteChar(char ch)
{
    DL_UART_Main_transmitDataBlocking(UART0, (uint8_t) ch);
}

static void uartWriteString(const char *text)
{
    while (*text != '\0') {
        uartWriteChar(*text);
        text++;
    }
}

static void uartWriteUint32(uint32_t val)
{
    char digits[12];
    uint8_t i = 0;
    if (val == 0) {
        digits[i++] = '0';
    } else {
        while (val > 0) {
            digits[i++] = '0' + (val % 10);
            val /= 10;
        }
    }
    while (i > 0) {
        i--;
        uartWriteChar(digits[i]);
    }
}

int main(void)
{
    SYSCFG_DL_init();

    DL_GPIO_clearPins(LED_PORT, LED_PIN);

    uartWriteString("========================================\r\n");
    uartWriteString("  GARY CLI - Tianmengxing MSPM0G3507\r\n");
    uartWriteString("  LED: PB22 | Interval: 5s\r\n");
    uartWriteString("========================================\r\n");
    uartWriteString("[INIT] System ready!\r\n\r\n");

    uint32_t count = 0;

    while (1) {
        delay_cycles(BLINK_DELAY);

        DL_GPIO_togglePins(LED_PORT, LED_PIN);
        count++;

        uartWriteString("[LED] Toggle #");
        uartWriteUint32(count);
        uartWriteString(" | State: ");
        uartWriteString((count % 2 == 1) ? "ON" : "OFF");
        uartWriteString("\r\n");
    }
}
