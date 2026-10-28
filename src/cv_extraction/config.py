import json
from pathlib import Path


def select_split(documents: list[dict], splits_path: Path, split_name: str) -> list[dict]:
    splits = json.loads(splits_path.read_text(encoding="utf-8"))

    if split_name not in splits:
        raise ValueError(f"Unknown dataset split: {split_name}")

    available_ids = {document["id"] for document in documents}

    assigned_ids = [
        document_id
        for split_ids in splits.values()
        for document_id in split_ids
    ]

    unknown_ids = set(assigned_ids) - available_ids

    if unknown_ids:
        raise ValueError(f"Split file contains unknown document IDs: {sorted(unknown_ids)}")

    if len(assigned_ids) != len(set(assigned_ids)):
        raise ValueError("Document IDs must not appear more than once in the split file." )

    selected_ids = set(splits[split_name])

    if not selected_ids:
        raise ValueError(f"Dataset split is empty: {split_name}")

    return [
        document
        for document in documents
        if document["id"] in selected_ids
    ]