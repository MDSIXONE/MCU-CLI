#!/usr/bin/env python3
"""编译工具 - 支持 STM32 GCC 交叉编译"""

import sys
import os
import subprocess
import argparse
import json
from typing import Optional, List, Dict, Any
from pathlib import Path

# 默认工具链路径
ARM_GCC = "arm-none-eabi-gcc"
ARM_OBJCOPY = "arm-none-eabi-objcopy"
ARM_SIZE = "arm-none-eabi-size"
BUILD_DIR = Path("build")

def check_toolchain() -> Dict[str, Any]:
    """检查工具链是否安装"""
    result = {
        "gcc": False,
        "gcc_version": "",
        "objcopy": False,
        "size": False
    }
    
    # 检查 GCC
    try:
        proc = subprocess.run([ARM_GCC, "--version"], 
                            capture_output=True, text=True, timeout=5)
        if proc.returncode == 0:
            result["gcc"] = True
            result["gcc_version"] = proc.stdout.split("\n")[0]
    except:
        pass
    
    # 检查 objcopy
    try:
        proc = subprocess.run([ARM_OBJCOPY, "--version"], 
                            capture_output=True, text=True, timeout=5)
        if proc.returncode == 0:
            result["objcopy"] = True
    except:
        pass
    
    # 检查 size
    try:
        proc = subprocess.run([ARM_SIZE, "--version"], 
                            capture_output=True, text=True, timeout=5)
        if proc.returncode == 0:
            result["size"] = True
    except:
        pass
    
    return result

