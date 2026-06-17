#!/usr/bin/env python3
"""烧录工具 - 支持 SWD 和 UART ISP 烧录，以及 TI MSPM0 经 SEGGER J-Link 烧录"""

import sys
import os
import time
import argparse
import json
import subprocess
import threading
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


# ================= TI MSPM0 经 SEGGER J-Link 烧录 =================
# MSPM0 系列（如 MSPM0G3507）使用 SEGGER J-Link 探针烧录，不依赖 pyOCD / stm32loader。
# 烧录流程（J-Link Commander 命令序列）：
#   1) （可选）gmake all 编译 CCS 工程
#   2) 定位最新的 .out 固件
#   3) JLink.exe -device MSPM0G3507 -if SWD -speed 4000 -autoconnect 1
#      依次输入: r / h / loadfile "<out>" / r / g / exit
#   4) （可选）再次连接读取 PC 验证程序已运行


def resolve_jlink_path() -> Optional[str]:
    """定位 JLink.exe：优先注册表，其次 PATH，最后已知路径兜底。"""

    try:
        import winreg  # type: ignore
        for root, label in ((winreg.HKEY_LOCAL_MACHINE, "HKLM"),
                            (winreg.HKEY_CURRENT_USER, "HKCU")):
            try:
                key = winreg.OpenKey(root, r"SOFTWARE\SEGGER\J-Link")
                install_path, _ = winreg.QueryValueEx(key, "InstallPath")
                winreg.CloseKey(key)
                candidate = os.path.join(install_path, "JLink.exe")
                if os.path.exists(candidate):
                    return candidate
            except FileNotFoundError:
                continue
            except OSError:
                continue
    except Exception:
        pass

    # PATH 查找
    for name in ("JLink.exe", "JLink"):
        try:
            from shutil import which
            found = which(name)
            if found:
                return found
        except Exception:
            pass

    # 已知路径兜底
    try:
        import mcucli.config as config  # type: ignore
        candidates = getattr(config, "JLINK_INSTALL_CANDIDATES", [])
    except Exception:
        candidates = []
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None


def _dismiss_jlink_firmware_dialog(stop_event: threading.Event) -> None:
    """后台线程：J-Link V9.48 可能弹出固件更新对话框，自动点击「No」。

    仅在 Windows 生效；非 Windows 或 WinAPI 不可用时静默退出。
    参考 flash-jlink.ps1 的 FindWindowEx + BM_CLICK 方案。
    """

    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        FindWindowEx = user32.FindWindowExW
        FindWindowEx.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
        FindWindowEx.restype = wintypes.HWND
        SendMessage = user32.SendMessageW
        SendMessage.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        SendMessage.restype = wintypes.LPARAM
        SetForegroundWindow = user32.SetForegroundWindow
        SetForegroundWindow.argtypes = [wintypes.HWND]
        SetForegroundWindow.restype = wintypes.BOOL
        BM_CLICK = 0x00F5

        window_titles = (
            "J-Link V9.48 Firmware update",
            "J-Link Firmware update",
            "J-Link 固件更新",
        )
        for _ in range(60):
            if stop_event.is_set():
                return
            time.sleep(0.5)
            for title in window_titles:
                hwnd = FindWindowEx(None, None, None, title)
                if hwnd:
                    SetForegroundWindow(hwnd)
                    time.sleep(0.2)
                    no_btn = FindWindowEx(hwnd, None, "Button", "&No")
                    if not no_btn:
                        no_btn = FindWindowEx(hwnd, None, "Button", "否(&N)")
                    if no_btn:
                        SendMessage(no_btn, BM_CLICK, 0, 0)
                        return
                    # 兜底：Alt+N
                    try:
                        shell = ctypes.windll.shell32
                        # 触发 Alt+N 不可靠，跳过；依赖按钮点击
                    except Exception:
                        pass
                    return
    except Exception:
        # 非 Windows 或 WinAPI 不可用：静默退出
        return


def _resolve_ccs_gmake() -> Optional[str]:
    """定位 CCS 自带的 gmake.exe。"""

    try:
        from shutil import which
        found = which("gmake.exe") or which("gmake")
        if found:
            return found
    except Exception:
        pass
    try:
        import mcucli.config as config  # type: ignore
        candidates = getattr(config, "CCS_GMAKE_CANDIDATES", [])
    except Exception:
        candidates = []
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None


