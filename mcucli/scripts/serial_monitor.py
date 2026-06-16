#!/usr/bin/env python3
"""串口监控工具 - 用于嵌入式设备通信和调试"""

import sys
import time
import argparse
import json
from typing import Optional, List, Dict, Any

def list_serial_ports() -> List[str]:
    """列出所有可用串口"""
    try:
        import serial.tools.list_ports as list_ports
        ports = []
        for info in list_ports.comports():
            ports.append({
                "port": info.device,
                "description": info.description,
                "hwid": info.hwid
            })
        return ports
    except ImportError:
        return [{"error": "pyserial 未安装，请运行: pip install pyserial"}]

def open_serial(port: str, baud: int = 115200, timeout: float = 1.0) -> Dict[str, Any]:
    """打开串口连接"""
    try:
        import serial
        ser = serial.Serial(port, baud, timeout=timeout)
        return {
            "success": True,
            "port": port,
            "baud": baud,
            "message": f"串口已打开: {port} @ {baud}"
        }
    except ImportError:
        return {"success": False, "error": "pyserial 未安装"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def read_serial(port: str, baud: int = 115200, timeout: float = 3.0, 
                wait_for: Optional[str] = None) -> Dict[str, Any]:
    """读取串口数据"""
    try:
        import serial
        ser = serial.Serial(port, baud, timeout=0.1)
        ser.reset_input_buffer()
        
        data = ""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if ser.in_waiting:
                chunk = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                data += chunk
                if wait_for and wait_for in data:
                    break
            time.sleep(0.01)
        
        ser.close()
        return {
            "success": True,
            "data": data,
            "has_data": bool(data.strip()),
            "length": len(data)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def monitor_serial(port: str, baud: int = 115200, duration: float = 10.0, 
                   keyword: Optional[str] = None) -> Dict[str, Any]:
    """持续监控串口输出"""
    try:
        import serial
        ser = serial.Serial(port, baud, timeout=0.1)
        ser.reset_input_buffer()
        
        output_lines = []
        start_time = time.time()
        found_keyword = False
        
        print(f"监控串口 {port} @ {baud}，持续 {duration} 秒...")
        print("按 Ctrl+C 停止")
        
        while time.time() - start_time < duration:
            if ser.in_waiting:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    timestamp = time.time() - start_time
                    output_lines.append({
                        "time": round(timestamp, 3),
                        "data": line
                    })
                    print(f"[{timestamp:.3f}] {line}")
                    
                    if keyword and keyword in line:
                        found_keyword = True
                        print(f"找到关键字: {keyword}")
                        break
            time.sleep(0.01)
        
        ser.close()
        return {
            "success": True,
            "output": output_lines,
            "found_keyword": found_keyword,
            "total_lines": len(output_lines)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def send_serial(port: str, data: str, baud: int = 115200, 
                newline: bool = True, timeout: float = 2.0) -> Dict[str, Any]:
    """发送数据到串口并等待完整响应"""
    try:
        import serial
        ser = serial.Serial(port, baud, timeout=0.1)
        ser.reset_input_buffer()
        
        if newline:
            data += "\n"
        
        ser.write(data.encode('utf-8'))
        ser.flush()
        
        # 等待并收集响应
        response = ""
        start_time = time.time()
        last_data_time = start_time
        
        while time.time() - start_time < timeout:
            if ser.in_waiting:
                chunk = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                response += chunk
                last_data_time = time.time()
            else:
                # 如果没有新数据，等待一小段时间
                time.sleep(0.05)
            
            # 如果超过 0.5 秒没有新数据，认为响应完成
            if time.time() - last_data_time > 0.5:
                break
        
        ser.close()
        
        # 清理响应（移除回显和提示符）
        clean_response = response.strip()
        
        return {
            "success": True,
            "sent": data.strip(),
            "response": clean_response,
            "has_response": bool(clean_response)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def reset_repl(port: str, baud: int = 115200) -> Dict[str, Any]:
    """重置 MicroPython REPL 状态"""
    try:
        import serial
        ser = serial.Serial(port, baud, timeout=0.1)
        ser.reset_input_buffer()
        
        # 发送 Ctrl+C 中断
        ser.write(b'\x03')
        time.sleep(0.5)
        
        # 读取响应
        response = ''
        while ser.in_waiting:
            response += ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        
        # 发送 Ctrl+D 软复位
        ser.write(b'\x04')
        time.sleep(1)
        
        # 读取响应
        response = ''
        while ser.in_waiting:
            response += ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        
        ser.close()
        
        return {
            "success": '>>>' in response,
            "response": response,
            "message": "REPL 重置成功" if '>>>' in response else "REPL 重置可能失败"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="串口监控工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 列出串口
    subparsers.add_parser("list", help="列出所有可用串口")
    
    # 读取串口
    read_parser = subparsers.add_parser("read", help="读取串口数据")
    read_parser.add_argument("port", help="串口端口")
    read_parser.add_argument("--baud", type=int, default=115200, help="波特率")
    read_parser.add_argument("--timeout", type=float, default=3.0, help="超时时间(秒)")
    read_parser.add_argument("--wait-for", help="等待特定字符串")
    
    # 监控串口
    monitor_parser = subparsers.add_parser("monitor", help="持续监控串口")
    monitor_parser.add_argument("port", help="串口端口")
    monitor_parser.add_argument("--baud", type=int, default=115200, help="波特率")
    monitor_parser.add_argument("--duration", type=float, default=10.0, help="监控时长(秒)")
    monitor_parser.add_argument("--keyword", help="等待的关键字")
    
    # 发送数据
    send_parser = subparsers.add_parser("send", help="发送数据到串口")
    send_parser.add_argument("port", help="串口端口")
    send_parser.add_argument("data", help="要发送的数据")
    send_parser.add_argument("--baud", type=int, default=115200, help="波特率")
    send_parser.add_argument("--no-newline", action="store_true", help="不添加换行符")
    
    # 重置 REPL
    reset_parser = subparsers.add_parser("reset", help="重置 MicroPython REPL")
    reset_parser.add_argument("port", help="串口端口")
    reset_parser.add_argument("--baud", type=int, default=115200, help="波特率")
    
    args = parser.parse_args()
    
    if args.command == "list":
        result = list_serial_ports()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "read":
        result = read_serial(args.port, args.baud, args.timeout, args.wait_for)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "monitor":
        result = monitor_serial(args.port, args.baud, args.duration, args.keyword)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "send":
        result = send_serial(args.port, args.data, args.baud, not args.no_newline)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "reset":
        result = reset_repl(args.port, args.baud)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()