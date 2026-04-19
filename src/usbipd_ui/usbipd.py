from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from typing import Callable


@dataclass
class UsbDevice:
    busid: str
    vid_pid: str
    device: str
    state: str
    is_shared: bool


class UsbipdError(Exception):
    pass


def parse_usbipd_list_output(output: str) -> list[UsbDevice]:
    devices: list[UsbDevice] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.lower().startswith(("connected", "persisted", "busid", "guid")):
            continue

        parts = re.split(r"\s{2,}", line)
        if len(parts) < 4:
            continue

        busid = parts[0]
        vid_pid = parts[1]
        state = parts[-1]
        device_name = "  ".join(parts[2:-1]).strip()

        if not re.match(r"^\d+-\d+(?:-\d+)*$", busid):
            continue
        if not re.match(r"^[0-9a-fA-F]{4}:[0-9a-fA-F]{4}$", vid_pid):
            continue

        state_lower = state.lower()
        is_shared = ("shared" in state_lower and "not" not in state_lower) or ("attached" in state_lower)
        devices.append(
            UsbDevice(
                busid=busid,
                vid_pid=vid_pid,
                device=device_name,
                state=state,
                is_shared=is_shared,
            )
        )

    return devices


def _run_usbipd_command(usbipd_path: str, args: list[str]) -> str:
    process = subprocess.run(
        [usbipd_path, *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if process.returncode != 0:
        stderr = process.stderr.strip()
        stdout = process.stdout.strip()
        details = stderr if stderr else stdout
        raise UsbipdError(details or "usbipd command failed")
    return process.stdout


class UsbipdService:
    def __init__(self, usbipd_path: str, runner: Callable[[str, list[str]], str] | None = None) -> None:
        self.usbipd_path = usbipd_path
        self._runner = runner or _run_usbipd_command

    def list_devices(self) -> list[UsbDevice]:
        output = self._runner(self.usbipd_path, ["list"])
        return parse_usbipd_list_output(output)

    def bind(self, busid: str) -> None:
        self._runner(self.usbipd_path, ["bind", "--busid", busid])

    def unbind(self, busid: str) -> None:
        self._runner(self.usbipd_path, ["unbind", "--busid", busid])
