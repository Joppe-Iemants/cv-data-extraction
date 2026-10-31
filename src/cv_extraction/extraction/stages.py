from pathlib import Path

from .methods.pdf_text import extract_pdf_text
from .methods.llm_structuring import structure_cv_text
from .methods.pdf_render import render_pdf
from .methods.vlm_structuring import structure_cv_images

def read_pdf_stage(pdf_path: Path, sort_text: bool) -> dict:
    data = extract_pdf_text(pdf_path, sort_text=sort_text)

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


STAGE_METHODS = {
    "pdf_text": {
        "function": read_pdf_stage,
        "input_kind": "pdf",
        "output_kind": "pages",
        "settings": {
            "sort_text": bool
        }
    },
    "join_page_text": {
        "function": prepare_text_stage,
        "input_kind": "pages",
        "output_kind": "text",
        "settings": {
            "page_separator": str
        }
    },
    "llm_structuring": {
        "function": structure_cv_text,
        "input_kind": "text",
        "output_kind": "cv",
        "settings": {
            "model": str,
            "base_url": str,
            "timeout_seconds": int,
            "options": dict,
            "keep_alive": str
        }
    },
    "render_pdf": {
        "function": render_pdf,
        "input_kind": "pdf",
        "output_kind": "images",
        "needs_stage_directory": True,
        "settings": {
            "dpi": int
        }
    },
    "vlm_structuring": {
        "function": structure_cv_images,
        "input_kind": "images",
        "output_kind": "cv",
        "settings": {
            "model_id": str,
            "load_in_4bit": bool,
            "max_new_tokens": int
        },
        "optional_settings": {
            "allow_cpu_offload": bool,
            "max_pixels": int,
            "gpu_memory_fraction": float,
            "expand_kv_for_sdpa": bool
        }
    }
}
