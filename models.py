"""変換ジョブおよびアプリ設定のデータモデル。"""

import datetime
import os
import uuid
from typing import Optional

INTERVAL_UNITS = ["seconds", "minutes", "hours"]

INTERVAL_UNIT_LABELS = {
    "seconds": "秒",
    "minutes": "分",
    "hours": "時間",
}

_INTERVAL_UNIT_SECONDS = {
    "seconds": 1,
    "minutes": 60,
    "hours": 3600,
}


def _resolve_path(path: str, base_dir: str) -> str:
    if not path:
        return path
    if os.path.isabs(path):
        return path
    return os.path.abspath(os.path.join(base_dir, path))


class ConversionJob:
    """1件の変換ジョブ(対象ファイル・出力設定・周期・実行状態)を表す。"""

    def __init__(self):
        self.id: str = str(uuid.uuid4())
        self.source_path: str = ""
        self.overwrite: bool = True
        self.output_file_name: str = ""
        self.output_directory: str = ""
        self.interval_value: int = 10
        self.interval_unit: str = "minutes"
        self.enabled: bool = True

        # 実行状態(設定ファイルに保存され、次回起動時にも引き継がれる)
        self.last_source_modified: Optional[float] = None
        self.last_run: Optional[float] = None
        self.last_status: str = "未実行"
        self.last_error: Optional[str] = None

    def interval_seconds(self) -> float:
        unit_seconds = _INTERVAL_UNIT_SECONDS.get(self.interval_unit, 60)
        return max(1, self.interval_value) * unit_seconds

    def resolve_source_path(self, base_dir: str) -> str:
        return _resolve_path(self.source_path, base_dir)

    def resolve_output_directory(self, base_dir: str) -> str:
        if not self.output_directory.strip():
            source_dir = os.path.dirname(self.resolve_source_path(base_dir))
            return source_dir if source_dir else base_dir
        return _resolve_path(self.output_directory, base_dir)

    @property
    def display_name(self) -> str:
        return os.path.basename(self.source_path) if self.source_path else "(未設定)"

    @property
    def interval_display(self) -> str:
        label = INTERVAL_UNIT_LABELS.get(self.interval_unit, self.interval_unit)
        return f"{self.interval_value} {label}ごと"

    @property
    def overwrite_display(self) -> str:
        if self.overwrite:
            return "上書き"
        name = self.output_file_name if self.output_file_name else "未設定"
        return f"別名 ({name})"

    @property
    def last_run_display(self) -> str:
        if self.last_run is None:
            return "-"
        return datetime.datetime.fromtimestamp(self.last_run).strftime("%Y/%m/%d %H:%M:%S")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_path": self.source_path,
            "overwrite": self.overwrite,
            "output_file_name": self.output_file_name,
            "output_directory": self.output_directory,
            "interval_value": self.interval_value,
            "interval_unit": self.interval_unit,
            "enabled": self.enabled,
            "last_source_modified": self.last_source_modified,
            "last_run": self.last_run,
            "last_status": self.last_status,
            "last_error": self.last_error,
        }

    @staticmethod
    def from_dict(data: dict) -> "ConversionJob":
        job = ConversionJob()
        job.id = data.get("id", job.id)
        job.source_path = data.get("source_path", "")
        job.overwrite = data.get("overwrite", True)
        job.output_file_name = data.get("output_file_name", "")
        job.output_directory = data.get("output_directory", "")
        job.interval_value = data.get("interval_value", 10)
        job.interval_unit = data.get("interval_unit", "minutes")
        job.enabled = data.get("enabled", True)
        job.last_source_modified = data.get("last_source_modified")
        job.last_run = data.get("last_run")
        job.last_status = data.get("last_status", "未実行")
        job.last_error = data.get("last_error")
        return job


class AppSettings:
    def __init__(self):
        self.libreoffice_path: str = ""
        self.jobs: list = []
