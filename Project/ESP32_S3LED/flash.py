#!/usr/bin/env python3
"""将 blink.py 烧录到 ESP32 的 main.py 中并通过软复位启动。"""

import sys
import time
from pathlib import Path

import serial

PORT = "COM9"
BAUD = 115200
SCRIPT_DIR = Path(__file__).parent
BLINK_PY = SCRIPT_DIR / "blink.py"


def wait_for(ser: serial.Serial, expected: bytes, timeout: float = 3.0) -> bytes:
    buf = b""
    start = time.time()
    while time.time() - start < timeout:
        if ser.in_waiting:
            chunk = ser.read(ser.in_waiting)
            buf += chunk
            if expected in buf:
                return buf
        time.sleep(0.01)
    return buf


def enter_raw_repl(ser: serial.Serial) -> bytes:
    ser.reset_input_buffer()
    ser.write(b"\x03")  # Ctrl+C 中断当前运行程序
    time.sleep(0.5)
    ser.read(ser.in_waiting)
    ser.write(b"\x01")  # Ctrl+A 进入 raw REPL
    time.sleep(0.5)
    return wait_for(ser, b"raw REPL")


def exit_raw_repl(ser: serial.Serial) -> None:
    ser.write(b"\x02")  # Ctrl+B 退出 raw REPL
    time.sleep(0.3)
    ser.read(ser.in_waiting)


def exec_raw(ser: serial.Serial, code: str, exec_timeout: float = 5.0) -> bytes:
    ser.write(code.encode("utf-8"))
    ser.write(b"\x04")  # Ctrl+D 执行
    # raw REPL 会先返回 OK，然后是 stdout，最后是结尾的 0x04
    response = wait_for(ser, b"OK", timeout=3.0)
    response += wait_for(ser, b"\x04", timeout=exec_timeout)
    return response


def main() -> int:
    if not BLINK_PY.exists():
        print(f"找不到源文件: {BLINK_PY}", file=sys.stderr)
        return 1

    blink_code = BLINK_PY.read_text(encoding="utf-8")
    # 写入 ESP32 的 main.py，软复位后会自动执行
    upload_code = (
        "with open('main.py', 'w') as f:\n"
        "    f.write('''" + blink_code.replace("'''", '"\'"\'') + "''')\n"
        "print('main.py written')\n"
    )

    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    try:
        print("进入 raw REPL...")
        print(enter_raw_repl(ser).decode("utf-8", errors="ignore"))

        print("上传 blink.py -> main.py...")
        result = exec_raw(ser, upload_code)
        print(result.decode("utf-8", errors="ignore"))

        print("退出 raw REPL 并软复位启动...")
        exit_raw_repl(ser)
        ser.write(b"\x04")  # Ctrl+D 软复位
        time.sleep(2.0)
        print(ser.read(ser.in_waiting).decode("utf-8", errors="ignore"))

        print("完成。ESP32 板载 LED (GPIO2) 应该正在闪烁。")
        return 0
    finally:
        ser.close()


if __name__ == "__main__":
    sys.exit(main())
