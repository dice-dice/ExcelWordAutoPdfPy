"""LibreOffice(soffice)の実行ファイルを自動検出する。"""

import os
import platform
import shutil
from typing import Optional


def try_find() -> Optional[str]:
    found = shutil.which("soffice") or shutil.which("libreoffice")
    if found:
        return found

    system = platform.system()
    candidates = []

    if system == "Darwin":
        candidates.append("/Applications/LibreOffice.app/Contents/MacOS/soffice")
    elif system == "Windows":
        for env_var in ("ProgramFiles", "ProgramFiles(x86)"):
            root = os.environ.get(env_var)
            if root:
                candidates.append(os.path.join(root, "LibreOffice", "program", "soffice.exe"))
    else:
        candidates.extend([
            "/usr/bin/soffice",
            "/usr/local/bin/soffice",
            "/opt/libreoffice/program/soffice",
        ])

    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return None
