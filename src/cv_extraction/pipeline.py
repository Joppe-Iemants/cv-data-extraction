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

    return {
        "document": pdf_path.name,
        "method": "pdf_text",
        "settings": {
            "sort_text": sort_text,
        },
        "metrics": {
            "extraction_seconds": elapsed,
        },
        "extracted_data": extracted_data,
    }