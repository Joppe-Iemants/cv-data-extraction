from pathlib import Path

import pymupdf


def extract_layout_text(pdf_path: Path) -> dict:
    with pymupdf.open(pdf_path) as document:
        if document.needs_pass:
            raise ValueError("Password-protected PDFs are not supported.")

        if document.page_count == 0:
            raise ValueError("PDF contains no pages.")

        chunks = document.to_markdown(
            page_chunks=True,
            use_ocr=False,
            force_ocr=False,
            write_images=False,
            embed_images=False,
            force_text=True,
            header=True,
            footer=True
        )

        pages = []

        for chunk in chunks:
            text = chunk["text"]

            pages.append({
                "page_number": chunk["metadata"]["page_number"],
                "text": text,
                "character_count": len(text.strip())
            })

        return {
            "page_count": document.page_count,
            "pages": pages
        }
    
def read_layout_stage(pdf_path: Path) -> dict:
    data = extract_layout_text(pdf_path)

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