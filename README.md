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
  "refresh_seconds": 5
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
