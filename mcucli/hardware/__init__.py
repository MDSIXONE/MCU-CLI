"""Public hardware module API."""

from mcucli.hardware.serial_mon import connect_serial, disconnect_serial, read_serial_output
from mcucli.hardware.swd import connect_swd, disconnect_swd, flash_via_swd, read_registers
from mcucli.hardware.uart_isp import flash_via_uart
from mcucli.hardware.mspm0 import (
    JLinkBridge,
    connect_mspm0,
    disconnect_mspm0,
    flash_via_mspm0,
)

__all__ = [
    "JLinkBridge",
    "connect_serial",
    "connect_swd",
    "connect_mspm0",
    "disconnect_serial",
    "disconnect_swd",
    "disconnect_mspm0",
    "flash_via_swd",
    "flash_via_uart",
    "flash_via_mspm0",
    "read_registers",
    "read_serial_output",
]
