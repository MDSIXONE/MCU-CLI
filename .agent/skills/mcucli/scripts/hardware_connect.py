#!/usr/bin/env python3
"""硬件连接工具 - 支持 SWD 连接和寄存器读取"""

import sys
import os
import time
import argparse
import json
from typing import Optional, List, Dict, Any

def connect_hardware(chip: str = "STM32F103C8",
                     method: str = "swd") -> Dict[str, Any]:
    """连接硬件设备"""
    if method == "swd":
        return connect_swd(chip)
    elif method == "uart":
        return {"success": False, "error": "UART 连接需要指定端口"}
    elif method == "mspm0":
        return connect_mspm0(chip)
    else:
        return {"success": False, "error": f"不支持的连接方式: {method}"}

def connect_mspm0(chip: str = "MSPM0G3507") -> Dict[str, Any]:
    """通过 SEGGER J-Link 连接 TI MSPM0（天猛星开发板）"""
    try:
        from mcucli.scripts.flash_tool import resolve_jlink_path
        jlink = resolve_jlink_path()
        if not jlink:
            return {"success": False, "error": "未找到 JLink.exe，请安装 SEGGER J-Link"}
        return {
            "success": True,
            "chip": chip,
            "probe": "SEGGER J-Link",
            "jlink_exe": jlink,
            "message": f"已连接: {chip} via J-Link"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def connect_swd(chip: str = "STM32F103C8") -> Dict[str, Any]:
    """通过 SWD 连接设备"""
    try:
        from pyocd.core.helpers import ConnectHelper
        
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
        
        # 读取一些基本信息
        try:
            # 尝试读取 IDCODE
            idcode = target.read32(0xE0042000)
            chip_id = f"0x{idcode:08X}"
        except:
            chip_id = "未知"
        
        return {
            "success": True,
            "chip": chip,
            "probe": session.board.description,
            "chip_id": chip_id,
            "message": f"已连接: {chip}"
        }
    except ImportError:
        return {"success": False, "error": "pyocd 未安装，请运行: pip install pyocd"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def disconnect_hardware() -> Dict[str, Any]:
    """断开硬件连接"""
    return {"success": True, "message": "已断开连接"}

def read_registers(names: Optional[List[str]] = None) -> Dict[str, Any]:
    """读取寄存器值"""
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
        
        # 寄存器映射 (STM32F1)
        reg_map = {
            # 核心寄存器
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
            
            # 系统控制块
            "SCB_CPUID": 0xE000ED00,
            "SCB_ICSR": 0xE000ED04,
            "SCB_VTOR": 0xE000ED08,
            "SCB_AIRCR": 0xE000ED0C,
            "SCB_SCR": 0xE000ED10,
            "SCB_CCR": 0xE000ED14,
            "SCB_SHPR": 0xE000ED18,
            "SCB_SHCSR": 0xE000ED24,
            "SCB_CFSR": 0xE000ED28,
            "SCB_HFSR": 0xE000ED2C,
            "SCB_MMAR": 0xE000ED34,
            "SCB_BFAR": 0xE000ED38,
            
            # SysTick
            "SysTick_CSR": 0xE000E010,
            "SysTick_RVR": 0xE000E014,
            "SysTick_CVR": 0xE000E018,
            "SysTick_CALIB": 0xE000E01C,
            
            # NVIC
            "NVIC_ISER0": 0xE000E100,
            "NVIC_ISER1": 0xE000E104,
            "NVIC_ICER0": 0xE000E180,
            "NVIC_ICER1": 0xE000E184,
            "NVIC_ISPR0": 0xE000E200,
            "NVIC_ISPR1": 0xE000E204,
            "NVIC_ICPR0": 0xE000E280,
            "NVIC_ICPR1": 0xE000E284,
            "NVIC_IABR0": 0xE000E300,
            "NVIC_IABR1": 0xE000E304,
            "NVIC_IPR0": 0xE000E400,
            "NVIC_IPR1": 0xE000E404,
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
        
        # 尝试读取 PC
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

def write_register(name: str, value: int) -> Dict[str, Any]:
    """写入寄存器值"""
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
        
        # 简化的寄存器映射
        reg_map = {
            "R0": 0x20000000,
            "R1": 0x20000004,
            "R2": 0x20000008,
            "R3": 0x2000000C,
            "SP": 0x20000034,
            "LR": 0x20000038,
            "PC": 0x2000003C,
        }
        
        if name not in reg_map:
            return {"success": False, "error": f"不支持的寄存器: {name}"}
        
        target.write32(reg_map[name], value)
        
        session.close()
        
        return {
            "success": True,
            "register": name,
            "value": f"0x{value:08X}",
            "message": f"已写入 {name} = 0x{value:08X}"
        }
    except ImportError:
        return {"success": False, "error": "pyocd 未安装"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def reset_device() -> Dict[str, Any]:
    """复位设备"""
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
        
        target.reset_and_halt()
        time.sleep(0.1)
        target.resume()
        
        session.close()
        
        return {"success": True, "message": "设备已复位"}
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
    parser = argparse.ArgumentParser(description="硬件连接工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 连接设备
    connect_parser = subparsers.add_parser("connect", help="连接设备")
    connect_parser.add_argument("--chip", default="STM32F103C8", help="芯片型号")
    connect_parser.add_argument("--method", default="swd", choices=["swd", "uart"], 
                               help="连接方式")
    
    # 断开连接
    subparsers.add_parser("disconnect", help="断开连接")
    
    # 读取寄存器
    reg_parser = subparsers.add_parser("read-regs", help="读取寄存器")
    reg_parser.add_argument("--names", nargs="+", help="寄存器名称列表")
    
    # 写入寄存器
    write_parser = subparsers.add_parser("write-reg", help="写入寄存器")
    write_parser.add_argument("name", help="寄存器名称")
    write_parser.add_argument("value", help="值 (支持十六进制 0x...)")
    
    # 复位设备
    subparsers.add_parser("reset", help="复位设备")
    
    # 分析故障
    fault_parser = subparsers.add_parser("analyze-fault", help="分析 HardFault")
    fault_parser.add_argument("--cfsr", help="CFSR 值 (十六进制)")
    
    args = parser.parse_args()
    
    if args.command == "connect":
        result = connect_hardware(args.chip, args.method)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "disconnect":
        result = disconnect_hardware()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "read-regs":
        result = read_registers(args.names)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "write-reg":
        try:
            value = int(args.value, 0)  # 支持十六进制
            result = write_register(args.name, value)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except ValueError:
            print("无效的数值格式")
    
    elif args.command == "reset":
        result = reset_device()
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