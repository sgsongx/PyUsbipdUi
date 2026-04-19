import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from usbipd_ui.ui import run_app
from usbipd_ui.elevation import ensure_admin_or_relaunch


if __name__ == "__main__":
    if not ensure_admin_or_relaunch():
        sys.exit(0)

    config_file = BASE_DIR / "config.json"
    run_app(config_file)
