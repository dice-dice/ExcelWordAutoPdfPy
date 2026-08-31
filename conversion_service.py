"""LibreOfficeのheadless変換を使って、1件のジョブをPDF化する処理。"""

import os
import shutil
import subprocess
import tempfile
from typing import Optional

CONVERT_TIMEOUT_SECONDS = 180


class ConversionResult:
    def __init__(self, success: bool, message: str = "", output_path: Optional[str] = None):
        self.success = success
        self.message = message
        self.output_path = output_path


def convert(job, base_dir: str, soffice_path: str) -> ConversionResult:
    if not soffice_path or not os.path.isfile(soffice_path):
        return ConversionResult(False, "LibreOffice (soffice) のパスが設定されていません。設定画面から指定してください。")

    source_path = job.resolve_source_path(base_dir)
    if not os.path.isfile(source_path):
        return ConversionResult(False, f"変換対象ファイルが見つかりません: {source_path}")

    output_dir = job.resolve_output_directory(base_dir)
    base_name = os.path.splitext(os.path.basename(source_path))[0]

    if job.overwrite:
        dest_file_name = base_name + ".pdf"
    else:
        name = job.output_file_name.strip()
        if not name:
            return ConversionResult(False, "出力ファイル名が指定されていません。")
        dest_file_name = name if name.lower().endswith(".pdf") else name + ".pdf"

    dest_path = os.path.join(output_dir, dest_file_name)

    temp_dir = tempfile.mkdtemp(prefix="ExcelWordAutoPdf_")
    try:
        os.makedirs(output_dir, exist_ok=True)

        cmd = [
            soffice_path,
            "--headless",
            "--norestore",
            "--convert-to", "pdf",
            "--outdir", temp_dir,
            source_path,
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                timeout=CONVERT_TIMEOUT_SECONDS,
                text=True,
            )
        except subprocess.TimeoutExpired:
            return ConversionResult(False, "LibreOfficeの変換がタイムアウトしました。")

        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            return ConversionResult(False, f"LibreOfficeの変換が失敗しました (exit={proc.returncode}): {stderr}")

        temp_pdf = os.path.join(temp_dir, base_name + ".pdf")
        if not os.path.isfile(temp_pdf):
            return ConversionResult(False, "変換後のPDFが生成されませんでした。ファイル形式を確認してください。")

        shutil.copy2(temp_pdf, dest_path)
        return ConversionResult(True, "", dest_path)
    except Exception as ex:  # 予期しないエラーはログに残して失敗として扱う
        return ConversionResult(False, f"予期しないエラー: {ex}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
