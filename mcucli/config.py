"""
STM32 Agent 配置文件（云端优先）

说明：
1. server.py + compiler.py 依赖本文件中的服务器/编译配置。
2. 客户端硬件配置已迁移到 client/client_config.py。
3. 下面保留的少量“单机遗留参数”仅用于兼容旧版 stm32_agent.py 参考运行。
"""

import os
from pathlib import Path

# ================= 网络代理 =================
# 默认不强制代理。Google/OpenAI 这类海外接口在当前网络环境下可能需要代理；
# 需要时再填入 URL，或在启动前导出环境变量。
HTTP_PROXY_URL = ""
HTTPS_PROXY_URL = ""
GRPC_PROXY_URL = ""
_LEGACY_DEFAULT_PROXY_URLS = {
    "http://127.0.0.1:7890",
    "http://localhost:7890",
}


def _apply_optional_proxy(env_name: str, configured_value: str) -> None:
    """Only export proxy variables when the user explicitly configured them."""

    value = (configured_value or "").strip()
    if value:
        os.environ[env_name] = value
        return
    current = (os.environ.get(env_name) or "").strip()
    if current in _LEGACY_DEFAULT_PROXY_URLS:
        os.environ.pop(env_name, None)


_apply_optional_proxy("HTTP_PROXY", HTTP_PROXY_URL)
_apply_optional_proxy("HTTPS_PROXY", HTTPS_PROXY_URL or HTTP_PROXY_URL)
_apply_optional_proxy("GRPC_PROXY_EXP", GRPC_PROXY_URL or HTTPS_PROXY_URL or HTTP_PROXY_URL)

AI_TEMPERATURE = 1  # 低温度保证代码稳定性

# ================= 编译工具链 =================
ARM_GCC = "arm-none-eabi-gcc"
ARM_OBJCOPY = "arm-none-eabi-objcopy"
ARM_AR = "arm-none-eabi-ar"
ARM_SIZE = "arm-none-eabi-size"

# ================= 目录结构 =================
BASE_DIR = Path(__file__).parent
WORKSPACE = BASE_DIR / "workspace"
BUILD_DIR = WORKSPACE / "build"
PROJECTS_DIR = WORKSPACE / "projects"
HAL_DIR = WORKSPACE / "hal"
RTOS_DIR = WORKSPACE / "rtos"

# ================= 调试参数 =================
MAX_DEBUG_ATTEMPTS = 5
REGISTER_READ_DELAY = 0.3  # 读寄存器前等待时间（秒）
POST_FLASH_DELAY = 1.5  # 烧录后等待程序启动时间（秒）
UART_READ_TIMEOUT = 3  # 串口读取超时（秒）

# ================= 默认目标芯片 =================
DEFAULT_CHIP = "STM32F103C8T6"
DEFAULT_CLOCK = "HSI_internal"

# ================= TI MSPM0 烧录（SEGGER J-Link）=================
# 通用框架默认值：仅保留芯片级通用配置，不含任何特定板/特定用户的硬件信息
# （探针序列号、特定工程路径、个人安装路径等由调用方传入或放在 Project/<项目>/ 下）
#
# J-Link Commander 命令序列：r / h / loadfile "<.out>" / r / g / exit
# MSPM0 flash 基址为 0x00000000（J-Link loadfile 自动解析 .out 段地址，无需手动指定）
MSPM0_DEFAULT_DEVICE = "MSPM0G3507"          # MCU 型号（芯片级通用）
MSPM0_DEFAULT_INTERFACE = "SWD"              # J-Link 调试接口（通用）
MSPM0_DEFAULT_SPEED = 4000                   # kHz（MSPM0 通用稳定速率）
# 注意：不设 MSPM0_DEFAULT_SERIAL。探针序列号由调用方传入，
# 或运行时通过 JLink.exe ShowEmuList 枚举在线探针自动选择（见 flash_mspm0 auto-fallback）。

# SEGGER J-Link 安装位置探测顺序（resolve_jlink_path 按此查找）：
# 1) 注册表 HKLM/HKCU\SOFTWARE\SEGGER\J-Link\InstallPath 下的 JLink.exe
# 2) PATH 中的 JLink.exe
# 3) 下列标准安装目录兜底（仅含 SEGGER 官方默认安装路径，不含任何个人路径）
JLINK_INSTALL_CANDIDATES = [
    r"C:\Program Files\SEGGER\JLink\JLink.exe",
    r"C:\Program Files (x86)\SEGGER\JLink\JLink.exe",
]

# TI Code Composer Studio 构建工具（gmake）探测顺序：
# 1) PATH 中的 gmake.exe
# 2) 下列标准 CCS 安装目录兜底（C:\ti 下按版本号通配，不含任何个人路径）
CCS_GMAKE_CANDIDATES = [
    r"C:\ti\ccs\ccs\utils\bin\gmake.exe",
]
# 注：CCS 工作区/工程路径属于项目专属信息，不在通用 config 中。
# 各 MSPM0 项目的工程路径放在 Project/<项目名>/board.json 或由调用方传入。
