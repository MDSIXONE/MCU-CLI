# MCU CLI 命令参考

## 串口工具 (serial_monitor.py)

### 列出串口
```bash
python scripts/serial_monitor.py list
```

### 读取串口数据
```bash
python scripts/serial_monitor.py read COM9 --baud 115200 --timeout 5
python scripts/serial_monitor.py read COM9 --wait-for "BOOT"
```

### 监控串口
```bash
python scripts/serial_monitor.py monitor COM9 --duration 10
python scripts/serial_monitor.py monitor COM9 --keyword "ERROR"
```

### 发送数据
```bash
python scripts/serial_monitor.py send COM9 "Hello"
python scripts/serial_monitor.py send COM9 "AT" --no-newline
```

## 烧录工具 (flash_tool.py)

### 列出调试探针
```bash
python scripts/flash_tool.py list-probes
```

### SWD 烧录
```bash
python scripts/flash_tool.py flash-swd firmware.bin --chip STM32F103C8
```

### UART ISP 烧录
```bash
python scripts/flash_tool.py flash-uart firmware.bin --port COM9
```

### TI MSPM0 经 SEGGER J-Link 烧录
```bash
# 直接烧录 .out 固件
python mcucli.py flash mspm0 firmware.out

# 指定 CCS 工程目录，先编译再烧录并验证运行
python mcucli.py flash mspm0 "<ccs_project_dir>" --build --verify

# 多探针时指定序列号（通常可省略，见下方 auto-fallback）
python mcucli.py flash mspm0 firmware.out --serial <SN>

# 只打印命令不执行（验证流程）
python mcucli.py flash mspm0 firmware.out --dry-run

# 自定义器件/接口/速率
python mcucli.py flash mspm0 firmware.out --device MSPM0G3507 --interface SWD --speed 4000
```

> **开源约定**：通用框架不内置任何探针序列号/工程路径。`--serial` 省略时走 auto-fallback；
> 项目专属信息（序列号、CCS 工程路径等）放 `Project/<项目>/board.json`，由该项目的 `flash.py` 读取传入。

> **auto-fallback**：`flash mspm0` 未传 `--serial` 时，直接枚举当前 USB 上的 J-Link 探针
> （`JLink.exe ShowEmuList`）自动选择；若传了 `--serial` 但该探针不在线
> （"Connecting to J-Link ...FAILED"），也会自动枚举在线探针重试一次，
> 结果带 `fallback`/`serial` 字段说明实际所用探针。

### 列出 J-Link 探针（实时枚举 USB）
```bash
python scripts/flash_tool.py list-jlink
```

### 读取寄存器
```bash
python scripts/flash_tool.py read-regs
python scripts/flash_tool.py read-regs --names PC SP LR SCB_CFSR
```

### 分析故障
```bash
python scripts/flash_tool.py analyze-fault --cfsr 0x00000000
```

## 编译工具 (compile_tool.py)

### 检查工具链
```bash
python scripts/compile_tool.py check
```

### 编译 STM32
```bash
python scripts/compile_tool.py compile-stm32 main.c --chip STM32F103C8
```

### 编译 ESP32
```bash
python scripts/compile_tool.py compile-esp32 main.py --board esp32
```

### 烧录 ESP32
```bash
python scripts/compile_tool.py flash-esp32 main.py --port COM9
```

## 硬件连接工具 (hardware_connect.py)

### 连接设备
```bash
python scripts/hardware_connect.py connect --chip STM32F103C8 --method swd
```

### 断开连接
```bash
python scripts/hardware_connect.py disconnect
```

### 读取寄存器
```bash
python scripts/hardware_connect.py read-regs
python scripts/hardware_connect.py read-regs --names PC SP LR
```

### 写入寄存器
```bash
python scripts/hardware_connect.py write-reg PC 0x08000000
```

### 复位设备
```bash
python scripts/hardware_connect.py reset
```

### 分析故障
```bash
python scripts/hardware_connect.py analyze-fault --cfsr 0x00000082
```

## Python API 使用

### 串口监控
```python
from scripts.serial_monitor import list_serial_ports, read_serial, monitor_serial

# 列出串口
ports = list_serial_ports()

# 读取数据
result = read_serial("COM9", baud=115200, timeout=3, wait_for="BOOT")

# 监控串口
result = monitor_serial("COM9", duration=10, keyword="ERROR")
```

### 烧录工具
```python
from scripts.flash_tool import flash_swd, flash_uart, flash_mspm0, read_registers

# SWD 烧录
result = flash_swd("firmware.bin", chip="STM32F103C8")

# UART 烧录
result = flash_uart("firmware.bin", port="COM9")

# TI MSPM0 经 J-Link 烧录（path 可为 .out 文件或 CCS 工程目录）
result = flash_mspm0("firmware.out")
result = flash_mspm0("project_dir", build=True, verify=True, dry_run=False)
# 可选参数: device, interface, speed, serial

# 读取寄存器
result = read_registers(["PC", "SP", "SCB_CFSR"])
```

### 编译工具
```python
from scripts.compile_tool import compile_stm32, check_toolchain

# 检查工具链
status = check_toolchain()

# 编译代码
result = compile_stm32("main.c", chip="STM32F103C8")
```

### 硬件连接
```python
from scripts.hardware_connect import connect_hardware, read_registers, reset_device

# 连接设备
result = connect_hardware("STM32F103C8", method="swd")

# 读取寄存器
result = read_registers(["PC", "SCB_CFSR"])

# 复位设备
result = reset_device()
```

## 常用寄存器

### STM32F1 系统寄存器
- **SCB_CPUID** (0xE000ED00): CPU ID
- **SCB_ICSR** (0xE000ED04): 中断控制状态
- **SCB_VTOR** (0xE000ED08): 向量表偏移
- **SCB_AIRCR** (0xE000ED0C): 应用中断和复位控制
- **SCB_SCR** (0xE000ED10): 系统控制
- **SCB_CCR** (0xE000ED14): 配置控制
- **SCB_CFSR** (0xE000ED28): 可配置故障状态
- **SCB_HFSR** (0xE000ED2C): 硬故障状态
- **SCB_BFAR** (0xE000ED38): 总线故障地址

### 故障状态寄存器位
- **IACCVIOL** (bit 0): 指令访问违规
- **DACCVIOL** (bit 1): 数据访问违规
- **IBUSERR** (bit 8): 指令总线错误
- **PRECISERR** (bit 9): 精确总线错误
- **IMPRECISERR** (bit 10): 非精确总线错误
- **UNDEFINSTR** (bit 16): 未定义指令
- **INVSTATE** (bit 17): 无效 EPSR 状态
- **UNALIGNED** (bit 24): 非对齐访问
- **DIVBYZERO** (bit 25): 除零