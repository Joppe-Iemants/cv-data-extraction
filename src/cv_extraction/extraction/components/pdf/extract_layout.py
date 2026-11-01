from pathlib import Path

import pymupdf

from .helpers.multi_column import column_boxes


def extract_layout_text(pdf_path: Path) -> dict:
    pages = []

    with pymupdf.open(pdf_path) as document:
        if document.needs_pass:
            raise ValueError("Password-protected PDFs are not supported.")

        if document.page_count == 0:
            raise ValueError("PDF contains no pages.")

        for page_number, page in enumerate(document, start=1):
            boxes = column_boxes(
                page,
                header_margin=0,
                footer_margin=0,
                no_image_text=False
            )

            regions = []

            for region_number, box in enumerate(boxes, start=1):
                text = page.get_text(
                    "text",
                    clip=box,
                    sort=True
                ).strip()

                regions.append({
                    "region_number": region_number,
                    "bbox": list(box),
                    "text": text
                })

            native_text = page.get_text("text").strip()

            if native_text and not any(region["text"] for region in regions):
                raise ValueError(f"No text regions were extracted from page {page_number}, although native text exists.")

            pages.append({
                "page_number": page_number,
                "width": page.rect.width,
                "height": page.rect.height,
                "regions": regions
            })

    return {
        "page_count": len(pages),
        "pages": pages
    }


def read_layout_stage(pdf_path: Path) -> dict:
    data = extract_layout_text(pdf_path)

    return {
        "data": data,
        "outcome": "success",
        "metrics": {
            "page_count": data["page_count"],
            "region_count": sum(
                len(page["regions"])
                for page in data["pages"]
            )
        }
    }