from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(eq=True)
class AppConfig:
    usbipd_path: str = "usbipd"
    refresh_seconds: int = 5
    startup_profile_path: str = ""
    auto_share_on_startup: bool = False
    batch_share_online_only: bool = True


def load_config(config_path: Path) -> AppConfig:
    if not config_path.exists():
        return AppConfig()

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    usbipd_path = str(payload.get("usbipd_path", "usbipd"))
    refresh_seconds = int(payload.get("refresh_seconds", 5))
    if refresh_seconds < 1:
        refresh_seconds = 1
    startup_profile_path = str(payload.get("startup_profile_path", "")).strip()
    auto_share_on_startup = bool(payload.get("auto_share_on_startup", False))
    batch_share_online_only = bool(payload.get("batch_share_online_only", True))
    return AppConfig(
        usbipd_path=usbipd_path,
        refresh_seconds=refresh_seconds,
        startup_profile_path=startup_profile_path,
        auto_share_on_startup=auto_share_on_startup,
        batch_share_online_only=batch_share_online_only,
    )


def save_config(config_path: Path, config: AppConfig) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "usbipd_path": config.usbipd_path,
        "refresh_seconds": max(1, int(config.refresh_seconds)),
        "startup_profile_path": config.startup_profile_path,
        "auto_share_on_startup": bool(config.auto_share_on_startup),
        "batch_share_online_only": bool(config.batch_share_online_only),
    }
    config_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