def _find_out_file(project_path: str) -> Optional[str]:
    """在 CCS 工程目录下查找最新的 .out 固件（按修改时间倒序）。"""

    out_files = []
    for root, _dirs, files in os.walk(project_path):
        for name in files:
            if name.lower().endswith(".out"):
                full = os.path.join(root, name)
                out_files.append((os.path.getmtime(full), full))
    if not out_files:
        return None
    out_files.sort(key=lambda item: item[0], reverse=True)
    return out_files[0][1]


def _build_ccs_project(project_path: str) -> Dict[str, Any]:
    """编译 CCS 工程（查找 Debug/makefile 或 makefile，执行 gmake all）。"""

    gmake = _resolve_ccs_gmake()
    if not gmake:
        return {"success": False, "error": "未找到 gmake.exe，请在 CCS 中先构建工程或配置 CCS_GMAKE_CANDIDATES"}

    debug_dir = os.path.join(project_path, "Debug")
    if os.path.exists(os.path.join(debug_dir, "makefile")):
        build_dir = debug_dir
    elif os.path.exists(os.path.join(project_path, "makefile")):
        build_dir = project_path
    else:
        return {"success": False, "error": f"未在 {project_path} 或其 Debug 目录下找到 makefile"}

    try:
        result = subprocess.run(
            [gmake, "all"],
            cwd=build_dir,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "编译超时（180s）"}
    except Exception as e:
        return {"success": False, "error": f"编译异常: {e}"}

    if result.returncode != 0:
        return {"success": False, "error": f"编译失败 (exit {result.returncode}): {result.stderr or result.stdout}"}
    return {"success": True, "message": f"编译成功: {build_dir}"}


def _enumerate_jlink_emulators() -> List[Dict[str, str]]:
    """枚举当前 USB 上在线的 J-Link 探针（通过 JLink.exe ShowEmuList）。

    返回 [{serial, product, connection, nickname}, ...]，失败返回空列表。
    """
    jlink = resolve_jlink_path()
    if not jlink:
        return []
    import tempfile
    fd, cmdfile = tempfile.mkstemp(suffix=".jlink")
    try:
        with os.fdopen(fd, "w") as f:
            f.write("ShowEmuList\nexit\n")
        proc = subprocess.run(
            [jlink, "-if", "SWD", "-speed", "4000", "-CommandFile", cmdfile],
            capture_output=True, text=True, timeout=15,
        )
    except Exception:
        return []
    finally:
        try:
            os.unlink(cmdfile)
        except OSError:
            pass

    out = (proc.stdout or "") + (proc.stderr or "")
    emus: List[Dict[str, str]] = []
    for line in out.splitlines():
        if not line.startswith("J-Link["):
            continue
        body = line.split(":", 1)[1].strip() if ":" in line else ""
        entry: Dict[str, str] = {}
        for part in body.split(","):
            part = part.strip()
            if ":" in part:
                k, v = part.split(":", 1)
                entry[k.strip().lower().replace(" ", "_")] = v.strip()
        sn = entry.get("serial_number", "")
        if sn and sn != "<not set>":
            emus.append({
                "serial": sn,
                "product": entry.get("productname", ""),
                "connection": entry.get("connection", ""),
                "nickname": entry.get("nickname", ""),
            })
    return emus