def compile_stm32(source_path: str, chip: str = "STM32F103C8", 
                  use_hal: bool = True) -> Dict[str, Any]:
    """编译 STM32 代码"""
    source = Path(source_path)
    if not source.exists():
        return {"success": False, "error": f"源文件不存在: {source}"}
    
    BUILD_DIR.mkdir(exist_ok=True)
    
    # 芯片信息
    chip_info = {
        "STM32F103C8": {"cpu": "cortex-m3", "flash_k": 64, "ram_k": 20, "define": "STM32F103xB"},
        "STM32F103CB": {"cpu": "cortex-m3", "flash_k": 128, "ram_k": 20, "define": "STM32F103xB"},
        "STM32F407VE": {"cpu": "cortex-m4", "flash_k": 512, "ram_k": 128, "define": "STM32F407xx"},
        "STM32F411CE": {"cpu": "cortex-m4", "flash_k": 512, "ram_k": 128, "define": "STM32F411xE"},
    }
    
    ci = chip_info.get(chip, chip_info["STM32F103C8"])
    
    # 生成链接脚本
    linker_script = f"""MEMORY {{
  FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = {ci['flash_k']}K
  RAM   (xrw) : ORIGIN = 0x20000000, LENGTH = {ci['ram_k']}K
}}
_estack = ORIGIN(RAM) + LENGTH(RAM);
_Min_Heap_Size = 0x200;
_Min_Stack_Size = 0x400;
SECTIONS {{
  .isr_vector : {{ KEEP(*(.isr_vector)) }} >FLASH
  .text : {{ *(.text*) *(.rodata*) . = ALIGN(4); _etext = .; }} >FLASH
  .init : {{ KEEP(*(.init)) }} >FLASH
  .fini : {{ KEEP(*(.fini)) }} >FLASH
  .init_array : {{ KEEP(*(.init_array*)) }} >FLASH
  .fini_array : {{ KEEP(*(.fini_array*)) }} >FLASH
  .data : AT(_etext) {{ _sdata = .; *(.data*) . = ALIGN(4); _edata = .; }} >RAM
  .bss : {{ _sbss = .; *(.bss*) *(COMMON) . = ALIGN(4); _ebss = .; end = _ebss; }} >RAM
  ._user_heap_stack : {{ . = ALIGN(8); . = . + _Min_Heap_Size; . = . + _Min_Stack_Size; . = ALIGN(8); }} >RAM
  /DISCARD/ : {{ *(.ARM.*) }}
}}
"""
    
    linker_path = BUILD_DIR / "link.ld"
    linker_path.write_text(linker_script)
    
    # 编译命令
    elf_path = BUILD_DIR / "firmware.elf"
    bin_path = BUILD_DIR / "firmware.bin"
    
    cmd = [
        ARM_GCC,
        f"-mcpu={ci['cpu']}",
        "-mthumb",
        f"-D{ci['define']}",
        "-Os",
        "-Wall",
        "-ffunction-sections",
        "-fdata-sections",
        f"-T{linker_path}",
        "-Wl,--gc-sections",
        str(source),
        "-o", str(elf_path),
        "-nostartfiles",
        "-lc", "-lm", "-lnosys"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            # 生成二进制文件
            subprocess.run([ARM_OBJCOPY, "-O", "binary", str(elf_path), str(bin_path)])
            
            # 获取大小
            size_result = subprocess.run([ARM_SIZE, str(elf_path)], 
                                       capture_output=True, text=True)
            
            return {
                "success": True,
                "bin_path": str(bin_path),
                "elf_path": str(elf_path),
                "size_output": size_result.stdout if size_result.returncode == 0 else "",
                "message": f"编译成功"
            }
        else:
            return {
                "success": False,
                "error": result.stderr[:1000] if result.stderr else "编译失败"
            }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "编译超时"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def compile_esp32(source_path: str, board: str = "esp32") -> Dict[str, Any]:
    """编译 ESP32 MicroPython 代码"""
    source = Path(source_path)
    if not source.exists():
        return {"success": False, "error": f"源文件不存在: {source}"}
    
    # ESP32 MicroPython 验证
    try:
        import ast
        code = source.read_text(encoding='utf-8')
        ast.parse(code)
        return {
            "success": True,
            "message": "MicroPython 语法检查通过",
            "board": board
        }
    except SyntaxError as e:
        return {
            "success": False,
            "error": f"语法错误: {e}"
        }

def flash_esp32(source_path: str, port: str = "COM9", 
                baud: int = 115200) -> Dict[str, Any]:
    """烧录 ESP32 MicroPython 代码"""
    source = Path(source_path)
    if not source.exists():
        return {"success": False, "error": f"源文件不存在: {source}"}
    
    # 使用 ampy 或 esptool
    try:
        # 尝试使用 ampy
        cmd = ["ampy", "--port", port, "--baud", str(baud), "put", str(source), "main.py"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return {
                "success": True,
                "message": f"ESP32 代码已上传到 {port}"
            }
        else:
            return {
                "success": False,
                "error": result.stderr or "上传失败"
            }
    except FileNotFoundError:
        return {"success": False, "error": "ampy 未安装，请运行: pip install adafruit-ampy"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="编译工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 检查工具链
    subparsers.add_parser("check", help="检查工具链")
    
    # 编译 STM32
    stm32_parser = subparsers.add_parser("compile-stm32", help="编译 STM32 代码")
    stm32_parser.add_argument("source", help="源文件路径")
    stm32_parser.add_argument("--chip", default="STM32F103C8", help="芯片型号")
    
    # 编译 ESP32
    esp32_parser = subparsers.add_parser("compile-esp32", help="编译 ESP32 代码")
    esp32_parser.add_argument("source", help="源文件路径")
    esp32_parser.add_argument("--board", default="esp32", help="开发板型号")
    
    # 烧录 ESP32
    flash_esp32_parser = subparsers.add_parser("flash-esp32", help="烧录 ESP32 代码")
    flash_esp32_parser.add_argument("source", help="源文件路径")
    flash_esp32_parser.add_argument("--port", default="COM9", help="串口端口")
    flash_esp32_parser.add_argument("--baud", type=int, default=115200, help="波特率")
    
    args = parser.parse_args()
    
    if args.command == "check":
        result = check_toolchain()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "compile-stm32":
        result = compile_stm32(args.source, args.chip)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "compile-esp32":
        result = compile_esp32(args.source, args.board)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "flash-esp32":
        result = flash_esp32(args.source, args.port, args.baud)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()