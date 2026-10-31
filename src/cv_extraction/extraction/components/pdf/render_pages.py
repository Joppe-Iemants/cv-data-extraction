from pathlib import Path

import pymupdf

def render_pdf(pdf_path: Path, dpi: int,stage_directory: Path) -> dict:
    if type(dpi) is not int or dpi <= 0:
        raise ValueError("dpi must be a positive integer.")

    images_directory = stage_directory / "images"
    images_directory.mkdir(parents=True, exist_ok=True)

    pages = []

    with pymupdf.open(pdf_path) as document:
        if document.needs_pass:
            raise ValueError("Password-protected PDFs are not supported.")

        if document.page_count == 0:
            raise ValueError("PDF contains no pages.")

        for page_number, page in enumerate(document, start=1):
            pixmap = page.get_pixmap(
                dpi=dpi,
                colorspace=pymupdf.csRGB,
                alpha=False
            )

            image_path = images_directory / f"page_{page_number:03d}.png"
            pixmap.save(str(image_path))

            pages.append({
                "page_number": page_number,
                "image_path": str(image_path.resolve()),
                "width": pixmap.width,
                "height": pixmap.height
            })

    return {
        "data": {
            "page_count": len(pages),
            "dpi": dpi,
            "pages": pages
        },
        "outcome": "success",
        "metrics": {
            "page_count": len(pages),
            "dpi": dpi,
            "total_pixels": sum(
                page["width"] * page["height"]
                for page in pages
            )
        }
    }