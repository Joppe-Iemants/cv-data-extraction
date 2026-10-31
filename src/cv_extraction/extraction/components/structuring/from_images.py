import json

from ....schemas import RawCV
from ...prompts.vision import build_vision_prompt
from ...backends.qwen_vl import generate_from_images


class VisionStructuringError(RuntimeError):
    def __init__(self, message: str, artifacts: dict):
        super().__init__(message)
        self.artifacts = artifacts


def structure_cv_images(data: dict, model_id: str, load_in_4bit: bool, max_new_tokens: int, allow_cpu_offload: bool = False) -> dict:
    if max_new_tokens <= 0:
        raise ValueError("max_new_tokens must be positive.")

    pages = data.get("pages", [])

    if not pages:
        raise ValueError("No rendered pages were supplied.")

    page_numbers = [page["page_number"] for page in pages]

    if page_numbers != list(range(1, len(pages) + 1)):
        raise ValueError("Rendered pages must be ordered and numbered consecutively from 1.")

    prompt = build_vision_prompt()

    artifacts = {
        "request": {
            "model_id": model_id,
            "load_in_4bit": load_in_4bit,
            "allow_cpu_offload": allow_cpu_offload,
            "max_new_tokens": max_new_tokens,
            "do_sample": False,
            "dpi": data["dpi"],
            "pages": pages,
            "prompt": prompt
        },
        "raw_response": None,
        "metrics": {}
    }

    try:
        metrics = artifacts["metrics"]
        response = generate_from_images(
            pages, prompt, model_id, load_in_4bit, max_new_tokens,
            allow_cpu_offload, metrics=metrics
        )
        artifacts["raw_response"] = response

        response_text = response.strip()

        if response_text.startswith("```"):
            lines = response_text.splitlines()

            if len(lines) >= 2 and lines[-1].strip() == "```":
                response_text = "\n".join(lines[1:-1]).strip()

        parsed = json.loads(response_text)
        extracted = RawCV.model_validate(parsed)

        if metrics["token_limit_reached"]:
            raise ValueError("Generation reached the token limit; completeness cannot be confirmed.")

        return {
            "data": extracted.model_dump(mode="json"),
            "outcome": "success",
            "metrics": metrics,
            "artifacts": artifacts
        }

    except Exception as error:
        artifacts["error"] = {
            "type": type(error).__name__,
            "message": str(error)
        }

        raise VisionStructuringError(f'Vision extraction failed: {error}', artifacts) from error
