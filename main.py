import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from usbipd_ui.ui import run_app


if __name__ == "__main__":
    config_file = BASE_DIR / "config.json"
    run_app(config_file)
