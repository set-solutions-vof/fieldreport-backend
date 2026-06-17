import fitz


def extract_text_from_pdf(data: bytes) -> str:
    document = fitz.open(stream=data, filetype="pdf")

    try:
        page_texts = [page.get_text("text").strip() for page in document]
    finally:
        document.close()

    return "\n\n".join(page_text for page_text in page_texts if page_text)
