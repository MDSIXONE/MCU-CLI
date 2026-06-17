/*
 * GARY CLI - Tianmengxing MSPM0G3507 Configuration
 */
#ifndef ti_msp_dl_config_h
#define ti_msp_dl_config_h

#define CONFIG_MSPM0G3507

#if defined(__ti_version__) || defined(__TI_COMPILER_VERSION__)
#define SYSCONFIG_WEAK __attribute__((weak))
#elif defined(__IAR_SYSTEMS_ICC__)
#define SYSCONFIG_WEAK __weak
#elif defined(__GNUC__)
#define SYSCONFIG_WEAK __attribute__((weak))
#endif

#include <ti/devices/msp/msp.h>
#include <ti/driverlib/driverlib.h>
#include <ti/driverlib/m0p/dl_core.h>

#ifdef __cplusplus
extern "C" {
#endif

#define POWER_STARTUP_DELAY                                                (16)
#define CPUCLK_FREQ                                                     32000000

#define UART_BAUD_RATE                                                 (115200)
#define UART_IBRD_32_MHZ_115200_BAUD                                     (17)
#define UART_FBRD_32_MHZ_115200_BAUD                                     (23)

#define UART_INST                                                         UART0
#define UART_INST_IRQHandler                                   UART0_IRQHandler
#define UART_INST_INT_IRQN                                       UART0_INT_IRQn

#define GPIO_UART_TX_PORT                                               GPIOA
#define GPIO_UART_RX_PORT                                               GPIOA
#define GPIO_UART_TX_PIN                                       DL_GPIO_PIN_10
#define GPIO_UART_RX_PIN                                       DL_GPIO_PIN_11
#define GPIO_UART_TX_IOMUX                                    (IOMUX_PINCM21)
#define GPIO_UART_RX_IOMUX                                    (IOMUX_PINCM22)
#define GPIO_UART_TX_IOMUX_FUNC                 IOMUX_PINCM21_PF_UART0_TX
#define GPIO_UART_RX_IOMUX_FUNC                 IOMUX_PINCM22_PF_UART0_RX

#define LED_PORT                                                           GPIOB
#define LED_PIN                                                    DL_GPIO_PIN_22
#define LED_IOMUX                                                (IOMUX_PINCM50)

#define KEY_PORT                                                           GPIOB
#define KEY_PIN                                                    DL_GPIO_PIN_21
#define KEY_IOMUX                                                (IOMUX_PINCM49)

void SYSCFG_DL_init(void);
void SYSCFG_DL_initPower(void);
void SYSCFG_DL_GPIO_init(void);
void SYSCFG_DL_SYSCTL_init(void);
void SYSCFG_DL_UART_init(void);

#ifdef __cplusplus
}
#endif

#endif /* ti_msp_dl_config_h */
