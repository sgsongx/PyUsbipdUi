from pathlib import Path

from usbipd_ui.ui import run_app


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    config_file = base_dir / "config.json"
    run_app(config_file)
