"""Excel/Word 自動PDF化アプリのエントリポイント(Tkinter製 常駐UIアプリ)。"""

import datetime
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

import config_service
import libreoffice_locator
from job_edit_dialog import JobEditDialog
from models import ConversionJob
from monitor_service import MonitorService
from settings_dialog import SettingsDialog

try:
    import pystray
    from PIL import Image, ImageDraw

    TRAY_LIBS_AVAILABLE = True
except ImportError:
    TRAY_LIBS_AVAILABLE = False


def get_base_dir() -> str:
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        # macOSの.appバンドルはexecutableが Contents/MacOS/ の中にあるため、
        # そのままだと「.appを置いたフォルダ」ではなくバンドル内部が基準になってしまう。
        # .appそのものがあるフォルダまで3階層上がる。
        if sys.platform == "darwin" and exe_dir.endswith(os.path.join(".app", "Contents", "MacOS")):
            return os.path.dirname(os.path.dirname(os.path.dirname(exe_dir)))
        return exe_dir
    return os.path.dirname(os.path.abspath(__file__))


class MainApp:
    def __init__(self):
        self.base_dir = get_base_dir()
        self.settings = config_service.load(self.base_dir)

        if not self.settings.libreoffice_path or not os.path.isfile(self.settings.libreoffice_path):
            found = libreoffice_locator.try_find()
            if found:
                self.settings.libreoffice_path = found
                config_service.save(self.base_dir, self.settings)

        self.monitor = MonitorService(
            self.settings,
            self.base_dir,
            on_log=self._on_log_threadsafe,
            on_jobs_updated=self._on_jobs_updated_threadsafe,
        )

        self.event_queue = queue.Queue()
        self.tray_icon = None

        self.root = tk.Tk()
        self.root.title("Excel/Word 自動PDF化")
        self.root.geometry("920x600")
        self.root.minsize(700, 420)

        self._build_menu()
        self._build_toolbar()
        self._build_body()
        self._build_statusbar()

        self._refresh_tree()
        self._update_libreoffice_status()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close_button)
        self.root.after(200, self._poll_queue)

        self._setup_tray()

    # --- UI構築 ---

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="LibreOfficeの設定...", command=self._open_settings)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self._exit_app)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        self.root.config(menu=menubar)

    def _build_toolbar(self):
        bar = ttk.Frame(self.root)
        bar.pack(side="top", fill="x", padx=4, pady=4)

        self.start_button = ttk.Button(bar, text="監視開始", command=self._start_monitoring)
        self.start_button.pack(side="left", padx=2)
        self.stop_button = ttk.Button(bar, text="監視停止", command=self._stop_monitoring, state="disabled")
        self.stop_button.pack(side="left", padx=2)

        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=6)

        ttk.Button(bar, text="ジョブ追加", command=self._add_job).pack(side="left", padx=2)
        ttk.Button(bar, text="編集", command=self._edit_job).pack(side="left", padx=2)
        ttk.Button(bar, text="削除", command=self._delete_job).pack(side="left", padx=2)

        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=6)

        ttk.Button(bar, text="今すぐ変換", command=self._convert_now).pack(side="left", padx=2)

    def _build_body(self):
        paned = ttk.PanedWindow(self.root, orient="vertical")
        paned.pack(side="top", fill="both", expand=True, padx=4, pady=(0, 4))

        tree_frame = ttk.Frame(paned)
        columns = ("enabled", "file", "interval", "output", "last_run", "status")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        headings = {
            "enabled": "有効",
            "file": "ファイル",
            "interval": "周期",
            "output": "出力",
            "last_run": "最終変換",
            "status": "状態",
        }
        widths = {"enabled": 50, "file": 220, "interval": 110, "output": 160, "last_run": 150, "status": 70}
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor="w")
        self.tree.pack(fill="both", expand=True, side="left")

        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", lambda event: self._edit_job())

        log_frame = ttk.Frame(paned)
        self.log_text = ScrolledText(log_frame, height=8, state="disabled", font=("Menlo", 11))
        self.log_text.pack(fill="both", expand=True)

        paned.add(tree_frame, weight=3)
        paned.add(log_frame, weight=1)

    def _build_statusbar(self):
        bar = ttk.Frame(self.root, relief="sunken")
        bar.pack(side="bottom", fill="x")
        self.monitor_status_label = ttk.Label(bar, text="監視: 停止中", padding=(6, 2))
        self.monitor_status_label.pack(side="left")
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y")
        self.libreoffice_status_label = ttk.Label(bar, text="LibreOffice: 未設定", padding=(6, 2))
        self.libreoffice_status_label.pack(side="left")

    # --- ジョブ一覧 ---

    def _refresh_tree(self):
        selected_id = self._selected_job_id()
        self.tree.delete(*self.tree.get_children())
        for job in self.settings.jobs:
            enabled_mark = "✓" if job.enabled else ""
            self.tree.insert(
                "",
                "end",
                iid=job.id,
                values=(
                    enabled_mark,
                    job.display_name,
                    job.interval_display,
                    job.overwrite_display,
                    job.last_run_display,
                    job.last_status,
                ),
            )
        if selected_id and self.tree.exists(selected_id):
            self.tree.selection_set(selected_id)

    def _selected_job_id(self):
        selection = self.tree.selection()
        return selection[0] if selection else None

    def _selected_job(self):
        job_id = self._selected_job_id()
        if not job_id:
            return None
        for job in self.settings.jobs:
            if job.id == job_id:
                return job
        return None

    # --- 監視開始/停止 ---

    def _libreoffice_ready(self) -> bool:
        return bool(self.settings.libreoffice_path) and os.path.isfile(self.settings.libreoffice_path)

    def _start_monitoring(self):
        if not self._libreoffice_ready():
            messagebox.showwarning(
                "LibreOffice未設定",
                "LibreOffice(soffice)のパスが設定されていません。\n「ファイル」メニューから設定してください。",
            )
            return
        self.monitor.start()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.monitor_status_label.configure(text="監視: 実行中")

    def _stop_monitoring(self):
        self.monitor.stop()
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.monitor_status_label.configure(text="監視: 停止中")

    # --- ジョブCRUD ---

    def _add_job(self):
        job = ConversionJob()
        dialog = JobEditDialog(self.root, job, self.base_dir)
        self.root.wait_window(dialog)
        if dialog.result:
            self.settings.jobs.append(job)
            config_service.save(self.base_dir, self.settings)
            self._refresh_tree()
            if self.monitor.is_running:
                # 監視中に追加した場合、次のtickですぐにチェックされるようにする
                self.monitor._next_run[job.id] = 0

    def _edit_job(self):
        job = self._selected_job()
        if not job:
            messagebox.showinfo("確認", "編集するジョブを選択してください。")
            return
        dialog = JobEditDialog(self.root, job, self.base_dir)
        self.root.wait_window(dialog)
        if dialog.result:
            config_service.save(self.base_dir, self.settings)
            self._refresh_tree()

    def _delete_job(self):
        job = self._selected_job()
        if not job:
            messagebox.showinfo("確認", "削除するジョブを選択してください。")
            return
        if not messagebox.askyesno("確認", f"「{job.display_name}」を削除しますか?"):
            return
        self.settings.jobs.remove(job)
        config_service.save(self.base_dir, self.settings)
        self._refresh_tree()

    def _convert_now(self):
        job = self._selected_job()
        if not job:
            messagebox.showinfo("確認", "変換するジョブを選択してください。")
            return
        if not self._libreoffice_ready():
            messagebox.showwarning(
                "LibreOffice未設定",
                "LibreOffice(soffice)のパスが設定されていません。\n「ファイル」メニューから設定してください。",
            )
            return

        def worker():
            result = self.monitor.convert_now(job)
            self.event_queue.put(("manual_result", job, result, None))

        threading.Thread(target=worker, daemon=True).start()

    # --- 設定 ---

    def _open_settings(self):
        dialog = SettingsDialog(self.root, self.settings)
        self.root.wait_window(dialog)
        if dialog.result:
            config_service.save(self.base_dir, self.settings)
            self._update_libreoffice_status()

    def _update_libreoffice_status(self):
        if self._libreoffice_ready():
            self.libreoffice_status_label.configure(text=f"LibreOffice: {self.settings.libreoffice_path}")
        else:
            self.libreoffice_status_label.configure(text="LibreOffice: 未設定")

    # --- スレッドセーフなイベント処理(バックグラウンドスレッド → Tkinterメインスレッド) ---

    def _on_log_threadsafe(self, job, message, is_error):
        self.event_queue.put(("log", job, message, is_error))

    def _on_jobs_updated_threadsafe(self):
        self.event_queue.put(("updated", None, None, None))

    def _poll_queue(self):
        try:
            while True:
                kind, job, message, is_error = self.event_queue.get_nowait()
                if kind == "log":
                    self._append_log(job, message, is_error)
                elif kind == "updated":
                    config_service.save(self.base_dir, self.settings)
                    self._refresh_tree()
                elif kind == "manual_result":
                    result = message
                    config_service.save(self.base_dir, self.settings)
                    self._refresh_tree()
                    if result.success:
                        messagebox.showinfo("完了", f"変換が完了しました:\n{result.output_path}")
                    else:
                        messagebox.showerror("失敗", f"変換に失敗しました:\n{result.message}")
        except queue.Empty:
            pass
        self.root.after(200, self._poll_queue)

    def _append_log(self, job, message, is_error):
        prefix = "[エラー]" if is_error else "[情報]"
        name = job.display_name if job else ""
        line = f"{datetime.datetime.now():%H:%M:%S} {prefix} {name}: {message}\n"
        self.log_text.configure(state="normal")
        self.log_text.insert("end", line)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # --- タスクトレイ / 終了 ---

    def _setup_tray(self):
        if not TRAY_LIBS_AVAILABLE:
            return
        try:
            image = Image.new("RGB", (64, 64), "white")
            draw = ImageDraw.Draw(image)
            draw.rectangle((6, 6, 58, 58), fill="#2b6cb0")
            draw.text((14, 24), "PDF", fill="white")

            menu = pystray.Menu(
                pystray.MenuItem("開く", lambda: self.root.after(0, self._show_from_tray)),
                pystray.MenuItem("監視開始", lambda: self.root.after(0, self._start_monitoring)),
                pystray.MenuItem("監視停止", lambda: self.root.after(0, self._stop_monitoring)),
                pystray.MenuItem("終了", lambda: self.root.after(0, self._exit_app)),
            )
            self.tray_icon = pystray.Icon("ExcelWordAutoPdf", image, "Excel/Word 自動PDF化", menu)

            if hasattr(self.tray_icon, "run_detached"):
                self.tray_icon.run_detached()
            else:
                threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except Exception:
            # トレイアイコンの初期化に失敗しても、アプリ本体は通常通り動作させる
            self.tray_icon = None

    def _show_from_tray(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _on_close_button(self):
        if self.tray_icon is not None:
            self.root.withdraw()
        else:
            self.root.iconify()

    def _exit_app(self):
        self.monitor.stop()
        if self.tray_icon is not None:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    app = MainApp()
    app.run()


if __name__ == "__main__":
    main()
