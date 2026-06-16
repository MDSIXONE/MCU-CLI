#!/usr/bin/env python3
"""烧录工具 - 支持 SWD 和 UART ISP 烧录"""

import sys
import os
import time
import argparse
import json
import subprocess
from typing import Optional, List, Dict, Any
from pathlib import Path

def list_debug_probes() -> List[Dict[str, Any]]:
    """列出所有调试探针"""
    try:
        from pyocd.probe.aggregator import DebugProbeAggregator
        probes = DebugProbeAggregator.get_all_connected_probes()
        return [{"uid": probe.unique_id, "description": probe.product_name} 
                for probe in probes]
    except ImportError:
        return [{"error": "pyocd 未安装，请运行: pip install pyocd"}]
    except Exception as e:
        return [{"error": str(e)}]

def connect_swd(chip: str = "STM32F103C8") -> Dict[str, Any]:
    """连接 SWD 探针"""
    try:
        from pyocd.core.helpers import ConnectHelper
        from pyocd.flash.file_programmer import FileProgrammer
        
        # 尝试连接
        session = ConnectHelper.session_with_chosen_probe(
            target_override=chip.lower(),
            auto_unlock=True,
            connect_mode="halt",
            blocking=False,
            return_first=True,
            options={"frequency": 1000000}
        )
        
        if session is None:
            return {"success": False, "error": "未找到调试探针"}
        
        session.open()
        target = session.board.target
        
        return {
            "success": True,
            "chip": chip,
            "probe": session.board.description,
            "message": f"已连接: {chip}"
        }
    except ImportError:
        return {"success": False, "error": "pyocd 未安装"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def flash_swd(bin_path: str, chip: str = "STM32F103C8") -> Dict[str, Any]:
    """通过 SWD 烧录固件"""
    try:
        from pyocd.core.helpers import ConnectHelper
        from pyocd.flash.file_programmer import FileProgrammer
        
        if not os.path.exists(bin_path):
            return {"success": False, "error": f"文件不存在: {bin_path}"}
        
        # 连接探针
        session = ConnectHelper.session_with_chosen_probe(
            target_override=chip.lower(),
            auto_unlock=True,
            connect_mode="halt",
            blocking=False,
            return_first=True,
            options={"frequency": 1000000}
        )
        
        if session is None:
            return {"success": False, "error": "未找到调试探针"}
        
        session.open()
        target = session.board.target
        
        # 烧录
        size = os.path.getsize(bin_path)
        t0 = time.time()
        
        programmer = FileProgrammer(session)
        programmer.program(bin_path, base_address=0x08000000)
        
        dt = time.time() - t0
        speed = size / dt / 1024 if dt > 0 else 0
        
        # 复位并运行
        try:
            target.reset_and_halt()
            time.sleep(0.1)
            target.resume()
        except:
            pass
        
        session.close()
        
        return {
            "success": True,
            "size": size,
            "time": round(dt, 2),
            "speed": round(speed, 1),
            "message": f"烧录成功 {size}B / {dt:.1f}s ({speed:.1f} KB/s)"
        }
    except ImportError:
        return {"success": False, "error": "pyocd 未安装"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def flash_uart(bin_path: str, port: str = "COM9", baud: int = 115200) -> Dict[str, Any]:
    """通过 UART ISP 烧录固件"""
    try:
        if not os.path.exists(bin_path):
            return {"success": False, "error": f"文件不存在: {bin_path}"}
        
        # 使用 stm32loader 工具
        cmd = [
            "stm32loader",
            "-p", port,
            "-b", str(baud),
            "-w", "-v",
            bin_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            return {
                "success": True,
                "message": f"UART 烧录成功: {port}"
            }
        else:
            return {
                "success": False,
                "error": result.stderr or result.stdout
            }
    except FileNotFoundError:
        return {"success": False, "error": "stm32loader 未安装，请运行: pip install stm32loader"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def read_registers(names: Optional[List[str]] = None) -> Dict[str, Any]:
    """读取寄存器"""
    try:
        from pyocd.core.helpers import ConnectHelper
        
        session = ConnectHelper.session_with_chosen_probe(
            auto_unlock=True,
            connect_mode="halt",
            blocking=False,
            return_first=True
        )
        
        if session is None:
            return {"success": False, "error": "未找到调试探针"}
        
        session.open()
        target = session.board.target
        
        # 默认寄存器映射 (STM32F1)
        reg_map = {
            "R0": 0x20000000,
            "R1": 0x20000004,
            "R2": 0x20000008,
            "R3": 0x2000000C,
            "R4": 0x20000010,
            "R5": 0x20000014,
            "R6": 0x20000018,
            "R7": 0x2000001C,
            "R8": 0x20000020,
            "R9": 0x20000024,
            "R10": 0x20000028,
            "R11": 0x2000002C,
            "R12": 0x20000030,
            "SP": 0x20000034,
            "LR": 0x20000038,
            "PC": 0x2000003C,
            "SCB_CFSR": 0xE000ED28,
            "SCB_HFSR": 0x2000003C,
            "SCB_MMAR": 0x20000040,
            "SCB_BFAR": 0x20000044,
        }
        
        target_regs = names if names else ["PC", "SP", "LR", "SCB_CFSR"]
        result = {}
        
        for name in target_regs:
            if name in reg_map:
                try:
                    val = target.read32(reg_map[name])
                    result[name] = f"0x{val:08X}"
                except:
                    result[name] = "读取失败"
        
        # 读取 PC
        try:
            pc = target.read_core_register("pc")
            result["PC"] = f"0x{pc:08X}"
        except:
            pass
        
        session.close()
        
        return {
            "success": True,
            "registers": result
        }
    except ImportError:
        return {"success": False, "error": "pyocd 未安装"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def analyze_fault(regs: Dict[str, str]) -> str:
    """分析 HardFault"""
    cfsr_str = regs.get("SCB_CFSR", "0x00000000")
    try:
        cfsr = int(cfsr_str, 16)
    except ValueError:
        return "CFSR 格式错误"
    
    if cfsr == 0:
        return "无故障"
    
    checks = [
        (0x01, "IACCVIOL: 指令访问违规"),
        (0x02, "DACCVIOL: 数据访问违规"),
        (0x100, "IBUSERR: 指令总线错误"),
        (0x200, "PRECISERR: 精确总线错误（外设未使能时钟）"),
        (0x400, "IMPRECISERR: 非精确总线错误"),
        (0x10000, "UNDEFINSTR: 未定义指令"),
        (0x20000, "INVSTATE: 无效 EPSR 状态"),
        (0x1000000, "UNALIGNED: 非对齐访问"),
        (0x2000000, "DIVBYZERO: 除零"),
    ]
    
    faults = [desc for mask, desc in checks if cfsr & mask]
    return "; ".join(faults) if faults else f"未知故障 CFSR=0x{cfsr:08X}"

def main():
    parser = argparse.ArgumentParser(description="烧录工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 列出探针
    subparsers.add_parser("list-probes", help="列出调试探针")
    
    # SWD 烧录
    swd_parser = subparsers.add_parser("flash-swd", help="SWD 烧录")
    swd_parser.add_argument("bin_path", help="固件文件路径")
    swd_parser.add_argument("--chip", default="STM32F103C8", help="芯片型号")
    
    # UART 烧录
    uart_parser = subparsers.add_parser("flash-uart", help="UART ISP 烧录")
    uart_parser.add_argument("bin_path", help="固件文件路径")
    uart_parser.add_argument("--port", default="COM9", help="串口端口")
    uart_parser.add_argument("--baud", type=int, default=115200, help="波特率")
    
    # 读取寄存器
    reg_parser = subparsers.add_parser("read-regs", help="读取寄存器")
    reg_parser.add_argument("--names", nargs="+", help="寄存器名称列表")
    
    # 分析故障
    fault_parser = subparsers.add_parser("analyze-fault", help="分析 HardFault")
    fault_parser.add_argument("--cfsr", help="CFSR 值 (十六进制)")
    
    args = parser.parse_args()
    
    if args.command == "list-probes":
        result = list_debug_probes()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "flash-swd":
        result = flash_swd(args.bin_path, args.chip)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "flash-uart":
        result = flash_uart(args.bin_path, args.port, args.baud)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "read-regs":
        result = read_registers(args.names)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "analyze-fault":
        if args.cfsr:
            regs = {"SCB_CFSR": args.cfsr}
            result = analyze_fault(regs)
            print(json.dumps({"analysis": result}, indent=2, ensure_ascii=False))
        else:
            print("请提供 --cfsr 参数")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()