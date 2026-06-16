---
name: mcucli
description: MCU CLI 工具集，用于嵌入式开发、烧录、串口监控和调试。支持 STM32、ESP32、RP2040 等芯片。当用户需要烧录固件、串口通信、硬件调试、编译嵌入式代码时使用此技能。每个任务都存放在 Project/ 目录下，包含 TASK.md 文档记录任务详情。
---

# MCU CLI 技能

提供嵌入式开发所需的工具和流程，让外部 AI 可以调用硬件操作功能。

## 核心工具

### 1. 串口监控工具
- **文件**: `scripts/serial_monitor.py`
- **功能**: 打开串口、读取数据、等待特定字符串、列出可用串口
- **使用场景**: 监控设备输出、调试通信、验证程序运行

### 2. 烧录工具
- **文件**: `scripts/flash_tool.py`
- **功能**: SWD 烧录、UART ISP 烧录、检测调试探针
- **使用场景**: 将固件下载到 MCU

### 3. 编译工具
- **文件**: `scripts/compile_tool.py`
- **功能**: GCC 交叉编译、生成二进制文件、检查工具链
- **使用场景**: 编译 STM32 HAL 项目

### 4. 硬件连接工具
- **文件**: `scripts/hardware_connect.py`
- **功能**: 连接 SWD 探针、读取寄存器、分析故障
- **使用场景**: 硬件调试、故障诊断

## 任务管理

### 任务目录结构

所有任务都存放在 `Project/` 目录下，每个任务一个文件夹：

```
Project/
├── README.md                    # 任务管理说明
├── ESP32_S3LED/                 # ESP32 S3 LED 控制任务
│   └── TASK.md                  # 任务详情文档
├── STM32_Motor/                 # STM32 电机控制任务
│   └── TASK.md
└── ...                          # 更多任务
```

### 任务文件夹命名规范

- 格式：`芯片型号_功能描述`
- 示例：`ESP32_S3LED`、`STM32_Motor`、`RP2040_Temperature`

### TASK.md 文档结构

每个任务文件夹必须包含 `TASK.md`，内容包括：

1. **任务概述** - 任务目标和背景
2. **硬件信息** - MCU 型号、引脚连接、外设配置
3. **完成的工作** - 已实现的功能列表
4. **遇到的问题** - 问题描述
5. **解决方案** - 如何解决问题
6. **测试结果** - 测试通过情况
7. **下一步计划** - 后续工作
8. **相关文件** - 代码、配置、文档链接

### 任务管理流程

1. **开始新任务**
   - 在 `Project/` 下创建任务文件夹
   - 创建 `TASK.md` 并填写基本信息
   - 记录硬件配置和目标

2. **执行任务**
   - 按照 TASK.md 中的计划执行
   - 遇到问题及时记录
   - 解决问题后更新 TASK.md

3. **完成任务**
   - 更新"完成的工作"部分
   - 更新"测试结果"部分
   - 更新"下一步计划"（如有）
   - 添加更新记录

4. **查看历史任务**
   - 读取 `Project/README.md` 了解所有任务
   - 读取特定任务的 `TASK.md` 了解详情

### 示例任务

**ESP32 S3 LED 控制任务** (`Project/ESP32_S3LED/TASK.md`)
- MCU: ESP32-S3
- 目标: 控制板载 LED 闪烁
- 状态: 已完成基本通信测试

## 标准工作流程

### 流程 1: 烧录并验证
```python
# 1. 连接硬件
result = connect_hardware(chip="STM32F103C8")

# 2. 烧录固件
flash_result = flash_firmware("firmware.bin", method="swd")

# 3. 监控串口验证
serial_data = monitor_serial(port="COM9", baud=115200, timeout=5)
```

### 流程 2: 编译烧录调试循环
```python
# 1. 编译代码
compile_result = compile_code("main.c", chip="STM32F103C8")

# 2. 烧录
if compile_result["success"]:
    flash_result = flash_firmware(compile_result["bin_path"])

# 3. 读取串口输出
output = monitor_serial(port="COM9", wait_for="BOOT", timeout=3)

# 4. 分析结果
if "ERROR" in output:
    # 读取寄存器诊断
    regs = read_registers(names=["SCB_CFSR", "PC"])
    fault_analysis = analyze_fault(regs)
```

### 流程 3: 子智能体协作
主智能体可以调用子智能体执行具体任务：
- **烧录子智能体**: 专注于固件下载
- **串口子智能体**: 专注于数据监控和解析
- **调试子智能体**: 专注于寄存器读取和故障分析

## 硬件连接参考

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

### ESP32 连接
```
USB-TTL               ESP32
  TX      ──────────→ GPIO3 (RX)
  RX      ←────────── GPIO1 (TX)
  GND     ─────────── GND
  GPIO0   ─────────── GND (进入下载模式)
```

## 命令参考

### 串口操作
```python
# 列出可用串口
ports = list_serial_ports()

# 打开串口监控
monitor = open_serial(port="COM9", baud=115200)

# 读取数据
data = read_serial(monitor, timeout=3)

# 等待特定字符串
data = wait_for_serial(monitor, keyword="BOOT", timeout=5)

# 关闭串口
close_serial(monitor)
```

### 烧录操作
```python
# 检测调试探针
probes = list_debug_probes()

# SWD 烧录
result = flash_swd("firmware.bin", chip="STM32F103C8")

# UART ISP 烧录
result = flash_uart("firmware.bin", port="COM9")
```

### 编译操作
```python
# 编译代码
result = compile_stm32("main.c", chip="STM32F103C8")

# 检查工具链
status = check_toolchain()
```

### 调试操作
```python
# 连接 SWD
connect = connect_swd(chip="STM32F103C8")

# 读取寄存器
regs = read_registers(names=["PC", "SP", "SCB_CFSR"])

# 分析故障
fault = analyze_fault(regs)
```

## 支持的芯片

### STM32 系列
- STM32F0: F030F4, F030C8, F072RB
- STM32F1: F103C8T6, F103CB, F103RC, F103RE
- STM32F3: F303CC, F303RE
- STM32F4: F401CC, F407VE, F411CE, F429ZI

### ESP32 系列
- ESP32, ESP32-S2, ESP32-S3, ESP32-C3

### RP2040 系列
- RP2040, Raspberry Pi Pico

## 注意事项

1. **权限问题**: Linux 下可能需要 `sudo usermod -aG dialout $USER`
2. **驱动安装**: Windows 下需要安装 CH340/CP2102 驱动
3. **BOOT0 引脚**: UART ISP 烧录时需要拉高 BOOT0
4. **波特率**: 串口监控默认 115200，可根据设备调整
5. **超时设置**: 根据设备启动时间调整等待超时

## 集成示例

```python
# 完整工作流示例
def develop_and_test():
    # 1. 编译
    compile_result = compile_code("main.c", chip="STM32F103C8")
    if not compile_result["success"]:
        return f"编译失败: {compile_result['error']}"
    
    # 2. 烧录
    flash_result = flash_firmware(compile_result["bin_path"])
    if not flash_result["success"]:
        return f"烧录失败: {flash_result['error']}"
    
    # 3. 监控验证
    monitor = open_serial(port="COM9", baud=115200)
    output = wait_for_serial(monitor, keyword="Hello", timeout=5)
    close_serial(monitor)
    
    if "Hello" in output:
        return "程序运行成功"
    else:
        # 4. 调试
        connect_swd(chip="STM32F103C8")
        regs = read_registers()
        fault = analyze_fault(regs)
        return f"程序未正常运行，故障分析: {fault}"
```