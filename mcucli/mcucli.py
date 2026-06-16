#!/usr/bin/env python3
"""MCU CLI - 嵌入式开发工具集"""

import sys
import argparse
import json
from pathlib import Path

# 添加当前目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

def main():
    parser = argparse.ArgumentParser(
        description="MCU CLI - 嵌入式开发工具集",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s serial list                    # 列出串口
  %(prog)s serial read COM9               # 读取串口
  %(prog)s flash swd firmware.bin         # SWD 烧录
  %(prog)s compile main.c                 # 编译代码
  %(prog)s connect --chip STM32F103C8     # 连接设备
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 串口命令
    serial_parser = subparsers.add_parser("serial", help="串口工具")
    serial_subparsers = serial_parser.add_subparsers(dest="serial_command")
    
    serial_subparsers.add_parser("list", help="列出串口")
    
    read_parser = serial_subparsers.add_parser("read", help="读取串口")
    read_parser.add_argument("port", help="串口端口")
    read_parser.add_argument("--baud", type=int, default=115200, help="波特率")
    read_parser.add_argument("--timeout", type=float, default=3.0, help="超时时间")
    
    monitor_parser = serial_subparsers.add_parser("monitor", help="监控串口")
    monitor_parser.add_argument("port", help="串口端口")
    monitor_parser.add_argument("--duration", type=float, default=10.0, help="监控时长")
    
    send_parser = serial_subparsers.add_parser("send", help="发送数据")
    send_parser.add_argument("port", help="串口端口")
    send_parser.add_argument("data", help="数据")
    
    # 烧录命令
    flash_parser = subparsers.add_parser("flash", help="烧录工具")
    flash_subparsers = flash_parser.add_subparsers(dest="flash_command")
    
    flash_swd_parser = flash_subparsers.add_parser("swd", help="SWD 烧录")
    flash_swd_parser.add_argument("bin_path", help="固件文件")
    flash_swd_parser.add_argument("--chip", default="STM32F103C8", help="芯片型号")
    
    flash_uart_parser = flash_subparsers.add_parser("uart", help="UART 烧录")
    flash_uart_parser.add_argument("bin_path", help="固件文件")
    flash_uart_parser.add_argument("--port", default="COM9", help="串口端口")
    
    flash_subparsers.add_parser("list", help="列出调试探针")
    
    # 编译命令
    compile_parser = subparsers.add_parser("compile", help="编译工具")
    compile_subparsers = compile_parser.add_subparsers(dest="compile_command")
    
    compile_stm32_parser = compile_subparsers.add_parser("stm32", help="编译 STM32")
    compile_stm32_parser.add_argument("source", help="源文件")
    compile_stm32_parser.add_argument("--chip", default="STM32F103C8", help="芯片型号")
    
    compile_esp32_parser = compile_subparsers.add_parser("esp32", help="编译 ESP32")
    compile_esp32_parser.add_argument("source", help="源文件")
    
    compile_subparsers.add_parser("check", help="检查工具链")
    
    # 连接命令
    connect_parser = subparsers.add_parser("connect", help="硬件连接")
    connect_parser.add_argument("--chip", default="STM32F103C8", help="芯片型号")
    connect_parser.add_argument("--method", default="swd", choices=["swd", "uart"])
    
    # 寄存器命令
    reg_parser = subparsers.add_parser("regs", help="寄存器操作")
    reg_subparsers = reg_parser.add_subparsers(dest="reg_command")
    
    reg_subparsers.add_parser("read", help="读取寄存器")
    
    write_parser = reg_subparsers.add_parser("write", help="写入寄存器")
    write_parser.add_argument("name", help="寄存器名称")
    write_parser.add_argument("value", help="值")
    
    # 复位命令
    subparsers.add_parser("reset", help="复位设备")
    
    args = parser.parse_args()
    
    if args.command == "serial":
        from scripts.serial_monitor import list_serial_ports, read_serial, monitor_serial, send_serial
        
        if args.serial_command == "list":
            result = list_serial_ports()
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        elif args.serial_command == "read":
            result = read_serial(args.port, args.baud, args.timeout)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        elif args.serial_command == "monitor":
            result = monitor_serial(args.port, duration=args.duration)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        elif args.serial_command == "send":
            result = send_serial(args.port, args.data)
            print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "flash":
        from scripts.flash_tool import flash_swd, flash_uart, list_debug_probes
        
        if args.flash_command == "list":
            result = list_debug_probes()
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        elif args.flash_command == "swd":
            result = flash_swd(args.bin_path, args.chip)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        elif args.flash_command == "uart":
            result = flash_uart(args.bin_path, args.port)
            print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "compile":
        from scripts.compile_tool import compile_stm32, compile_esp32, check_toolchain
        
        if args.compile_command == "check":
            result = check_toolchain()
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        elif args.compile_command == "stm32":
            result = compile_stm32(args.source, args.chip)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        elif args.compile_command == "esp32":
            result = compile_esp32(args.source)
            print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "connect":
        from scripts.hardware_connect import connect_hardware
        result = connect_hardware(args.chip, args.method)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "regs":
        from scripts.hardware_connect import read_registers, write_register
        
        if args.reg_command == "read":
            result = read_registers()
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        elif args.reg_command == "write":
            try:
                value = int(args.value, 0)
                result = write_register(args.name, value)
                print(json.dumps(result, indent=2, ensure_ascii=False))
            except ValueError:
                print("无效的数值格式")
    
    elif args.command == "reset":
        from scripts.hardware_connect import reset_device
        result = reset_device()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()