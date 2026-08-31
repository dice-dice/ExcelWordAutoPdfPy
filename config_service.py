"""設定ファイル(config.json)の読み書き。アプリの実行フォルダに保存する。"""

import json
import os

from models import AppSettings, ConversionJob

CONFIG_FILENAME = "config.json"


def get_config_path(base_dir: str) -> str:
    return os.path.join(base_dir, CONFIG_FILENAME)


def load(base_dir: str) -> AppSettings:
    settings = AppSettings()
    path = get_config_path(base_dir)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            settings.libreoffice_path = data.get("libreoffice_path", "")
            settings.jobs = [ConversionJob.from_dict(j) for j in data.get("jobs", [])]
        except (OSError, ValueError):
            # 設定ファイルが壊れている場合は新規作成として扱う
            pass
    return settings


def save(base_dir: str, settings: AppSettings) -> None:
    path = get_config_path(base_dir)
    data = {
        "libreoffice_path": settings.libreoffice_path,
        "jobs": [job.to_dict() for job in settings.jobs],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
