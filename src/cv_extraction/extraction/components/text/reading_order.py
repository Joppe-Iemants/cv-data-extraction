def split_at_gap(regions: list[dict], axis: int, min_gap: int) -> tuple:
    ordered = sorted(
        regions,
        key=lambda region: region["text_bbox"][axis]
    )

    boundary = ordered[0]["text_bbox"][axis + 2]
    best_gap = 0
    split_index = None

    for index in range(1, len(ordered)):
        box = ordered[index]["text_bbox"]
        gap = box[axis] - boundary

        if gap >= min_gap and gap > best_gap:
            best_gap = gap
            split_index = index

        boundary = max(boundary, box[axis + 2])

    if split_index is None:
        return [], []

    return ordered[:split_index], ordered[split_index:]


def order_regions(regions: list[dict], min_gap: int) -> list[dict]:
    if len(regions) <= 1:
        return regions

    for axis in (0, 1):
        first, second = split_at_gap(regions, axis, min_gap)

        if first:
            return order_regions(first, min_gap) + order_regions(second, min_gap)

    return sorted(
        regions,
        key=lambda region: (
            region["text_bbox"][1],
            region["text_bbox"][0]
        )
    )


def prepare_reading_order_stage(data: dict, min_gap: int) -> dict:
    if min_gap <= 0:
        raise ValueError("min_gap must be positive.")

    pages = []

    for page in data["pages"]:
        regions = [
            region
            for region in page["regions"]
            if region["text"].strip()
        ]

        ordered = order_regions(regions, min_gap)

        text = "\n\n".join(
            region["text"].strip()
            for region in ordered
        )

        pages.append({
            "page_number": page["page_number"],
            "text": text,
            "character_count": len(text.strip()),
            "region_order": [
                region["region_number"]
                for region in ordered
            ]
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
            "page_count": data["page_count"],
            "pages": pages
        },
        "outcome": outcome,
        "metrics": {
            "character_count": character_count,
            "pages_without_text": pages_without_text
        }
    }