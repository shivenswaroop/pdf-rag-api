import fitz  # PyMuPDF


def extract_text(pdf_path: str):
    """
    Extract text page by page from a PDF.
    Returns:
        [
            {"page": 1, "text": "..."},
            {"page": 2, "text": "..."}
        ]
    """

    document = fitz.open(pdf_path)

    pages = []

    for page_num, page in enumerate(document, start=1):
        text = page.get_text()

        pages.append({
            "page": page_num,
            "text": text
        })

    document.close()

    return pages
