"""TI MSPM0 / SEGGER J-Link hardware helpers.

天猛星开发板（MSPM0G3507）通过 SEGGER J-Link OB 探针烧录，不依赖 pyOCD。
本模块提供与 ``hardware.swd.PyOCDBridge`` 同构的 ``JLinkBridge`` 抽象，
供常驻 Agent 通过 ``ctx.bridge`` 复用连接状态。

J-Link Commander 烧录命令序列：r / h / loadfile "<.out>" / r / g / exit
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional


def _console_print(console: Any, message: str) -> None:
    """Print via the injected console when available."""

    if console is None:
        return
    try:
        console.print(message)
    except Exception:
        pass


def _resolve_jlink_path() -> Optional[str]:
    """Locate JLink.exe: registry first, then PATH, then known candidates."""

    try:
        import winreg  # type: ignore
        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
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

    for name in ("JLink.exe", "JLink"):
        try:
            from shutil import which
            found = which(name)
            if found:
                return found
        except Exception:
            pass

    try:
        import mcucli.config as config  # type: ignore
        for candidate in getattr(config, "JLINK_INSTALL_CANDIDATES", []):
            if os.path.exists(candidate):
                return candidate
    except Exception:
        pass
    return None


def _dismiss_firmware_dialog(stop_event: threading.Event) -> None:
    """Background thread auto-clicking "No" on the J-Link firmware-update dialog.

    Mirrors flash-jlink.ps1: FindWindowEx on the specific window title, then
    BM_CLICK on the "&No" button. No-op on non-Windows or WinAPI failure.
    """

    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        find = user32.FindWindowExW
        find.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
        find.restype = wintypes.HWND
        send = user32.SendMessageW
        send.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        send.restype = wintypes.LPARAM
        fg = user32.SetForegroundWindow
        fg.argtypes = [wintypes.HWND]
        fg.restype = wintypes.BOOL
        BM_CLICK = 0x00F5
        titles = ("J-Link V9.48 Firmware update", "J-Link Firmware update")
        for _ in range(60):
            if stop_event.is_set():
                return
            time.sleep(0.5)
            for title in titles:
                hwnd = find(None, None, None, title)
                if hwnd:
                    fg(hwnd)
                    time.sleep(0.2)
                    no_btn = find(hwnd, None, "Button", "&No")
                    if no_btn:
                        send(no_btn, BM_CLICK, 0, 0)
                    return
    except Exception:
        return


class JLinkBridge:
    """Thin wrapper around SEGGER J-Link Commander operations for MSPM0."""

    def __init__(
        self,
        *,
        console: Any = None,
        device: str = "",
        interface: str = "",
        speed: int = 0,
        serial: str = "",
    ) -> None:
        """Initialize the J-Link bridge state."""

        self.console = console
        self.device = device or self._default("MSPM0_DEFAULT_DEVICE", "MSPM0G3507")
        self.interface = interface or self._default("MSPM0_DEFAULT_INTERFACE", "SWD")
        self.speed = speed or int(self._default("MSPM0_DEFAULT_SPEED", "4000"))
        self.serial = serial or self._default("MSPM0_DEFAULT_SERIAL", "")
        self.jlink_exe: Optional[str] = None
        self.connected = False
        self.chip_info: dict[str, Any] = {}

    @staticmethod
    def _default(name: str, fallback: str) -> str:
        try:
            import mcucli.config as config  # type: ignore
            return str(getattr(config, name, fallback)) or fallback
        except Exception:
            return fallback

    def configure(
        self,
        *,
        console: Any = None,
        device: Optional[str] = None,
        interface: Optional[str] = None,
        speed: Optional[int] = None,
        serial: Optional[str] = None,
    ) -> None:
        """Refresh runtime dependencies without recreating the instance."""

        if console is not None:
            self.console = console
        if device is not None:
            self.device = device
        if interface is not None:
            self.interface = interface
        if speed is not None:
            self.speed = speed
        if serial is not None:
            self.serial = serial

    def _base_args(self) -> list[str]:
        """Build the base JLink.exe argument list."""

        exe = self.jlink_exe or _resolve_jlink_path()
        args = [exe, "-device", self.device, "-if", self.interface,
                "-speed", str(self.speed), "-autoconnect", "1"]
        if self.serial:
            args += ["-SelectEmuBySN", self.serial]
        return args

    def start(self) -> bool:
        """Verify J-Link is available and ready (no persistent connection kept)."""

        self.stop()
        self.jlink_exe = _resolve_jlink_path()
        if not self.jlink_exe:
            _console_print(self.console, "[red]未找到 JLink.exe，请安装 SEGGER J-Link[/]")
            return False
        self.chip_info = {
            "device": self.device,
            "interface": self.interface,
            "speed": self.speed,
            "serial": self.serial or "(auto)",
            "jlink_exe": self.jlink_exe,
        }
        self.connected = True
        _console_print(
            self.console,
            f"[green]  J-Link 就绪: {self.device} | {self.interface}@{self.speed}kHz[/]",
        )
        return True

    def stop(self) -> None:
        """Release the bridge (J-Link Commander is per-invocation, nothing to close)."""

        self.connected = False

    def flash(self, bin_path: str) -> dict[str, Any]:
        """Program a .out/.bin image through J-Link Commander."""

        if not self.connected:
            return {"ok": False, "msg": "J-Link 未就绪，请先 connect"}
        binary_path = Path(bin_path)
        if not binary_path.exists():
            return {"ok": False, "msg": f"文件不存在: {bin_path}"}

        size = binary_path.stat().st_size
        commands = ["r", "h", f'loadfile "{binary_path}"', "r", "g", "exit"]
        t0 = time.time()
        _console_print(self.console, f"[dim]  烧录 {size} 字节 via J-Link...[/]")

        stop_event = threading.Event()
        worker = threading.Thread(target=_dismiss_firmware_dialog, args=(stop_event,), daemon=True)
        worker.start()
        try:
            proc = subprocess.run(
                self._base_args(),
                input="\n".join(commands) + "\n",
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "msg": "J-Link 烧录超时（120s）"}
        finally:
            stop_event.set()

        output = (proc.stdout or "") + (proc.stderr or "")
        dt = time.time() - t0

        if proc.returncode != 0:
            return {"ok": False, "msg": f"J-Link 退出码 {proc.returncode}: {output[-500:]}"}
        if "Downloading file" not in output or "O.K." not in output:
            return {"ok": False, "msg": f"未检测到烧录成功标志: {output[-500:]}"}

        spd = size / dt / 1024 if dt > 0 else 0
        return {"ok": True, "msg": f"烧录成功 {size}B / {dt:.1f}s ({spd:.1f} KB/s)"}

    def read_registers(self, names: Optional[list[str]] = None) -> Optional[dict[str, str]]:
        """Read core registers (PC/SP/R0..) via J-Link Commander ``regs`` command."""

        if not self.connected:
            return None
        commands = ["h", "regs", "g", "exit"]
        try:
            proc = subprocess.run(
                self._base_args(),
                input="\n".join(commands) + "\n",
                capture_output=True,
                text=True,
                timeout=30,
            )
        except Exception as exc:
            _console_print(self.console, f"[red]  寄存器读取异常: {exc}[/]")
            return None
        output = (proc.stdout or "") + (proc.stderr or "")
        regs: dict[str, str] = {}
        for match in re.finditer(r"([A-Z0-9]+)\s*=\s*([0-9A-Fa-f]{8})", output):
            regs[match.group(1)] = f"0x{match.group(2).upper()}"
        return regs or None

    def list_probes(self) -> list[dict[str, Any]]:
        """Return configured J-Link probe info (J-Link has no unified enum API)."""

        return [{
            "type": "jlink",
            "serial": self.serial,
            "device": self.device,
            "jlink_exe": self.jlink_exe or _resolve_jlink_path() or "未找到",
        }]


def _prepare_bridge(
    ctx: Any,
    *,
    console: Any = None,
    device: str = "",
    interface: str = "",
    speed: int = 0,
    serial: str = "",
) -> JLinkBridge:
    """Return a configured J-Link bridge, reusing the context object when possible."""

    bridge = getattr(ctx, "bridge", None)
    if isinstance(bridge, JLinkBridge):
        bridge.configure(
            console=console, device=device, interface=interface, speed=speed, serial=serial
        )
        return bridge
    return JLinkBridge(
        console=console, device=device, interface=interface, speed=speed, serial=serial
    )


def connect_mspm0(
    ctx: Any,
    *,
    device: str = "",
    interface: str = "",
    speed: int = 0,
    serial: str = "",
    console: Any = None,
) -> dict[str, Any]:
    """Bring up a J-Link bridge for MSPM0 and store it on the context."""

    bridge = _prepare_bridge(
        ctx, console=console, device=device, interface=interface, speed=speed, serial=serial
    )
    success = bridge.start()
    if success:
        ctx.bridge = bridge  # type: ignore[attr-defined]
    return {
        "success": success,
        "bridge": bridge,
        "chip_info": dict(bridge.chip_info),
        "message": (
            f"硬件已连接: {bridge.chip_info.get('device', 'MSPM0G3507')} via J-Link"
            if success
            else "J-Link 连接失败，请检查探针 USB 连接与驱动"
        ),
    }


def disconnect_mspm0(ctx: Any) -> dict[str, Any]:
    """Release the J-Link bridge held by the context."""

    bridge = getattr(ctx, "bridge", None)
    if isinstance(bridge, JLinkBridge):
        bridge.stop()
    return {"success": True, "message": "已断开"}


def flash_via_mspm0(ctx: Any, bin_path: str) -> dict[str, Any]:
    """Flash a binary through the J-Link bridge stored in the context."""

    bridge = getattr(ctx, "bridge", None)
    if not isinstance(bridge, JLinkBridge) or not bridge.connected:
        return {"success": False, "message": "硬件未连接，请先调用 connect_mspm0"}
    result = bridge.flash(bin_path)
    return {"success": result["ok"], "message": result["msg"]}


__all__ = [
    "JLinkBridge",
    "connect_mspm0",
    "disconnect_mspm0",
    "flash_via_mspm0",
]
