from __future__ import annotations

import json
from pathlib import Path

from .usbipd import UsbDevice


def save_share_profile(path: Path, devices: list[UsbDevice]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    busids = [d.busid for d in devices if d.is_shared]
    payload = {"busids": busids}
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def load_share_profile(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    value = payload.get("busids", [])
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def select_batch_share_busids(profile_busids: list[str], devices: list[UsbDevice], online_only: bool) -> tuple[list[str], list[str]]:
    if not online_only:
        return profile_busids, []

    online_busids = {device.busid for device in devices}
    targets: list[str] = []
    skipped: list[str] = []

    for busid in profile_busids:
        if busid in online_busids:
            targets.append(busid)
        else:
            skipped.append(busid)
    return targets, skipped
