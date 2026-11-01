import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

SOURCE = Path(os.environ.get("NODEJAM_PDF_READ_SOURCE", Path(__file__).parents[1] / "scripts/pdf_read.py"))
spec = importlib.util.spec_from_file_location("pdf_read_contract", SOURCE)
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


@pytest.fixture
def mixed_pdf(tmp_path):
    path = tmp_path / "Östersund.pdf"
    pdf = canvas.Canvas(str(path), pagesize=(300, 400))
    pdf.drawString(30, 350, "Östersund – Vänner, böcker och ljus.")
    pdf.showPage()
    pdf.setPageRotation(90)
    pdf.showPage()
    pdf.setPageRotation(0)
    picture = io.BytesIO()
    Image.new("RGB", (20, 20), "navy").save(picture, format="PNG")
    for whitespace in (False, True):
        pdf.drawImage(ImageReader(picture), 30, 30, width=100, height=100)
        if whitespace:
            pdf.drawString(30, 350, "   ")
        pdf.showPage()
    for index in range(2000):
        pdf.line(index % 300, 0, index % 300, 400)
    pdf.showPage()
    pdf.save()
    return path


def forbid_python_drawing_parser(monkeypatch):
    need = reader._need

    def require(module, package):
        if module == "pdfplumber":
            raise AssertionError("Text/metadata must use the bundled native reader, not parse drawing paths in Python")
        return need(module, package)

    monkeypatch.setattr(reader, "_need", require)


def test_text_keeps_unicode_page_boundaries_and_empty_pages(mixed_pdf, monkeypatch):
    forbid_python_drawing_parser(monkeypatch)
    data = reader.read_text(str(mixed_pdf), None)
    assert data["page_count"] == 5
    assert "Östersund – Vänner, böcker och ljus." in data["pages"][0]
    assert all(not text.strip() for text in data["pages"][1:])
    assert all("\r\n" not in text for text in data["pages"])


def test_metadata_distinguishes_image_only_blank_and_vector_pages(mixed_pdf, monkeypatch):
    forbid_python_drawing_parser(monkeypatch)
    data = reader.read_meta(str(mixed_pdf), None)
    assert data["page_count"] == 5
    assert data["pages"][0]["width"] == 300
    assert data["pages"][0]["height"] == 400
    assert data["pages"][1]["rotation"] == 90
    assert data["likely_scanned_pages"] == [3, 4]


@pytest.fixture
def encrypted_pdf(mixed_pdf, tmp_path):
    path = tmp_path / "locked.pdf"
    writer = PdfWriter(clone_from=PdfReader(mixed_pdf))
    writer.encrypt("fixture-password")
    writer.write(path)
    return path


@pytest.mark.parametrize("password", [None, "wrong"])
def test_locked_metadata_does_not_claim_to_read_pages(encrypted_pdf, password):
    data = reader.read_meta(str(encrypted_pdf), password)
    assert data["encrypted"] is True
    assert "page_count" not in data
    assert "password" in data["note"]


def test_supplied_password_reads_encrypted_text_and_scan_flags(encrypted_pdf):
    assert "Östersund" in reader.read_text(str(encrypted_pdf), "fixture-password")["pages"][0]
    assert reader.read_meta(str(encrypted_pdf), "fixture-password")["likely_scanned_pages"] == [3, 4]


def test_cli_keeps_json_shape_and_source_bytes(mixed_pdf):
    digest = hashlib.sha256(mixed_pdf.read_bytes()).hexdigest()
    for mode in ("--meta", "--text"):
        result = subprocess.run([sys.executable, str(SOURCE), str(mixed_pdf), mode], capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["page_count"] == 5
        assert len(data["pages"]) == 5
    assert hashlib.sha256(mixed_pdf.read_bytes()).hexdigest() == digest
