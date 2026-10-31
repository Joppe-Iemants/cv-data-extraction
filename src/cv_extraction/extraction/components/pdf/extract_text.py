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
                "character_count": len(text.strip())
            })

    return {
        "page_count": len(pages),
        "pages": pages
    }

def read_pdf_stage(pdf_path: Path, sort_text: bool) -> dict:
    data = extract_pdf_text(pdf_path, sort_text=sort_text)

    character_count = sum(
        page["character_count"]
        for page in data["pages"]
    )

    pages_without_text = [
        page["page_number"]
        for page in data["pages"]
        if page["character_count"] == 0
    ]

    if character_count == 0:
        outcome = "empty_text"
    elif pages_without_text:
        outcome = "partial_text"
    else:
        outcome = "success"

    return {
        "data": data,
        "outcome": outcome,
        "metrics": {
            "page_count": data["page_count"],
            "character_count": character_count,
            "pages_without_text": pages_without_text
        }
    }
