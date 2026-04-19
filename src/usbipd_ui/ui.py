from __future__ import annotations

from datetime import datetime
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .config import AppConfig, load_config, save_config
from .profiles import load_share_profile, save_share_profile, select_batch_share_busids
from .usbipd import UsbDevice, UsbipdError, UsbipdService


class UsbipdUiApp:
    def __init__(self, root: tk.Tk, config_path: Path) -> None:
        self.root = root
        self.config_path = config_path
        self.config = load_config(config_path)

        self.root.title("USBIPD UI")
        self.root.geometry("1000x620")

        self.usbipd_path_var = tk.StringVar(value=self.config.usbipd_path)
        self.refresh_seconds_var = tk.StringVar(value=str(self.config.refresh_seconds))
        self.startup_profile_path_var = tk.StringVar(value=self.config.startup_profile_path)
        self.auto_share_on_startup_var = tk.BooleanVar(value=self.config.auto_share_on_startup)
        self.batch_share_online_only_var = tk.BooleanVar(value=self.config.batch_share_online_only)
        self.enable_logging_var = tk.BooleanVar(value=self.config.enable_logging)
        self.show_log_panel_var = tk.BooleanVar(value=self.config.show_log_panel)
        self.status_var = tk.StringVar(value="Ready")

        self._devices: list[UsbDevice] = []
        self._refresh_job: str | None = None
        self._refresh_running = False
        self._startup_batch_attempted = False

        self._build_ui()
        self._toggle_log_panel()
        self._schedule_refresh(immediate=True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=12)
        top.pack(fill=tk.X)

        ttk.Label(top, text="usbipd path:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(top, textvariable=self.usbipd_path_var, width=78).grid(row=0, column=1, sticky=tk.EW, padx=6)
        ttk.Button(top, text="Browse", command=self._browse_usbipd_path).grid(row=0, column=2)

        ttk.Label(top, text="Refresh(s):").grid(row=1, column=0, sticky=tk.W, pady=(8, 0))
        ttk.Entry(top, textvariable=self.refresh_seconds_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=6, pady=(8, 0))
        ttk.Button(top, text="Save Config", command=self._save_config).grid(row=1, column=2, pady=(8, 0), sticky=tk.E)

        ttk.Label(top, text="Startup list:").grid(row=2, column=0, sticky=tk.W, pady=(8, 0))
        ttk.Entry(top, textvariable=self.startup_profile_path_var, width=78).grid(row=2, column=1, sticky=tk.EW, padx=6, pady=(8, 0))
        ttk.Button(top, text="Browse", command=self._browse_startup_profile_path).grid(row=2, column=2, pady=(8, 0))

        ttk.Checkbutton(top, text="Auto share on startup", variable=self.auto_share_on_startup_var).grid(
            row=3, column=1, sticky=tk.W, pady=(6, 0)
        )
        ttk.Checkbutton(top, text="Batch share online devices only", variable=self.batch_share_online_only_var).grid(
            row=4, column=1, sticky=tk.W, pady=(2, 0)
        )
        ttk.Checkbutton(top, text="Enable logging", variable=self.enable_logging_var).grid(
            row=5, column=1, sticky=tk.W, pady=(2, 0)
        )
        ttk.Checkbutton(
            top,
            text="Show log panel",
            variable=self.show_log_panel_var,
            command=self._toggle_log_panel,
        ).grid(row=6, column=1, sticky=tk.W, pady=(2, 0))

        top.columnconfigure(1, weight=1)

        actions = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        actions.pack(fill=tk.X)
        ttk.Button(actions, text="Refresh Now", command=lambda: self._schedule_refresh(immediate=True)).pack(side=tk.LEFT)
        ttk.Button(actions, text="Share Selected", command=self._share_selected).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="Unshare Selected", command=self._unshare_selected).pack(side=tk.LEFT)
        ttk.Button(actions, text="Export Shared List", command=self._export_shared_list).pack(side=tk.RIGHT)
        ttk.Button(actions, text="Load List & Share", command=self._load_list_and_share).pack(side=tk.RIGHT, padx=6)

        table_frame = ttk.Frame(self.root, padding=(12, 0, 12, 12))
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("busid", "vidpid", "device", "state", "shared")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("busid", text="BUSID")
        self.tree.heading("vidpid", text="VID:PID")
        self.tree.heading("device", text="Device")
        self.tree.heading("state", text="State")
        self.tree.heading("shared", text="Shared")

        self.tree.column("busid", width=110, anchor=tk.CENTER)
        self.tree.column("vidpid", width=120, anchor=tk.CENTER)
        self.tree.column("device", width=520, anchor=tk.W)
        self.tree.column("state", width=120, anchor=tk.CENTER)
        self.tree.column("shared", width=90, anchor=tk.CENTER)

        yscroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_frame = ttk.LabelFrame(self.root, text="Operation Log", padding=(8, 6))
        self.log_frame.pack(fill=tk.BOTH, expand=False, padx=12, pady=(0, 8))
        self.log_text = tk.Text(self.log_frame, height=8, state=tk.DISABLED, wrap=tk.WORD)
        log_scroll = ttk.Scrollbar(self.log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        status_bar = ttk.Label(self.root, textvariable=self.status_var, anchor=tk.W, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def _browse_usbipd_path(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select usbipd executable",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")],
        )
        if selected:
            self.usbipd_path_var.set(selected)

    def _on_close(self) -> None:
        if self._refresh_job is not None:
            self.root.after_cancel(self._refresh_job)
            self._refresh_job = None
        self.root.destroy()

    def _append_log(self, message: str) -> None:
        if not self.enable_logging_var.get():
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}\n"
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, line)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _toggle_log_panel(self) -> None:
        if self.show_log_panel_var.get():
            if not self.log_frame.winfo_manager():
                self.log_frame.pack(fill=tk.BOTH, expand=False, padx=12, pady=(0, 8))
        else:
            if self.log_frame.winfo_manager():
                self.log_frame.pack_forget()

    def _browse_startup_profile_path(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select startup shared device list",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if selected:
            self.startup_profile_path_var.set(selected)

    def _save_config(self) -> None:
        try:
            refresh_seconds = max(1, int(self.refresh_seconds_var.get().strip()))
        except ValueError:
            messagebox.showerror("Invalid value", "Refresh interval must be an integer >= 1")
            return

        config = AppConfig(
            usbipd_path=self.usbipd_path_var.get().strip() or "usbipd",
            refresh_seconds=refresh_seconds,
            startup_profile_path=self.startup_profile_path_var.get().strip(),
            auto_share_on_startup=bool(self.auto_share_on_startup_var.get()),
            batch_share_online_only=bool(self.batch_share_online_only_var.get()),
            enable_logging=bool(self.enable_logging_var.get()),
            show_log_panel=bool(self.show_log_panel_var.get()),
        )
        save_config(self.config_path, config)
        self.config = config
        self._toggle_log_panel()
        self.status_var.set("Configuration saved")
        self._append_log("Configuration saved")
        self._schedule_refresh(immediate=False)

    def _service(self) -> UsbipdService:
        return UsbipdService(self.usbipd_path_var.get().strip() or "usbipd")

    def _schedule_refresh(self, immediate: bool) -> None:
        if self._refresh_job is not None:
            self.root.after_cancel(self._refresh_job)
            self._refresh_job = None

        if immediate:
            self._refresh_devices_async()

        seconds = self._current_refresh_seconds()
        self._refresh_job = self.root.after(seconds * 1000, lambda: self._schedule_refresh(immediate=True))

    def _current_refresh_seconds(self) -> int:
        try:
            return max(1, int(self.refresh_seconds_var.get().strip()))
        except ValueError:
            return 5

    def _refresh_devices_async(self) -> None:
        if self._refresh_running:
            return

        self._refresh_running = True

        def worker() -> None:
            try:
                devices = self._service().list_devices()
                self.root.after(0, lambda: self._update_devices(devices))
            except Exception as ex:  # noqa: BLE001
                self.root.after(0, lambda: self.status_var.set(f"Refresh failed: {ex}"))
            finally:
                self.root.after(0, self._mark_refresh_idle)

        threading.Thread(target=worker, daemon=True).start()

    def _mark_refresh_idle(self) -> None:
        self._refresh_running = False

    def _update_devices(self, devices: list[UsbDevice]) -> None:
        self._devices = devices
        self.tree.delete(*self.tree.get_children())
        for device in devices:
            self.tree.insert(
                "",
                tk.END,
                iid=device.busid,
                values=(
                    device.busid,
                    device.vid_pid,
                    device.device,
                    device.state,
                    "Yes" if device.is_shared else "No",
                ),
            )
        self.status_var.set(f"Refreshed {len(devices)} devices")
        if not self._startup_batch_attempted and self.auto_share_on_startup_var.get():
            self._startup_batch_attempted = True
            startup_path = self.startup_profile_path_var.get().strip()
            if startup_path:
                self._append_log(f"Auto startup share from {startup_path}")
                self._run_batch_share(Path(startup_path), from_startup=True)
            else:
                self._append_log("Auto startup share enabled but startup list is empty")

    def _run_batch_share(self, path: Path, from_startup: bool = False) -> None:
        try:
            busids = load_share_profile(path)
        except Exception as ex:  # noqa: BLE001
            messagebox.showerror("Load failed", f"Failed to load file: {ex}")
            self._append_log(f"Load list failed: {ex}")
            return

        if not busids:
            messagebox.showinfo("No devices", "No busid found in the selected file")
            self._append_log("Loaded profile has no busid")
            return

        online_only = bool(self.batch_share_online_only_var.get())
        targets, skipped = select_batch_share_busids(busids, self._devices, online_only=online_only)
        self._append_log(
            f"Batch share start. Source={path.name}, requested={len(busids)}, target={len(targets)}, skipped_offline={len(skipped)}"
        )

        if skipped:
            self._append_log(f"Skipped offline busid: {', '.join(skipped)}")

        success = 0
        failed: list[str] = []
        service = self._service()
        for busid in targets:
            try:
                service.bind(busid)
                success += 1
                self._append_log(f"Shared {busid}")
            except UsbipdError as ex:
                failed.append(busid)
                self._append_log(f"Share failed {busid}: {ex}")

        self._schedule_refresh(immediate=True)
        if failed:
            messagebox.showwarning(
                "Batch share completed",
                f"Success: {success}, Failed: {len(failed)}\nFailed busid: {', '.join(failed)}",
            )
        if not from_startup and not failed and success > 0:
            messagebox.showinfo("Batch share completed", f"Shared {success} device(s)")
        self.status_var.set(
            f"Batch share done. Success: {success}, Failed: {len(failed)}, Skipped offline: {len(skipped)}"
        )
        self._append_log(
            f"Batch share done. success={success}, failed={len(failed)}, skipped_offline={len(skipped)}"
        )

    def _selected_busid(self) -> str | None:
        selection = self.tree.selection()
        if not selection:
            return None
        return str(selection[0])

    def _share_selected(self) -> None:
        busid = self._selected_busid()
        if not busid:
            messagebox.showwarning("No selection", "Please select a device first")
            return
        try:
            self._service().bind(busid)
            self.status_var.set(f"Shared device {busid}")
            self._append_log(f"Shared selected device {busid}")
            self._schedule_refresh(immediate=True)
        except UsbipdError as ex:
            messagebox.showerror("Share failed", str(ex))
            self._append_log(f"Share selected failed {busid}: {ex}")

    def _unshare_selected(self) -> None:
        busid = self._selected_busid()
        if not busid:
            messagebox.showwarning("No selection", "Please select a device first")
            return
        try:
            self._service().unbind(busid)
            self.status_var.set(f"Unshared device {busid}")
            self._append_log(f"Unshared selected device {busid}")
            self._schedule_refresh(immediate=True)
        except UsbipdError as ex:
            messagebox.showerror("Unshare failed", str(ex))
            self._append_log(f"Unshare selected failed {busid}: {ex}")

    def _export_shared_list(self) -> None:
        if not self._devices:
            messagebox.showinfo("No data", "No device data available to export")
            return

        save_path = filedialog.asksaveasfilename(
            title="Save shared device list",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not save_path:
            return

        path = Path(save_path)
        save_share_profile(path, self._devices)
        shared_count = len([d for d in self._devices if d.is_shared])
        self.status_var.set(f"Exported {shared_count} shared device(s) to {path.name}")
        self._append_log(f"Exported shared profile to {path}")

    def _load_list_and_share(self) -> None:
        open_path = filedialog.askopenfilename(
            title="Load shared device list",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not open_path:
            return

        path = Path(open_path)
        self._run_batch_share(path)


def run_app(config_path: Path) -> None:
    root = tk.Tk()
    app = UsbipdUiApp(root, config_path)
    root.mainloop()
