import json
from pathlib import Path

from .extraction.stages import STAGE_METHODS

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

def validate_stages(stages: list[dict]) -> None:
    if not isinstance(stages, list) or not stages:
        raise ValueError("stages must be a nonempty list.")

    names = set()
    available_kind = "pdf"

    for stage in stages:
        name = stage["name"]
        method = stage["method"]
        settings = stage["settings"]

        if not isinstance(name, str) or not name.isidentifier():
            raise ValueError(
                "Stage names must be valid identifiers, such as read_pdf."
            )

        if name in names:
            raise ValueError(f"Duplicate stage name: {name}")

        names.add(name)

        if method not in STAGE_METHODS:
            raise ValueError(f"Unknown stage method: {method}")

        definition = STAGE_METHODS[method]

        if definition["input_kind"] != available_kind:
            raise ValueError(
                f"Stage {name} requires {definition['input_kind']}, "
                f"but the previous output is {available_kind}."
            )

        expected_settings = definition["settings"]

        if not isinstance(settings, dict):
            raise ValueError(f"Settings for {name} must be an object.")

        if set(settings) != set(expected_settings):
            raise ValueError(
                f"Stage {name} requires these settings: "
                f"{sorted(expected_settings)}"
            )

        for key, expected_type in expected_settings.items():
            if type(settings[key]) is not expected_type:
                raise ValueError(
                    f"Invalid type for {name}.{key}; "
                    f"expected {expected_type.__name__}."
                )

        available_kind = definition["output_kind"]