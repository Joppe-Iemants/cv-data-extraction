def recognize_page_images(data: dict, language: str, page_segmentation: int, timeout_seconds: int) -> dict:
    import pytesseract

    if not language.strip():
        raise ValueError("language must be nonempty.")

    if page_segmentation not in range(3, 14):
        raise ValueError("page_segmentation must be between 3 and 13.")

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive.")

    image_pages = data.get("pages", [])

    if not image_pages:
        raise ValueError("No page images were supplied.")

    pages = []

    for page in image_pages:
        text = pytesseract.image_to_string(
            page["image_path"],
            lang=language,
            config=f"--psm {page_segmentation} --dpi {data['dpi']}",
            timeout=timeout_seconds
        ).strip()

        pages.append({
            "page_number": page["page_number"],
            "text": text,
            "character_count": len(text)
        })

    character_count = sum(
        page["character_count"]
        for page in pages
    )

    pages_without_text = [
        page["page_number"]
        for page in pages
        if page["character_count"] == 0
    ]

    if character_count == 0:
        outcome = "empty_text"
    elif pages_without_text:
        outcome = "partial_text"
    else:
        outcome = "success"

    return {
        "data": {
            "page_count": len(pages),
            "pages": pages
        },
        "outcome": outcome,
        "metrics": {
            "engine": "tesseract",
            "engine_version": str(pytesseract.get_tesseract_version()),
            "language": language,
            "page_segmentation": page_segmentation,
            "dpi": data["dpi"],
            "page_count": len(pages),
            "character_count": character_count,
            "pages_without_text": pages_without_text
        }
    }