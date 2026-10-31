import json
from contextlib import ExitStack
from time import perf_counter

from ...schemas import RawCV
from ..prompts.vision import build_vision_prompt
from .vlm_runtime import get_vlm_runtime


class VisionStructuringError(RuntimeError):
    def __init__(self, message: str, artifacts: dict):
        super().__init__(message)
        self.artifacts = artifacts


def structure_cv_images(
    data: dict, model_id: str, load_in_4bit: bool, max_new_tokens: int,
    allow_cpu_offload: bool = False
) -> dict:
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
        import torch
        from PIL import Image

        runtime = get_vlm_runtime(model_id, load_in_4bit, allow_cpu_offload)
        processor = runtime["processor"]
        model = runtime["model"]

        metrics = {
            "model": model_id,
            "model_load_seconds": runtime["model_load_seconds"],
            "model_reused": runtime["model_reused"],
            "input_device": runtime["input_device"],
            "device_map": runtime["device_map"],
            "cpu_offload_used": runtime["cpu_offload_used"],
            "max_memory": runtime["max_memory"],
            "page_count": len(pages)
        }
        artifacts["metrics"] = metrics

        torch.cuda.synchronize(0)
        preprocessing_start = perf_counter()

        with ExitStack() as stack:
            images = []

            for page in pages:
                source_image = stack.enter_context(Image.open(page["image_path"]))
                image = source_image.convert("RGB")
                stack.callback(image.close)
                images.append(image)

            content = [
                {"type": "image", "image": image}
                for image in images
            ]
            content.append({"type": "text", "text": prompt})

            messages = [
                {
                    "role": "user",
                    "content": content
                }
            ]

            inputs = processor.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_dict=True,
                return_tensors="pt"
            )

            inputs.pop("token_type_ids", None)
            inputs = inputs.to(runtime["input_device"])

        torch.cuda.synchronize(0)

        metrics["preprocessing_seconds"] = perf_counter() - preprocessing_start
        metrics["input_tokens"] = int(inputs["input_ids"].shape[1])

        torch.cuda.reset_peak_memory_stats(0)
        metrics["gpu_allocated_before_generation_bytes"] = int(torch.cuda.memory_allocated(0))

        generation_start = perf_counter()

        with torch.inference_mode():
            output = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                use_cache=True
            )

        torch.cuda.synchronize(0)
        generation_seconds = perf_counter() - generation_start

        generated_tokens = output[:, metrics["input_tokens"]:]
        output_tokens = int(generated_tokens.shape[1])

        response = processor.batch_decode(
            generated_tokens,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False
        )[0]

        artifacts["raw_response"] = response

        metrics.update({
            "generation_seconds": generation_seconds,
            "output_tokens": output_tokens,
            "output_tokens_per_second": output_tokens / generation_seconds if generation_seconds else None,
            "generation_peak_gpu_allocated_bytes": int(torch.cuda.max_memory_allocated(0)),
            "generation_peak_gpu_reserved_bytes": int(torch.cuda.max_memory_reserved(0)),
            "token_limit_reached": output_tokens >= max_new_tokens
        })

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

        raise VisionStructuringError(
            f"Vision extraction failed: {error}",
            artifacts
        ) from error
