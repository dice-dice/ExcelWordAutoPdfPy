import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

import conversion_service
import libreoffice_locator
from models import ConversionJob

SOFFICE = libreoffice_locator.try_find()

pytestmark = pytest.mark.skipif(
    SOFFICE is None, reason="LibreOffice (soffice) not found in this environment"
)


@pytest.fixture
def xlsx_file(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    path = os.path.join(str(tmp_path), "sample.xlsx")
    wb = openpyxl.Workbook()
    wb.active["A1"] = "test"
    wb.save(path)
    return path


@pytest.fixture
def docx_file(tmp_path):
    docx = pytest.importorskip("docx")
    path = os.path.join(str(tmp_path), "sample.docx")
    document = docx.Document()
    document.add_paragraph("test document")
    document.save(path)
    return path


def test_overwrite_mode_creates_pdf_next_to_source(xlsx_file, tmp_path):
    job = ConversionJob()
    job.source_path = xlsx_file
    job.overwrite = True

    result = conversion_service.convert(job, str(tmp_path), SOFFICE)

    assert result.success, result.message
    expected = os.path.join(str(tmp_path), "sample.pdf")
    assert result.output_path == expected
    assert os.path.isfile(expected)
    assert os.path.getsize(expected) > 0


def test_rename_mode_with_custom_output_dir(docx_file, tmp_path):
    out_dir = os.path.join(str(tmp_path), "out")
    job = ConversionJob()
    job.source_path = docx_file
    job.overwrite = False
    job.output_file_name = "renamed_report"
    job.output_directory = out_dir

    result = conversion_service.convert(job, str(tmp_path), SOFFICE)

    assert result.success, result.message
    expected = os.path.join(out_dir, "renamed_report.pdf")
    assert result.output_path == expected
    assert os.path.isfile(expected)


def test_relative_source_path_resolves_against_base_dir(xlsx_file, tmp_path):
    job = ConversionJob()
    job.source_path = os.path.basename(xlsx_file)
    job.overwrite = True

    result = conversion_service.convert(job, str(tmp_path), SOFFICE)

    assert result.success, result.message
    assert os.path.isfile(result.output_path)


def test_missing_source_file_fails_gracefully(tmp_path):
    job = ConversionJob()
    job.source_path = "does_not_exist.xlsx"
    job.overwrite = True

    result = conversion_service.convert(job, str(tmp_path), SOFFICE)

    assert not result.success
    assert "見つかりません" in result.message


def test_missing_libreoffice_path_fails_gracefully(xlsx_file, tmp_path):
    job = ConversionJob()
    job.source_path = xlsx_file
    job.overwrite = True

    result = conversion_service.convert(job, str(tmp_path), "/nonexistent/soffice")

    assert not result.success
    assert "設定されていません" in result.message
