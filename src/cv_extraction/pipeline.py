from pathlib import Path
from time import perf_counter

from .methods.pdf_text import extract_pdf_text

def execute_stage(name: str, method: str, function, *args, **kwargs) -> dict:
    start = perf_counter()

    try:
        output = function(*args, **kwargs)
    except Exception as error:
        return {
            "report": {
                "name": name,
                "method": method,
                "execution_status": "error",
                "outcome": None,
                "metrics": {
                    "duration_seconds": perf_counter() - start
                },
                "error": {
                    "type": type(error).__name__,
                    "message": str(error)
                }
            },
            "output": None
        }

    return {
        "report": {
            "name": name,
            "method": method,
            "execution_status": "completed",
            "outcome": None,
            "metrics": {
                "duration_seconds": perf_counter() - start
            },
            "error": None
        },
        "output": output
    }

def run_extraction(pdf_path: Path, sort_text: bool = False, on_stage_finished=None) -> dict:
    stage = execute_stage(
        "read_pdf",
        "pdf_text",
        extract_pdf_text,
        pdf_path,
        sort_text=sort_text
    )

    stage_report = stage["report"]
    extracted_data = stage["output"]

    if stage_report["execution_status"] == "error":
        status = "error"
    else:
        pages = extracted_data["pages"]

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
            status = "empty_text"
        elif pages_without_text:
            status = "partial_text"
        else:
            status = "success"

        stage_report["outcome"] = status

        stage_report["metrics"].update({
            "page_count": extracted_data["page_count"],
            "character_count": character_count,
            "pages_without_text": pages_without_text
        })

    if on_stage_finished is not None:
        on_stage_finished(stage_report, extracted_data)

    return {
        "status": status,
        "metrics": {
            "extraction_seconds": (
                stage_report["metrics"]["duration_seconds"]
            )
        },
        "stages": [stage_report],
        "extracted_data": extracted_data
    }