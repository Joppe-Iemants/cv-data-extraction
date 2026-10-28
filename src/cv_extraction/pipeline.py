from pathlib import Path
from time import perf_counter

from .methods.pdf_text import extract_pdf_text


def run_extraction(pdf_path: Path, sort_text: bool = False) -> dict:
    start = perf_counter()

    extracted_data = extract_pdf_text(
        pdf_path,
        sort_text=sort_text,
    )

    elapsed = perf_counter() - start

    pages = extracted_data["pages"]
    character_count = sum(page["character_count"] for page in pages)

    pages_without_text = [
        page["page_number"]
        for page in pages
        if page["character_count"] == 0
    ]

    if character_count == 0:
        status = "empty_text"
    elif pages_without_text:
        status = "partial_text"
    else:
        status = "success"
        
    return {
        "status": status,
        "metrics": {
            "extraction_seconds": elapsed,
            "page_count": extracted_data["page_count"],
            "character_count": character_count,
            "pages_without_text": pages_without_text,
        },
        "extracted_data": extracted_data,
    }