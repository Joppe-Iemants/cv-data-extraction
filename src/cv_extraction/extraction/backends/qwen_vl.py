from contextlib import ExitStack
from time import perf_counter

_RUNTIME = None
_RUNTIME_KEY = None

def get_vlm_runtime(model_id: str, load_in_4bit: bool, allow_cpu_offload: bool = False) -> dict:
    global _RUNTIME, _RUNTIME_KEY

    runtime_key = (model_id, load_in_4bit, allow_cpu_offload)

    if _RUNTIME is not None:
        if runtime_key != _RUNTIME_KEY:
            raise ValueError("Use a separate experiment process when changing model, quantization or CPU offloading.")

        return {
            **_RUNTIME,
            "model_load_seconds": 0.0,
            "model_reused": True
        }

    import torch
    from transformers import AutoProcessor, BitsAndBytesConfig, Qwen3VLForConditionalGeneration

    if not torch.cuda.is_available():
        raise RuntimeError("This VLM runtime requires CUDA-enabled PyTorch and an NVIDIA GPU.")

    print(f"Loading VLM: {model_id}")
    start = perf_counter()

    quantization = None

    if load_in_4bit:
        quantization = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            llm_int8_enable_fp32_cpu_offload=allow_cpu_offload
        )

    placement = {"device_map": {"": 0}}
    if allow_cpu_offload:
        import psutil

        reserve_bytes = 2 * 1024 ** 3
        max_memory = {0: max(0, torch.cuda.mem_get_info(0)[0] - reserve_bytes)}
        max_memory["cpu"] = int(psutil.virtual_memory().available * 0.8)
        placement = {"device_map": "auto", "max_memory": max_memory}

    processor = AutoProcessor.from_pretrained(model_id)

    model = Qwen3VLForConditionalGeneration.from_pretrained(
        model_id,
        quantization_config=quantization,
        **placement,
        dtype=torch.float16,
        attn_implementation="sdpa"
    )

    model.eval()
    torch.cuda.synchronize(0)

    device_map = getattr(model, "hf_device_map", {"": str(model.device)})
    if any(str(device) == "disk" for device in device_map.values()):
        raise RuntimeError("The VLM exceeds the GPU/CPU memory budget; disk offloading is not enabled.")

    execution_device = getattr(getattr(model, "_hf_hook", None), "execution_device", None)
    if execution_device is None:
        execution_device = next(
            (device for device in device_map.values() if str(device) not in {"cpu", "disk"}),
            model.device
        )
    input_device = f"cuda:{execution_device}" if isinstance(execution_device, int) else str(execution_device)

    load_seconds = perf_counter() - start

    _RUNTIME = {
        "processor": processor,
        "model": model,
        "input_device": input_device,
        "device_map": {name: str(device) for name, device in device_map.items()},
        "cpu_offload_used": any(str(device) == "cpu" for device in device_map.values()),
        "max_memory": {str(device): budget for device, budget in placement.get("max_memory", {}).items()}
    }
    _RUNTIME_KEY = runtime_key

    return {
        **_RUNTIME,
        "model_load_seconds": load_seconds,
        "model_reused": False
    }


def generate_from_images(
    pages: list[dict], prompt: str, model_id: str, load_in_4bit: bool,
    max_new_tokens: int, allow_cpu_offload: bool = False, *, metrics: dict
) -> str:
    """Generate text from page images, updating metrics as work completes.

    The caller owns the metrics dictionary so partial measurements survive
    backend errors. CV prompts, schema validation and artifacts belong to the
    structuring component.
    """
    import torch
    from PIL import Image

    runtime = get_vlm_runtime(model_id, load_in_4bit, allow_cpu_offload)
    processor = runtime["processor"]
    model = runtime["model"]

    metrics.update({
        "model": model_id,
        "model_load_seconds": runtime["model_load_seconds"],
        "model_reused": runtime["model_reused"],
        "input_device": runtime["input_device"],
        "device_map": runtime["device_map"],
        "cpu_offload_used": runtime["cpu_offload_used"],
        "max_memory": runtime["max_memory"],
        "page_count": len(pages)
    })

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

    metrics.update({
        "generation_seconds": generation_seconds,
        "output_tokens": output_tokens,
        "output_tokens_per_second": output_tokens / generation_seconds if generation_seconds else None,
        "generation_peak_gpu_allocated_bytes": int(torch.cuda.max_memory_allocated(0)),
        "generation_peak_gpu_reserved_bytes": int(torch.cuda.max_memory_reserved(0)),
        "token_limit_reached": output_tokens >= max_new_tokens
    })

    return response
