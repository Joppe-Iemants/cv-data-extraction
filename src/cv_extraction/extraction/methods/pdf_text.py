from pathlib import Path

import pymupdf


def extract_pdf_text(pdf_path: Path, sort_text: bool = False) -> dict:
    pages = []

    with pymupdf.open(pdf_path) as document:
        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text", sort=sort_text)

            pages.append({
                "page_number": page_number,
                "text": text,
                "character_count": len(text.strip()),
            })

    return {
        "page_count": len(pages),
        "pages": pages,
    }