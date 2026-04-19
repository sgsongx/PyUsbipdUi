from __future__ import annotations

import os
import subprocess
import sys
from typing import Callable


def is_running_as_admin() -> bool:
    if os.name != "nt":
        return True

    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def get_elevated_python_executable(executable: str) -> str:
    if os.name != "nt":
        return executable

    if executable.lower().endswith("python.exe"):
        return executable[:-10] + "pythonw.exe"
    return executable


def relaunch_as_admin() -> None:
    if os.name != "nt":
        return

    import ctypes

    params = subprocess.list2cmdline(sys.argv)
    executable = get_elevated_python_executable(sys.executable)
    result = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, params, os.getcwd(), 0)
    if result <= 32:
        raise RuntimeError(f"Failed to relaunch with admin privileges, ShellExecuteW code={result}")


def ensure_admin_or_relaunch(launcher: Callable[[], None] | None = None) -> bool:
    if is_running_as_admin():
        return True

    elevate = launcher or relaunch_as_admin
    elevate()
    return False
