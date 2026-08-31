import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config_service
from models import AppSettings, ConversionJob


def test_save_and_load_round_trip(tmp_path):
    settings = AppSettings()
    settings.libreoffice_path = "/usr/bin/soffice"

    job = ConversionJob()
    job.source_path = "sample.xlsx"
    job.overwrite = False
    job.output_file_name = "report"
    job.output_directory = "out"
    job.interval_value = 5
    job.interval_unit = "hours"
    job.enabled = False
    job.last_source_modified = 12345.0
    job.last_run = 67890.0
    job.last_status = "成功"
    settings.jobs.append(job)

    base_dir = str(tmp_path)
    config_service.save(base_dir, settings)

    loaded = config_service.load(base_dir)
    assert loaded.libreoffice_path == "/usr/bin/soffice"
    assert len(loaded.jobs) == 1

    loaded_job = loaded.jobs[0]
    assert loaded_job.source_path == "sample.xlsx"
    assert loaded_job.overwrite is False
    assert loaded_job.output_file_name == "report"
    assert loaded_job.output_directory == "out"
    assert loaded_job.interval_value == 5
    assert loaded_job.interval_unit == "hours"
    assert loaded_job.enabled is False
    assert loaded_job.last_source_modified == 12345.0
    assert loaded_job.last_run == 67890.0
    assert loaded_job.last_status == "成功"


def test_load_missing_file_returns_defaults(tmp_path):
    settings = config_service.load(str(tmp_path))
    assert settings.libreoffice_path == ""
    assert settings.jobs == []


def test_load_corrupt_file_returns_defaults(tmp_path):
    config_path = os.path.join(str(tmp_path), "config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        f.write("{not valid json")

    settings = config_service.load(str(tmp_path))
    assert settings.libreoffice_path == ""
    assert settings.jobs == []