def _run_jlink_flash(
    jlink: str,
    device: str,
    interface: str,
    speed: int,
    serial: str,
    commands: List[str],
    timeout: int = 120,
) -> Dict[str, Any]:
    """执行一次 J-Link Commander 烧录/验证会话。

    返回 {proc, output, dt, args}（proc 为 subprocess.CompletedProcess 或 None）。
    内部启动固件更新对话框自动关闭线程。
    """
    args = [jlink, "-device", device, "-if", interface,
            "-speed", str(speed), "-autoconnect", "1"]
    if serial:
        args += ["-SelectEmuBySN", serial]

    stop_event = threading.Event()
    dismiss_thread = threading.Thread(
        target=_dismiss_jlink_firmware_dialog, args=(stop_event,), daemon=True
    )
    dismiss_thread.start()
    t0 = time.time()
    try:
        proc = subprocess.run(
            args,
            input="\n".join(commands) + "\n",
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        stop_event.set()
        return {"proc": None, "output": f"J-Link 超时（{timeout}s）",
                "dt": time.time() - t0, "args": args, "timed_out": True}
    finally:
        stop_event.set()
    output = (proc.stdout or "") + (proc.stderr or "")
    return {"proc": proc, "output": output, "dt": time.time() - t0, "args": args}


def list_jlink_probes() -> List[Dict[str, Any]]:
    """列出当前在线的 J-Link 探针（实时枚举 USB）。"""
    jlink = resolve_jlink_path()
    emus = _enumerate_jlink_emulators()
    if emus:
        return [{
            "type": "jlink",
            "serial": e["serial"],
            "product": e["product"],
            "connection": e["connection"],
            "jlink_exe": jlink or "未找到",
            "description": e["product"] or "SEGGER J-Link",
        } for e in emus]
    # 回退到配置默认值
    try:
        import mcucli.config as config  # type: ignore
        serial = getattr(config, "MSPM0_DEFAULT_SERIAL", "")
        device = getattr(config, "MSPM0_DEFAULT_DEVICE", "MSPM0G3507")
    except Exception:
        serial, device = "", "MSPM0G3507"
    return [{
        "type": "jlink",
        "serial": serial,
        "device": device,
        "jlink_exe": jlink or "未找到",
        "description": "未检测到在线 J-Link 探针（仅返回配置默认值）",
    }]


def flash_mspm0(
    path: str,
    device: str = "",
    interface: str = "",
    speed: int = 0,
    serial: str = "",
    build: bool = False,
    verify: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """通过 SEGGER J-Link 烧录 TI MSPM0 固件（天猛星开发板）。

    path 可以是：
      - .out / .bin 固件文件 → 直接烧录
      - CCS 工程目录 → 定位（或先 --build 编译）最新 .out 后烧录

    返回标准 {success, message, ...} 字典。
    """

    # 读取默认配置
    try:
        import mcucli.config as config  # type: ignore
        default_device = getattr(config, "MSPM0_DEFAULT_DEVICE", "MSPM0G3507")
        default_interface = getattr(config, "MSPM0_DEFAULT_INTERFACE", "SWD")
        default_speed = getattr(config, "MSPM0_DEFAULT_SPEED", 4000)
        default_serial = getattr(config, "MSPM0_DEFAULT_SERIAL", "")
    except Exception:
        default_device, default_interface, default_speed, default_serial = "MSPM0G3507", "SWD", 4000, ""

    device = device or default_device
    interface = interface or default_interface
    speed = speed or default_speed
    serial = serial if serial is not None else ""
    serial = serial or default_serial

    # 校验路径：文件 or 目录
    if not os.path.exists(path):
        return {"success": False, "error": f"路径不存在: {path}"}

    out_file: Optional[str] = None
    build_info: Optional[Dict[str, Any]] = None

    if os.path.isdir(path):
        # CCS 工程目录
        if build:
            build_info = _build_ccs_project(path)
            if not build_info.get("success"):
                return build_info
        out_file = _find_out_file(path)
        if not out_file:
            tip = "（可加 --build 先编译）" if not build else ""
            return {"success": False, "error": f"在工程目录下未找到 .out 固件{tip}: {path}"}
    else:
        # 固件文件
        out_file = os.path.abspath(path)

    jlink = resolve_jlink_path()
    if not jlink:
        return {"success": False, "error": "未找到 JLink.exe，请安装 SEGGER J-Link 或配置 JLINK_INSTALL_CANDIDATES"}

    # 烧录命令序列：复位 / 停机 / 下载 / 复位 / 运行 / 退出
    flash_commands = ["r", "h", f'loadfile "{out_file}"', "r", "g", "exit"]

    if dry_run:
        emus = _enumerate_jlink_emulators()
        eff_serial = serial or (emus[0]["serial"] if emus else default_serial)
        args_preview = [jlink, "-device", device, "-if", interface,
                        "-speed", str(speed), "-autoconnect", "1"]
        if eff_serial:
            args_preview += ["-SelectEmuBySN", eff_serial]
        return {
            "success": True,
            "dry_run": True,
            "jlink": jlink,
            "out_file": out_file,
            "device": device,
            "interface": interface,
            "speed": speed,
            "serial": eff_serial or "(auto)",
            "online_probes": [{"serial": e["serial"], "product": e["product"]} for e in emus],
            "command": " ".join(f'"{a}"' if " " in a else a for a in args_preview),
            "sequence": flash_commands,
            "message": f"[DRY RUN] 将烧录 {out_file} 到 {device}",
        }

    size = os.path.getsize(out_file)
    # 首次尝试：显式 serial 优先，其次配置默认 serial
    first_serial = serial or default_serial
    run = _run_jlink_flash(jlink, device, interface, speed, first_serial, flash_commands)
    output = run["output"]
    dt = run["dt"]

    fallback_note = ""
    if run.get("timed_out"):
        return {"success": False, "error": output, "output": output[-2000:]}

    proc = run["proc"]
    connect_failed = ("Connecting to J-Link" in output and "FAILED" in output)

    # Auto-fallback：serial 不匹配/探针变更导致连接失败时，枚举在线探针重试一次
    if connect_failed:
        emus = _enumerate_jlink_emulators()
        alt = next((e for e in emus if e["serial"] != first_serial), None) or (emus[0] if emus else None)
        if alt:
            fallback_note = (f"配置 serial={first_serial or '(空)'} 连接失败，"
                             f"自动改用在线探针 {alt['serial']} ({alt['product']}) 重试")
            run2 = _run_jlink_flash(jlink, device, interface, speed, alt["serial"], flash_commands)
            output = run2["output"]
            dt += run2["dt"]
            first_serial = alt["serial"]
            if run2.get("timed_out"):
                return {"success": False, "error": output, "output": output[-2000:],
                        "fallback": fallback_note}
            proc = run2["proc"]

    base_err = {"fallback": fallback_note} if fallback_note else {}
    if proc is None or proc.returncode != 0:
        rc = proc.returncode if proc else "N/A"
        return {"success": False, "error": f"J-Link 退出码 {rc}",
                "output": output[-2000:], **base_err}

    # 成功标志：包含 "Downloading file" 且包含 "O.K."
    if "Downloading file" not in output or "O.K." not in output:
        return {"success": False,
                "error": "J-Link 未报告明确的烧录成功标志（缺少 Downloading file / O.K.）",
                "output": output[-2000:], **base_err}

    result: Dict[str, Any] = {
        "success": True,
        "size": size,
        "time": round(dt, 2),
        "out_file": out_file,
        "device": device,
        "jlink": jlink,
        "message": f"烧录成功 {size}B / {dt:.1f}s → {device}",
    }
    if fallback_note:
        result["fallback"] = fallback_note
        result["serial"] = first_serial
    if build_info and build_info.get("success"):
        result["build"] = build_info["message"]

    # 可选：验证程序已运行（再次连接读 PC）
    if verify:
        verify_commands = ["sleep 1200", "h", "regs", "g", "exit"]
        try:
            vrun = _run_jlink_flash(jlink, device, interface, speed, first_serial,
                                    verify_commands, timeout=30)
            voutput = vrun["output"]
            import re
            m = re.search(r"PC\s*=\s*([0-9A-Fa-f]{8})", voutput)
            if m:
                result["verify_pc"] = f"0x{m.group(1).upper()}"
                result["verify"] = True
            else:
                result["verify"] = False
                result["verify_note"] = "未读取到有效 PC 值"
        except Exception as e:
            result["verify"] = False
            result["verify_note"] = f"验证异常: {e}"

    return result


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

    # MSPM0 经 J-Link 烧录
    mspm0_parser = subparsers.add_parser("flash-mspm0", help="TI MSPM0 经 SEGGER J-Link 烧录")
    mspm0_parser.add_argument("path", help=".out/.bin 固件文件或 CCS 工程目录")
    mspm0_parser.add_argument("--device", default="", help="目标器件 (默认 MSPM0G3507)")
    mspm0_parser.add_argument("--interface", default="", help="调试接口 (默认 SWD)")
    mspm0_parser.add_argument("--speed", type=int, default=0, help="速率 kHz (默认 4000)")
    mspm0_parser.add_argument("--serial", default="", help="J-Link 序列号 (多探针时指定)")
    mspm0_parser.add_argument("--build", action="store_true", help="先编译 CCS 工程")
    mspm0_parser.add_argument("--verify", action="store_true", help="烧录后验证程序运行")
    mspm0_parser.add_argument("--dry-run", action="store_true", help="只打印命令不执行")

    # 列出 J-Link 探针
    subparsers.add_parser("list-jlink", help="列出 J-Link 探针信息")
    
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

    elif args.command == "flash-mspm0":
        result = flash_mspm0(
            args.path,
            device=args.device,
            interface=args.interface,
            speed=args.speed,
            serial=args.serial,
            build=args.build,
            verify=args.verify,
            dry_run=args.dry_run,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "list-jlink":
        result = list_jlink_probes()
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