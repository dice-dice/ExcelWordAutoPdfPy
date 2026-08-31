import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import monitor_service as monitor_service_module
from conversion_service import ConversionResult
from models import AppSettings, ConversionJob
from monitor_service import MonitorService


def _make_job(tmp_path, interval_seconds=1):
    src = os.path.join(str(tmp_path), "sample.xlsx")
    with open(src, "w", encoding="utf-8") as f:
        f.write("v1")

    job = ConversionJob()
    job.source_path = src
    job.overwrite = True
    job.interval_value = interval_seconds
    job.interval_unit = "seconds"
    return job, src


def test_skips_conversion_when_file_unchanged(tmp_path, monkeypatch):
    calls = []

    def fake_convert(job, base_dir, soffice_path):
        calls.append(1)
        return ConversionResult(True, "", os.path.join(base_dir, "sample.pdf"))

    monkeypatch.setattr(monitor_service_module.conversion_service, "convert", fake_convert)

    job, src = _make_job(tmp_path, interval_seconds=1)
    settings = AppSettings()
    settings.libreoffice_path = "/fake/soffice"
    settings.jobs.append(job)

    monitor = MonitorService(settings, str(tmp_path))
    monitor.start()
    try:
        time.sleep(1.5)
        first_call_count = len(calls)
        assert first_call_count == 1

        time.sleep(1.5)
        assert len(calls) == first_call_count  # 変更なしなのでスキップされる

        with open(src, "w", encoding="utf-8") as f:
            f.write("v2-changed")
        time.sleep(1.5)
        assert len(calls) == first_call_count + 1  # 変更後は再変換される
    finally:
        monitor.stop()


def test_convert_now_ignores_change_detection(tmp_path, monkeypatch):
    calls = []

    def fake_convert(job, base_dir, soffice_path):
        calls.append(1)
        return ConversionResult(True, "", os.path.join(base_dir, "sample.pdf"))

    monkeypatch.setattr(monitor_service_module.conversion_service, "convert", fake_convert)

    job, _ = _make_job(tmp_path, interval_seconds=9999)
    settings = AppSettings()
    settings.libreoffice_path = "/fake/soffice"
    settings.jobs.append(job)

    monitor = MonitorService(settings, str(tmp_path))
    result1 = monitor.convert_now(job)
    result2 = monitor.convert_now(job)

    assert result1.success and result2.success
    assert len(calls) == 2  # 強制実行なので毎回変換される


def test_missing_file_reports_error(tmp_path, monkeypatch):
    def fake_convert(job, base_dir, soffice_path):
        raise AssertionError("should not be called when source file is missing")

    monkeypatch.setattr(monitor_service_module.conversion_service, "convert", fake_convert)

    job = ConversionJob()
    job.source_path = "does_not_exist.xlsx"
    settings = AppSettings()
    settings.jobs.append(job)

    monitor = MonitorService(settings, str(tmp_path))
    result = monitor.convert_now(job)

    assert not result.success
    assert job.last_status == "エラー"
