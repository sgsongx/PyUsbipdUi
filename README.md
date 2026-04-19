# UsbipdUI

A Python desktop UI for managing USB sharing through usbipd on Windows.

## Features

- Configurable `usbipd` executable path
- Configurable auto-refresh interval
- Device list refresh and display of share state
- Share selected device (`bind`)
- Unshare selected device (`unbind`)
- Export currently shared device BUSID list to JSON
- Load JSON BUSID list and batch share devices quickly
- Optional auto-share from a configured profile at app startup
- Optional "online devices only" filter for batch share
- Detailed operation log panel for share/unshare/batch tasks

## Requirements

- Windows with `usbipd` installed
- Python 3.10+
- Administrator privileges are typically required for `usbipd bind/unbind`

## Run

From project root:

```bash
set PYTHONPATH=src
python main.py
```

## Config

The app saves config to `config.json` in project root:

```json
{
  "usbipd_path": "C:/path/to/usbipd.exe",
  "refresh_seconds": 5,
  "startup_profile_path": "C:/path/to/shared_devices.json",
  "auto_share_on_startup": false,
  "batch_share_online_only": true
}
```

## Shared Device Profile

Exported profile file format:

```json
{
  "busids": ["1-7", "2-4", "3-1"]
}
```

Use `Load List & Share` to load this file and batch execute sharing for all BUSID entries.

If `batch_share_online_only` is enabled, only BUSID values currently present in the refreshed device list are executed; others are skipped and recorded in the log panel.
