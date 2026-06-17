# MCU-CLI

跨平台嵌入式开发命令行工具集，统一封装 **STM32 / TI MSPM0 / ESP32 / RP2040** 等芯片的烧录、串口监控、编译与调试操作。

所有硬件相关命令返回结构化 JSON，便于脚本化与自动化集成。

**将 mcucli 作为项目技能加载（AI 辅助开发）：**

在项目的 `AGENTS.md` 或配置文件中声明使用 `.agent/skills/mcucli/` 目录下的技能，或在会话开始时加载：

```python
skill("mcucli")
```

---

## 目录

- [特性](#特性)
- [环境要求](#环境要求)
- [快速部署](#快速部署)
- [外部工具安装（按芯片选装）](#外部工具安装按芯片选装)
- [命令参考](#命令参考)
- [项目结构](#项目结构)
- [项目隔离约定](#项目隔离约定)
- [配置说明](#配置说明)
- [示例项目](#示例项目)
- [常见问题](#常见问题)
- [许可证](#许可证)

---

## 特性

- **统一 CLI**：`serial` / `flash` / `compile` / `connect` / `regs` / `reset` 六大子命令，覆盖嵌入式开发主流程
- **多芯片烧录**：
  - STM32 —— pyOCD（SWD）
  - STM32 —— stm32loader（UART ISP，需 BOOT0 拉高）
  - TI MSPM0 —— SEGGER J-Link Commander（支持 `.out` 固件或 CCS 工程目录，可选 `--build` 先编译）
  - ESP32 / RP2040 —— MicroPython 文件上传
- **结构化输出**：所有命令返回 JSON，方便管道与自动化
- **开源洁净**：通用框架代码不含任何个人硬件信息（探针序列号、个人安装路径等），所需信息一律动态发现或由调用方传入
- **项目隔离**：单次项目的固件、板级配置、烧录脚本统一放在 `Project/<项目名>/`，不污染通用框架

---

## 环境要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows / Linux / macOS |
| Python | >= 3.8 |
| Python 包 | `pyserial`、`pyocd`（必需） |

各芯片的烧录/编译还需对应的外部工具，见 [外部工具安装](#外部工具安装按芯片选装)。

> **Linux 权限提示**：访问串口与调试探针需将用户加入 `dialout` / `plugdev` 组，否则要 `sudo`。
> ```bash
> sudo usermod -aG dialout,plugdev $USER
> # 重新登录后生效
> ```

---

## 快速部署

```bash
# 1. 克隆仓库
git clone <your-repo-url> MCU-CLI
cd MCU-CLI

# 2. 安装（editable 模式，注册 mcucli 命令到 PATH）
pip install -e .

# 3. 验证安装 —— 列出本机串口
mcucli serial list
```

看到串口列表的 JSON 输出即部署成功。`pip install -e .` 会安装核心依赖（`pyocd`、`pyserial`）并注册 `mcucli` 命令。

**可选 extras**（按需安装）：

```bash
pip install -e ".[uart]"     # 额外装 stm32loader（STM32 UART ISP 烧录）
pip install -e ".[esp32]"    # 额外装 adafruit-ampy（ESP32 MicroPython 上传）
pip install -e ".[uart,esp32]"  # 全装
pip install -e ".[dev]"      # 开发依赖（pytest）
```

> 要求 Python ≥ 3.10。

### 关于 `mcucli/gary_setup.py`

`mcucli/gary_setup.py`（原名 `setup.py`）是历史遗留的全功能环境引导脚本（来自上层 Gary Dev Agent 项目，含 AI 接口配置、SearXNG、HAL 库下载等），**与 MCU-CLI 的烧录/串口/编译功能无关**，已重命名以避免与打包脚本混淆。部署 MCU-CLI **不需要**运行它。MCU-CLI 的打包定义在仓库根的 `pyproject.toml`。

---

## 外部工具安装（按芯片选装）

按你要用的芯片选装，互不依赖。

### STM32 —— SWD 烧录（pyOCD）

`pyocd` 已在核心依赖中（`pip install -e .` 自动安装）。首次使用需安装目标芯片的支持包：

```bash
# 安装 STM32F1 支持包
pyocd pack install stm32f103c8

# 列出已安装与可用的目标
pyocd list --targets
```

常用探针：ST-Link V2/V3、CMSIS-DAP、J-Link。

### STM32 —— UART ISP 烧录（stm32loader）

```bash
pip install -e ".[uart]"   # 安装核心依赖 + stm32loader
# 或单独装：pip install stm32loader
```

烧录时需将目标板 BOOT0 拉高进入 ISP 模式。

### TI MSPM0 —— SEGGER J-Link 烧录

1. 从 [segger.com](https://www.segger.com/downloads/jlink/) 下载并安装 **J-Link Software and Documentation Pack**（含 `JLink.exe`）。
2. 安装后 `JLink.exe` 会进入 PATH，或在注册表 `HKLM\SOFTWARE\SEGGER\J-Link\InstallPath` 中登记。
3. MCU-CLI 会按 **注册表 → PATH → 标准安装目录** 的顺序自动定位，无需手动配置路径。

`flash mspm0` 无需手动指定探针序列号：若默认序列号在 USB 上找不到探针，会自动调用 `JLink.exe ShowEmuList` 枚举在线探针并重试（auto-fallback）。

### TI MSPM0 —— 编译 CCS 工程（可选）

仅当使用 `flash mspm0 <工程目录> --build` 时需要。安装 **TI Code Composer Studio** 后，`gmake` 会在 `C:\ti\ccs\...\utils\bin\` 下，MCU-CLI 会从 PATH 与标准目录自动定位。

### STM32 —— 编译（arm-none-eabi-gcc）

```bash
# Linux (Debian/Ubuntu)
sudo apt install gcc-arm-none-eabi

# macOS
brew install arm-none-eabi-gcc

# Windows
winget install Arm.GnuArmEmbeddedToolchain
```

`compile check` 可检测工具链是否就绪。

### ESP32 —— MicroPython 文件上传（可选）

```bash
pip install -e ".[esp32]"   # 安装核心依赖 + adafruit-ampy
# 或单独装：pip install adafruit-ampy
```

---

## 命令参考

所有命令在 `pip install -e .` 后直接用 `mcucli <子命令> ...`（未安装时可用 `python -m mcucli.mcucli <子命令> ...`）：

### serial —— 串口工具

```bash
# 列出所有串口
mcucli serial list

# 读取串口（默认 115200，超时 3s）
mcucli serial read COM9
mcucli serial read COM9 --baud 9600 --timeout 5

# 持续监控（默认 10s）
mcucli serial monitor COM9 --duration 30

# 发送数据
mcucli serial send COM9 "print('Hello')"
```

### flash —— 烧录工具

```bash
# 列出调试探针
mcucli flash list

# SWD 烧录（STM32，经 pyOCD）
mcucli flash swd firmware.bin
mcucli flash swd firmware.bin --chip STM32F411CE

# UART ISP 烧录（STM32，经 stm32loader，需 BOOT0 拉高）
mcucli flash uart firmware.bin --port COM9

# TI MSPM0 经 J-Link 烧录
mcucli flash mspm0 firmware.out              # 直接烧 .out
mcucli flash mspm0 /path/to/ccs_project      # 自动定位工程内最新 .out
mcucli flash mspm0 /path/to/ccs_project --build --verify   # 先编译再烧录并验证
mcucli flash mspm0 firmware.out --dry-run    # 只打印 JLink 命令不执行
mcucli flash mspm0 firmware.out --serial 123456789          # 多探针时指定序列号
mcucli flash mspm0 firmware.out --device MSPM0G3507 --speed 4000
```

| 选项 | 说明 |
|------|------|
| `--device` | 目标器件（默认 `MSPM0G3507`） |
| `--interface` | 调试接口（默认 `SWD`） |
| `--speed` | 速率 kHz（默认 `4000`） |
| `--serial` | J-Link 序列号，多探针时指定；省略则 auto-fallback |
| `--build` | 先用 gmake 编译 CCS 工程再烧录 |
| `--verify` | 烧录后读取 PC 寄存器验证程序已运行 |
| `--dry-run` | 只打印 JLink 命令与 .out 路径，不执行 |

### compile —— 编译工具

```bash
# 编译 STM32（arm-none-eabi-gcc）
mcucli compile stm32 main.c
mcucli compile stm32 main.c --chip STM32F407VE

# 验证 ESP32 MicroPython 代码语法
mcucli compile esp32 main.py

# 检查工具链是否就绪
mcucli compile check
```

### connect / regs / reset —— 调试

```bash
# 连接设备（swd / uart / mspm0）
mcucli connect --chip STM32F103C8 --method swd
mcucli connect --method mspm0

# 寄存器操作（需先 connect）
mcucli regs read
mcucli regs write PC 0x08001000

# 复位设备
mcucli reset
```

---

## 项目结构

```
MCU-CLI/
├── LICENSE                        # Apache-2.0
├── README.md                      # 本文件
├── pyproject.toml                 # 打包配置（pip install -e . 入口）
├── .gitignore
├── mcucli/                        # 主程序包（通用框架，不含个人硬件信息）
│   ├── __init__.py                #   包入口（版本号）
│   ├── mcucli.py                  # CLI 入口
│   ├── config.py                  # 通用配置（仅芯片级默认值）
│   ├── gary_setup.py              # 历史遗留环境脚本（非打包用，勿运行）
│   ├── requirements.txt           # Python 依赖（兼容旧用法，推荐用 pyproject.toml）
│   ├── scripts/                   # 工具脚本层
│   │   ├── flash_tool.py          #   烧录：flash_swd / flash_uart / flash_mspm0
│   │   ├── compile_tool.py        #   编译
│   │   ├── serial_monitor.py      #   串口
│   │   └── hardware_connect.py    #   连接
│   ├── hardware/                  # 硬件抽象层
│   │   ├── swd.py                 #   pyOCD 桥（STM32）
│   │   ├── mspm0.py               #   J-Link 桥（MSPM0）
│   │   ├── uart_isp.py            #   UART ISP
│   │   ├── serial_mon.py          #   串口
│   │   └── micropython.py         #   MicroPython
│   └── compiler/                  # 编译器层（@register 自动加载）
│       ├── registry.py
│       ├── base.py
│       └── chips/
├── Project/                       # 项目任务目录（项目隔离）
│   ├── README.md                  #   任务管理说明
│   ├── TASK_TEMPLATE.md           #   任务模板
│   ├── ESP32_S3LED/               #   示例：ESP32 MicroPython LED
│   └── MSPM0_Tianmengxing_Blink/ #   示例：TI MSPM0 C 工程 LED 闪烁
└── .agent/skills/mcucli/          # 技能文档（脚本镜像 + 参考）
    ├── SKILL.md
    ├── scripts/                   #   与 mcucli/scripts/ 字节级同步
    └── references/
```

---

## 项目隔离约定

**单次项目相关的所有文件一律放在 `Project/<项目名>/`，不污染通用框架 `mcucli/`。**

每个项目目录的标准内容：

| 文件 | 说明 |
|------|------|
| `TASK.md` | 任务记录（按 `Project/TASK_TEMPLATE.md` 填写） |
| 固件源码 | `.c` / `.h` / `.py` 等（C 工程含 main + 板级配置 + 启动文件 + 链接脚本） |
| `flash.py` | 项目烧录入口脚本（调用 `mcucli` 的烧录函数，读取本项目 `board.json`） |
| `board.json` | **板级专属配置**（探针序列号、CCS 工程路径、引脚定义等） |

### `board.json` 示例

```json
{
  "board": "<开发板名称>",
  "device": "MSPM0G3507",
  "interface": "SWD",
  "speed": 4000,
  "serial": "",
  "ccs_project": "<本机 CCS 工程绝对路径>",
  "notes": "serial 留空时 flash_mspm0 会自动枚举在线 J-Link 探针"
}
```

`board.json` 属于项目专属文件，可含个人硬件信息；通用框架 `mcucli/` 不得含此类信息。
作为开源示例提交的 `board.json` 应使用占位符，使用者按自身环境填写。

### 创建新项目

```bash
mkdir Project/STM32_Motor
cp Project/TASK_TEMPLATE.md Project/STM32_Motor/TASK.md
# 编辑 TASK.md，添加固件源码与 flash.py
```

项目命名规范：`芯片型号_功能描述`，全大写加下划线，如 `ESP32_S3LED`、`STM32_Motor`。

---

## 配置说明

`mcucli/config.py` 只包含**芯片级通用默认值**，不含任何个人硬件信息：

- 芯片默认值：`DEFAULT_CHIP`、`MSPM0_DEFAULT_DEVICE`（`MSPM0G3507`）、接口（`SWD`）、速率（`4000`）
- 工具发现路径：仅含官方标准安装目录（如 `C:\Program Files\SEGGER\...`、`C:\ti\ccs\...`），无个人路径

**动态发现机制**（开源项目该有的能力，不依赖任何硬编码个人路径）：

| 工具 | 发现顺序 |
|------|----------|
| `JLink.exe` | 注册表 `HKLM/HKCU\SOFTWARE\SEGGER\J-Link\InstallPath` → PATH → 标准安装目录 |
| `gmake` | PATH → `C:\ti\ccs\...` 标准目录 |
| J-Link 探针序列号 | 调用方传入 → `board.json` → `JLink.exe ShowEmuList` 实时枚举（auto-fallback） |

如需覆盖默认芯片，可编辑 `mcucli/config.py` 中的 `DEFAULT_CHIP`，或通过命令行 `--chip` / `--device` 指定。

---

## 示例项目

### `Project/ESP32_S3LED/` —— ESP32 MicroPython LED

MicroPython 固件，`blink.py` + `flash.py` + `TASK.md`。

### `Project/MSPM0_Tianmengxing_Blink/` —— TI MSPM0 LED 闪烁

C 裸金属工程（天猛星 MSPM0G3507 开发板），含：
- `empty_non_sysconfig.c` —— main（LED 翻转 + UART 打印）
- `ti_msp_dl_config.c/.h` —— SysConfig 板级初始化
- `startup_mspm0g350x_ticlang.c` —— 启动文件
- `mspm0g3507.cmd` —— 链接器脚本
- `board.json` —— 板级专属配置
- `flash.py` —— 烧录入口

```bash
# 烧录（serial 从 board.json 读取，auto-fallback 到在线探针）
python Project/MSPM0_Tianmengxing_Blink/flash.py --verify

# 先编译再烧录
python Project/MSPM0_Tianmengxing_Blink/flash.py --build --verify
```

---

## 常见问题

**Q: 烧录 STM32 报 "No debug probe found"？**
确认探针 USB 已连接、驱动已装（ST-Link 需 ST 官方驱动，CMSIS-DAP 通常免驱）。Linux 下检查用户是否在 `dialout`/`plugdev` 组。

**Q: MSPM0 烧录报 "Connecting to J-Link ...FAILED"？**
J-Link 探针序列号不匹配。`flash mspm0` 会自动枚举在线探针重试；若仍失败，用 `mcucli flash list` 查看在线探针，或 `--serial <序列号>` 显式指定。

**Q: Windows 下中文帮助/输出乱码？**
终端编码问题，不影响功能。在 PowerShell 执行 `chcp 65001` 切换 UTF-8，或用 `PYTHONIOENCODING=utf-8 mcucli ...`。

**Q: `serial` 没有 `reset` 子命令？**
REPL 重置通过 `serial send` 发送 Ctrl-C 实现。如需硬件复位，用 `reset` 命令（经调试探针）。

**Q: 如何贡献新的芯片支持？**
- 烧录：在 `hardware/` 新增桥接类（参考 `swd.py` / `mspm0.py`），在 `scripts/flash_tool.py` 新增 `flash_<chip>()` 函数，在 `mcucli.py` 新增 `flash` 子命令
- 编译：在 `compiler/chips/` 新增芯片模块，用 `@register` 自动加载

---

## 许可证

[Apache License 2.0](./LICENSE)
