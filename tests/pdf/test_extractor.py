from pathlib import Path

import fitz

from src.pdf import extractor


def test_extract_text_from_pdf_returns_joined_page_text(tmp_path: Path) -> None:
    pdf_path = tmp_path / "report.pdf"
    document = fitz.open()
    document.new_page()
    document.new_page()
    first_page = document[0]
    second_page = document[1]
    first_page.insert_text((72, 72), "Summary page")
    second_page.insert_text((72, 72), "Findings page")
    document.save(pdf_path)
    document.close()

    result = extractor.extract_text_from_pdf(str(pdf_path))

    assert result == "Summary page\n\nFindings page"
