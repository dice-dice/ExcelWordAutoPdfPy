"""ジョブの追加・編集用モーダルダイアログ。"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from models import INTERVAL_UNIT_LABELS, INTERVAL_UNITS


class JobEditDialog(tk.Toplevel):
    def __init__(self, parent, job, base_dir: str):
        super().__init__(parent)
        self.title("ジョブの設定")
        self.resizable(False, False)
        self.transient(parent)

        self._job = job
        self._base_dir = base_dir
        self.result = False

        pad = {"padx": 8, "pady": 6}

        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True, padx=12, pady=12)

        ttk.Label(frm, text="変換対象ファイル").grid(row=0, column=0, sticky="w", **pad)
        self.source_var = tk.StringVar(value=job.source_path)
        ttk.Entry(frm, textvariable=self.source_var, width=48).grid(row=0, column=1, **pad)
        ttk.Button(frm, text="参照...", command=self._browse_source).grid(row=0, column=2, **pad)

        ttk.Label(
            frm,
            text="※ アプリと同じフォルダに置く場合はファイル名だけでもOK(相対パス可)",
            foreground="gray",
        ).grid(row=1, column=1, columnspan=2, sticky="w")

        ttk.Label(frm, text="出力方法").grid(row=2, column=0, sticky="w", **pad)
        self.output_mode_var = tk.StringVar(value="overwrite" if job.overwrite else "rename")
        mode_frame = ttk.Frame(frm)
        mode_frame.grid(row=2, column=1, columnspan=2, sticky="w")
        ttk.Radiobutton(
            mode_frame, text="同名で上書き", variable=self.output_mode_var,
            value="overwrite", command=self._update_output_name_state,
        ).pack(side="left")
        ttk.Radiobutton(
            mode_frame, text="別名で保存", variable=self.output_mode_var,
            value="rename", command=self._update_output_name_state,
        ).pack(side="left", padx=(16, 0))

        ttk.Label(frm, text="出力ファイル名").grid(row=3, column=0, sticky="w", **pad)
        self.output_name_var = tk.StringVar(value=job.output_file_name)
        self.output_name_entry = ttk.Entry(frm, textvariable=self.output_name_var, width=48)
        self.output_name_entry.grid(row=3, column=1, columnspan=2, sticky="w", **pad)

        ttk.Label(frm, text="出力先フォルダ").grid(row=4, column=0, sticky="w", **pad)
        self.output_dir_var = tk.StringVar(value=job.output_directory)
        ttk.Entry(frm, textvariable=self.output_dir_var, width=48).grid(row=4, column=1, **pad)
        ttk.Button(frm, text="参照...", command=self._browse_output_dir).grid(row=4, column=2, **pad)

        ttk.Label(
            frm,
            text="※ 空欄の場合は変換対象ファイルと同じフォルダに出力します",
            foreground="gray",
        ).grid(row=5, column=1, columnspan=2, sticky="w")

        ttk.Label(frm, text="変換周期").grid(row=6, column=0, sticky="w", **pad)
        interval_frame = ttk.Frame(frm)
        interval_frame.grid(row=6, column=1, columnspan=2, sticky="w")
        self.interval_value_var = tk.StringVar(value=str(job.interval_value))
        ttk.Entry(interval_frame, textvariable=self.interval_value_var, width=8).pack(side="left")
        self.interval_unit_var = tk.StringVar(value=INTERVAL_UNIT_LABELS.get(job.interval_unit, "分"))
        unit_labels = [INTERVAL_UNIT_LABELS[u] for u in INTERVAL_UNITS]
        ttk.Combobox(
            interval_frame, textvariable=self.interval_unit_var, values=unit_labels,
            width=6, state="readonly",
        ).pack(side="left", padx=(8, 16))
        self.enabled_var = tk.BooleanVar(value=job.enabled)
        ttk.Checkbutton(
            interval_frame, text="このジョブを有効にする", variable=self.enabled_var,
        ).pack(side="left")

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=7, column=0, columnspan=3, sticky="e", pady=(16, 0))
        ttk.Button(btn_frame, text="OK", command=self._on_ok, width=10).pack(side="left", padx=(0, 8))
        ttk.Button(btn_frame, text="キャンセル", command=self.destroy, width=10).pack(side="left")

        self._update_output_name_state()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.update_idletasks()
        self.grab_set()

    def _update_output_name_state(self):
        state = "disabled" if self.output_mode_var.get() == "overwrite" else "normal"
        self.output_name_entry.configure(state=state)

    def _browse_source(self):
        path = filedialog.askopenfilename(
            parent=self,
            initialdir=self._base_dir,
            filetypes=[("Office文書", "*.xlsx *.xls *.docx *.doc"), ("すべてのファイル", "*.*")],
        )
        if path:
            self.source_var.set(path)

    def _browse_output_dir(self):
        initial = self.output_dir_var.get().strip() or self._base_dir
        path = filedialog.askdirectory(parent=self, initialdir=initial)
        if path:
            self.output_dir_var.set(path)

    def _on_ok(self):
        source_path = self.source_var.get().strip()
        if not source_path:
            messagebox.showwarning("確認", "変換対象ファイルを指定してください。", parent=self)
            return

        overwrite = self.output_mode_var.get() == "overwrite"
        output_name = self.output_name_var.get().strip()
        if not overwrite and not output_name:
            messagebox.showwarning("確認", "別名で保存する場合は出力ファイル名を指定してください。", parent=self)
            return

        try:
            interval_value = int(self.interval_value_var.get().strip())
            if interval_value <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("確認", "変換周期には1以上の整数を指定してください。", parent=self)
            return

        label_to_unit = {v: k for k, v in INTERVAL_UNIT_LABELS.items()}
        interval_unit = label_to_unit.get(self.interval_unit_var.get(), "minutes")

        self._job.source_path = source_path
        self._job.overwrite = overwrite
        self._job.output_file_name = output_name
        self._job.output_directory = self.output_dir_var.get().strip()
        self._job.interval_value = interval_value
        self._job.interval_unit = interval_unit
        self._job.enabled = self.enabled_var.get()

        self.result = True
        self.destroy()
