import json
import tempfile
import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from usbipd_ui.config import AppConfig, load_config, save_config
from usbipd_ui.profiles import load_share_profile, save_share_profile, select_batch_share_busids
from usbipd_ui.usbipd import UsbDevice, parse_usbipd_list_output


class ConfigTests(unittest.TestCase):
    def test_load_default_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "config.json"
            cfg = load_config(cfg_path)
            self.assertEqual(cfg.usbipd_path, "usbipd")
            self.assertEqual(cfg.refresh_seconds, 5)

    def test_save_and_load_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "config.json"
            expected = AppConfig(
                usbipd_path=r"C:\\tools\\usbipd.exe",
                refresh_seconds=9,
                startup_profile_path=r"C:\\profiles\\lab.json",
                auto_share_on_startup=True,
                batch_share_online_only=False,
            )
            save_config(cfg_path, expected)
            actual = load_config(cfg_path)
            self.assertEqual(expected, actual)


class ParseTests(unittest.TestCase):
    def test_parse_usbipd_output(self):
        output = """
Connected:
BUSID  VID:PID    DEVICE                                                        STATE
1-1    04ca:7070  Integrated Camera                                             Not shared
1-7    046d:c534  USB Receiver                                                  Shared
2-4    8087:0032  Intel(R) Wireless Bluetooth(R)                               Attached
Persisted:
GUID                                  DEVICE
"""
        devices = parse_usbipd_list_output(output)
        self.assertEqual(len(devices), 3)
        self.assertEqual(devices[0].busid, "1-1")
        self.assertFalse(devices[0].is_shared)
        self.assertTrue(devices[1].is_shared)
        self.assertTrue(devices[2].is_shared)


class ProfileTests(unittest.TestCase):
    def test_save_and_load_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            file_path = Path(tmp) / "shared_devices.json"
            devices = [
                UsbDevice(busid="1-2", vid_pid="1234:abcd", device="Device A", state="Shared", is_shared=True),
                UsbDevice(busid="2-9", vid_pid="1111:2222", device="Device B", state="Not shared", is_shared=False),
                UsbDevice(busid="3-1", vid_pid="3333:4444", device="Device C", state="Attached", is_shared=True),
            ]
            save_share_profile(file_path, devices)
            self.assertTrue(file_path.exists())

            data = json.loads(file_path.read_text(encoding="utf-8"))
            self.assertEqual(data["busids"], ["1-2", "3-1"])

            busids = load_share_profile(file_path)
            self.assertEqual(busids, ["1-2", "3-1"])

    def test_select_batch_share_busids_online_only(self):
        devices = [
            UsbDevice(busid="1-2", vid_pid="1234:abcd", device="Device A", state="Not shared", is_shared=False),
            UsbDevice(busid="3-1", vid_pid="3333:4444", device="Device C", state="Shared", is_shared=True),
        ]
        targets, skipped = select_batch_share_busids(["1-2", "2-9", "3-1"], devices, online_only=True)
        self.assertEqual(targets, ["1-2", "3-1"])
        self.assertEqual(skipped, ["2-9"])

    def test_select_batch_share_busids_without_filter(self):
        devices = [UsbDevice(busid="1-2", vid_pid="1234:abcd", device="Device A", state="Not shared", is_shared=False)]
        targets, skipped = select_batch_share_busids(["1-2", "2-9"], devices, online_only=False)
        self.assertEqual(targets, ["1-2", "2-9"])
        self.assertEqual(skipped, [])


if __name__ == "__main__":
    unittest.main()
