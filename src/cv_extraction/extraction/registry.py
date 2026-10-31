from .components.pdf.extract_text import read_pdf_stage
from .components.pdf.render_pages import render_pdf
from .components.text.join_pages import prepare_text_stage
from .components.structuring.from_text import structure_cv_text
from .components.structuring.from_images import structure_cv_images


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
            "allow_cpu_offload": bool
        }
    }
}
