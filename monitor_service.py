"""登録されたジョブを一定周期でチェックし、更新されていれば変換するバックグラウンド監視。"""

import os
import threading
import time

import conversion_service
from conversion_service import ConversionResult


class MonitorService:
    def __init__(self, settings, base_dir, on_log=None, on_jobs_updated=None):
        self._settings = settings
        self._base_dir = base_dir
        self._on_log = on_log
        self._on_jobs_updated = on_jobs_updated

        self._running = threading.Event()
        self._thread = None
        self._next_run = {}
        # LibreOfficeのheadlessプロセスは同時に複数起動すると競合しやすいため、
        # 変換処理は常に1件ずつ直列で実行する。
        self._convert_lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._running.is_set()

    def start(self):
        if self._running.is_set():
            return
        now = time.time()
        for job in self._settings.jobs:
            self._next_run[job.id] = now
        self._running.set()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running.clear()

    def convert_now(self, job) -> ConversionResult:
        return self._process_job(job, force=True)

    def _run_loop(self):
        while self._running.is_set():
            now = time.time()
            for job in list(self._settings.jobs):
                if not self._running.is_set():
                    break
                if not job.enabled:
                    continue
                if now < self._next_run.get(job.id, 0):
                    continue
                self._next_run[job.id] = now + job.interval_seconds()
                self._process_job(job, force=False)

            # 1秒間隔でチェックしつつ、停止指示に素早く反応できるよう細かくsleepする
            for _ in range(10):
                if not self._running.is_set():
                    break
                time.sleep(0.1)

    def _process_job(self, job, force: bool) -> ConversionResult:
        with self._convert_lock:
            source_path = job.resolve_source_path(self._base_dir)
            if not os.path.isfile(source_path):
                job.last_status = "エラー"
                job.last_error = "ファイルが見つかりません"
                self._log(job, f"ファイルが見つかりません: {source_path}", True)
                self._notify_updated()
                return ConversionResult(False, job.last_error)

            mtime = os.path.getmtime(source_path)
            if not force and job.last_source_modified is not None and job.last_source_modified == mtime:
                # 前回変換時から更新されていないのでスキップ
                return ConversionResult(True, "", None)

            self._log(job, f"変換開始: {os.path.basename(source_path)}", False)
            result = conversion_service.convert(job, self._base_dir, self._settings.libreoffice_path)
            job.last_run = time.time()

            if result.success:
                job.last_source_modified = mtime
                job.last_status = "成功"
                job.last_error = None
                self._log(job, f"変換成功: {result.output_path}", False)
            else:
                job.last_status = "失敗"
                job.last_error = result.message
                self._log(job, f"変換失敗: {result.message}", True)

            self._notify_updated()
            return result

    def _log(self, job, message, is_error):
        if self._on_log:
            self._on_log(job, message, is_error)

    def _notify_updated(self):
        if self._on_jobs_updated:
            self._on_jobs_updated()
