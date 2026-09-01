import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import app


def test_source_mode_returns_script_directory():
    assert app.get_base_dir() == os.path.dirname(os.path.abspath(app.__file__))


def test_frozen_windows_exe_returns_executable_directory(monkeypatch):
    # os.path はテスト実行OSにひもづくため、バックスラッシュ区切りはこのテストでは検証できない。
    # ここではダーウィン以外なら exe_dir をそのまま返すという分岐だけを検証する。
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "executable", "C:/Users/someone/Desktop/ExcelWordAutoPdf.exe")

    assert app.get_base_dir() == "C:/Users/someone/Desktop"


def test_frozen_macos_app_bundle_returns_folder_containing_app(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(
        sys,
        "executable",
        "/Users/someone/Desktop/ExcelWordAutoPdf.app/Contents/MacOS/ExcelWordAutoPdf",
    )

    assert app.get_base_dir() == "/Users/someone/Desktop"


def test_frozen_macos_onefile_without_app_bundle_returns_executable_directory(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(sys, "executable", "/Users/someone/Desktop/ExcelWordAutoPdf")

    assert app.get_base_dir() == "/Users/someone/Desktop"
