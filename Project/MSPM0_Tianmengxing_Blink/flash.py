#!/usr/bin/env python3
"""将 MSPM0 天猛星 LED 闪烁固件烧录到开发板。

对应 ESP32_S3LED/flash.py 的角色：调用 MCU-CLI 的 flash_mspm0，
把 CCS 工程（或直接 .out）通过 SEGGER J-Link 下载到 MSPM0G3507。

本项目专属信息（探针序列号、CCS 工程路径、板子硬件描述）全部从同目录的
board.json 读取——通用框架代码 mcucli/ 不含任何此类信息（开源约定）。

用法:
    python flash.py                      # 烧录 board.json 里 ccs_project 指定的工程
    python flash.py --verify             # 烧录并验证 PC 寄存器
    python flash.py --build              # 先 gmake 编译再烧录
    python flash.py --dry-run            # 只打印 J-Link 命令不执行
    python flash.py --serial <SN>        # 覆盖 board.json 里的探针序列号
    python flash.py path/to/firmware.out # 直接烧录指定 .out（覆盖工程目录）
"""

import sys
import json
import argparse
from pathlib import Path

# 支持 mcucli 已安装（pip install -e .）或开发模式（直接 clone 跑）
SCRIPT_DIR = Path(__file__).resolve().parent
try:
    import mcucli  # noqa: F401
except ImportError:
    # 开发模式：把仓库根加入 path
    REPO_ROOT = SCRIPT_DIR.parent.parent.parent
    sys.path.insert(0, str(REPO_ROOT))

BOARD_JSON = SCRIPT_DIR / "board.json"


def load_board_config() -> dict:
    """读取本项目专属硬件配置（board.json）。"""
    if not BOARD_JSON.exists():
        print(f"找不到项目配置: {BOARD_JSON}", file=sys.stderr)
        sys.exit(2)
    return json.loads(BOARD_JSON.read_text(encoding="utf-8"))


def build_parser(default_target: str, default_serial: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="MSPM0 天猛星 LED 闪烁固件烧录脚本（调用 MCU-CLI flash_mspm0）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("target", nargs="?", default=default_target,
                   help=f"烧录目标：.out 文件或 CCS 工程目录（默认来自 board.json: {default_target}）")
    p.add_argument("--serial", default=default_serial,
                   help=f"J-Link 探针序列号（默认来自 board.json: {default_serial or '(空, auto-fallback)'}）")
    p.add_argument("--device", default="", help="目标器件（默认 MSPM0G3507）")
    p.add_argument("--build", action="store_true", help="先 gmake 编译再烧录")
    p.add_argument("--verify", action="store_true", help="烧录后验证 PC 寄存器")
    p.add_argument("--dry-run", action="store_true", help="只打印 J-Link 命令不执行")
    return p


def main() -> int:
    board = load_board_config()
    default_target = board.get("ccs_project", "")
    default_serial = board.get("probe", {}).get("serial", "")

    args = build_parser(default_target, default_serial).parse_args()

    if not args.target:
        print("board.json 未指定 ccs_project，且命令行未给出 target", file=sys.stderr)
        return 1

    try:
        from mcucli.scripts.flash_tool import flash_mspm0
    except ImportError as e:
        print(f"无法导入 flash_mspm0，请先 pip install -e . 安装 MCU-CLI: {e}", file=sys.stderr)
        return 1

    result = flash_mspm0(
        path=args.target,
        device=args.device,
        serial=args.serial,
        build=args.build,
        verify=args.verify,
        dry_run=args.dry_run,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result.get("success"):
        msg = result.get("message", "OK")
        if result.get("verify_pc"):
            msg += f" | verify_pc={result['verify_pc']}"
        if result.get("fallback"):
            msg += f" | {result['fallback']}"
        print(f"\n[OK] {msg}")
        if not args.dry_run:
            led = board.get("led", {})
            print(f"天猛星板载 LED ({led.get('port','GPIOB')}.{led.get('pin',22)}) 应该正在闪烁（5 秒周期）。")
        return 0
    else:
        print(f"\n[FAIL] 烧录失败: {result.get('error', '未知错误')}", file=sys.stderr)
        if result.get("output"):
            print("--- J-Link 输出 ---", file=sys.stderr)
            print(result["output"][-1500:], file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
