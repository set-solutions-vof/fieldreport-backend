from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.services import report_pdf
from tests.db.sqlalchemy_fakes import FakeResult, build_connection


def test_content_returns_reviewed_content_when_present() -> None:
    row = {"reviewed_content": ["reviewed"], "generated_content": ["generated"]}
    assert report_pdf._content(row) == "reviewed"


def test_content_falls_back_to_generated_when_no_reviewed() -> None:
    row = {"reviewed_content": None, "generated_content": ["generated"]}
    assert report_pdf._content(row) == "generated"


def test_content_returns_empty_when_both_absent() -> None:
    row = {"reviewed_content": None, "generated_content": None}
    assert report_pdf._content(row) == ""


async def test_fetch_image_bytes_returns_bytesio_on_success() -> None:
    with patch.object(report_pdf, "download_file", AsyncMock(return_value=(b"data", "image/jpeg"))):
        result = await report_pdf._fetch_image_bytes("photos/img.jpg")

    assert isinstance(result, BytesIO)
    assert result.read() == b"data"


async def test_fetch_image_bytes_returns_none_on_error() -> None:
    with patch.object(report_pdf, "download_file", AsyncMock(side_effect=Exception("not found"))):
        result = await report_pdf._fetch_image_bytes("photos/missing.jpg")

    assert result is None


async def test_render_report_to_pdf_returns_pdf_bytes() -> None:
    report_id = str(uuid4())
    company_id = str(uuid4())
    fake_pdf = b"%%PDF fake"
    fake_docx = b"PK fake docx"

    results = [
        FakeResult(row={"docx_storage_key": "tpl/key.docx"}),
        FakeResult(row={"metadata": {"projectnummer": "P001", "opdrachtgever": "ACME"}}),
        FakeResult(rows=[
            {
                "section_id": "panel_paneelnummer",
                "reviewed_content": None,
                "generated_content": ["Panel 1"],
            },
            {
                "section_id": "panel_conclusie",
                "reviewed_content": ["Rev conclusie"],
                "generated_content": ["Gen conclusie"],
            },
        ]),
        FakeResult(rows=[
            {"storage_key": "photos/photo1.jpg"},
            {"storage_key": "photos/photo2.jpg"},
        ]),
    ]
    connection = build_connection(results=results)
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

    def fake_soffice(cmd, **kwargs):
        docx_path = cmd[-1]
        pdf_path = docx_path.replace(".docx", ".pdf")
        with open(pdf_path, "wb") as f:
            f.write(fake_pdf)
        return MagicMock(returncode=0, stderr=b"")

    mock_tpl = MagicMock()
    mock_tpl.save.side_effect = lambda path: open(path, "wb").write(b"docx content")

    with (
        patch.object(report_pdf, "get_database", return_value=pool),
        patch.object(
            report_pdf,
            "download_file",
            AsyncMock(side_effect=[
                (fake_docx, "application/vnd.openxmlformats"),
                (b"photo1", "image/jpeg"),
                (b"photo2", "image/jpeg"),
            ]),
        ),
        patch.object(report_pdf, "DocxTemplate", return_value=mock_tpl),
        patch.object(report_pdf, "InlineImage", return_value="PHOTO"),
        patch("subprocess.run", side_effect=fake_soffice),
    ):
        result = await report_pdf.render_report_to_pdf(report_id, company_id)

    assert result == fake_pdf
    mock_tpl.render.assert_called_once()
    panels = mock_tpl.render.call_args.args[0]["panels"]
    assert len(panels) == 1
    assert panels[0]["paneelnummer"] == "Panel 1"
    assert panels[0]["conclusie"] == "Rev conclusie"
    assert panels[0]["projectnummer"] == "P001"


async def test_render_report_to_pdf_raises_when_libreoffice_fails() -> None:
    report_id = str(uuid4())
    company_id = str(uuid4())
    fake_docx = b"PK fake docx"

    results = [
        FakeResult(row={"docx_storage_key": "tpl/key.docx"}),
        FakeResult(row={"metadata": {}}),
        FakeResult(rows=[]),
        FakeResult(rows=[]),
    ]
    connection = build_connection(results=results)
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

    mock_tpl = MagicMock()
    mock_tpl.save.side_effect = lambda path: open(path, "wb").write(b"docx")

    with (
        patch.object(report_pdf, "get_database", return_value=pool),
        patch.object(
            report_pdf,
            "download_file",
            AsyncMock(return_value=(fake_docx, "application/vnd.openxmlformats")),
        ),
        patch.object(report_pdf, "DocxTemplate", return_value=mock_tpl),
        patch("subprocess.run", return_value=MagicMock(returncode=1, stderr=b"LibreOffice error")),
    ):
        try:
            await report_pdf.render_report_to_pdf(report_id, company_id)
        except RuntimeError as error:
            assert "LibreOffice conversion failed" in str(error)
        else:
            raise AssertionError("Expected RuntimeError")
