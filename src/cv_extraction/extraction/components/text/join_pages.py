def prepare_text_stage(data: dict, page_separator: str) -> dict:
    text = page_separator.join(
        page["text"]
        for page in data["pages"]
    )

    return {
        "data": {
            "text": text,
            "page_count": data["page_count"]
        },
        "outcome": "success" if text.strip() else "empty_text",
        "metrics": {
            "character_count": len(text.strip())
        }
    }


