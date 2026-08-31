"""LibreOfficeのパスを設定するモーダルダイアログ。"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, settings):
        super().__init__(parent)
        self.title("LibreOfficeの設定")
        self.resizable(False, False)
        self.transient(parent)

        self._settings = settings
        self.result = False

        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True, padx=12, pady=12)

        ttk.Label(frm, text="soffice のパス").pack(anchor="w")
        path_frame = ttk.Frame(frm)
        path_frame.pack(fill="x", pady=(4, 0))
        self.path_var = tk.StringVar(value=settings.libreoffice_path)
        ttk.Entry(path_frame, textvariable=self.path_var, width=50).pack(side="left", fill="x", expand=True)
        ttk.Button(path_frame, text="参照...", command=self._browse).pack(side="left", padx=(6, 0))

        ttk.Label(
            frm,
            text=(
                "通常は次の場所です。\n"
                "Mac: /Applications/LibreOffice.app/Contents/MacOS/soffice\n"
                "Windows: C:\\Program Files\\LibreOffice\\program\\soffice.exe"
            ),
            foreground="gray",
            justify="left",
        ).pack(anchor="w", pady=(8, 0))

        btn_frame = ttk.Frame(frm)
        btn_frame.pack(fill="x", pady=(16, 0))
        ttk.Button(btn_frame, text="OK", command=self._on_ok, width=10).pack(side="right", padx=(8, 0))
        ttk.Button(btn_frame, text="キャンセル", command=self.destroy, width=10).pack(side="right")

        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.update_idletasks()
        self.grab_set()

    def _browse(self):
        path = filedialog.askopenfilename(parent=self, title="soffice を選択")
        if path:
            self.path_var.set(path)

    def _on_ok(self):
        path = self.path_var.get().strip()
        if not path or not os.path.isfile(path):
            messagebox.showwarning("確認", "有効なsofficeのパスを指定してください。", parent=self)
            return
        self._settings.libreoffice_path = path
        self.result = True
        self.destroy()
