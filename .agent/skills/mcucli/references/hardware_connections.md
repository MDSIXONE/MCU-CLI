# 硬件连接参考

## STM32 连接

### SWD 连接 (推荐)
```
ST-Link / J-Link      STM32
  SWDIO   ─────────── PA13
  SWCLK   ─────────── PA14
  GND     ─────────── GND
  3.3V    ─────────── 3.3V
```

### 串口连接
```
USB-TTL               STM32
  TX      ──────────→ PA10 (RX)
  RX      ←────────── PA9 (TX)
  GND     ─────────── GND
```

### UART ISP 烧录连接
```
USB-TTL               STM32
  TX      ──────────→ PA10 (RX)
  RX      ←────────── PA9 (TX)
  GND     ─────────── GND
  BOOT0   ─────────── 3.3V (高电平)
  NRST    ─────────── GND (复位)
```

## ESP32 连接

### 串口连接
```
USB-TTL               ESP32
  TX      ──────────→ GPIO3 (RX)
  RX      ←────────── GPIO1 (TX)
  GND     ─────────── GND
  GPIO0   ─────────── GND (进入下载模式)
```

### USB 直连
大多数 ESP32 开发板内置 USB-UART 转换器，直接用 USB 线连接即可。

## RP2040 / Raspberry Pi Pico

### 串口连接
```
USB-TTL               Pico
  TX      ──────────→ GP1 (RX)
  RX      ←────────── GP0 (TX)
  GND     ─────────── GND
```

### USB 直连
Pico 内置 USB-UART，可直接通过 USB 连接。

## 常见问题

### 串口权限问题 (Linux)
```bash
# 添加用户到 dialout 组
sudo usermod -aG dialout $USER
newgrp dialout

# 或者临时设置权限
sudo chmod 666 /dev/ttyUSB0
```

### 驱动安装 (Windows)
- **CH340**: 下载 CH340 驱动
- **CP2102**: 下载 CP210x 驱动
- **FTDI**: 下载 FTDI 驱动

### BOOT0 引脚设置
- **正常运行**: BOOT0 接 GND
- **UART 下载模式**: BOOT0 接 3.3V，然后复位

## 调试探针

### ST-Link V2
- 支持 SWD 调试
- 可烧录 STM32 全系列
- 支持寄存器读取和断点

### J-Link
- 支持 SWD/JTAG
- 性能更好
- 支持更多芯片

### ESP-Prog
- 支持 ESP32 系列
- 支持 JTAG 调试