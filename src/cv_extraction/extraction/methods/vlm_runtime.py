from time import perf_counter

_RUNTIME = None
_RUNTIME_KEY = None

def get_vlm_runtime(model_id: str, load_in_4bit: bool) -> dict:
    global _RUNTIME, _RUNTIME_KEY

    runtime_key = (model_id, load_in_4bit)

    if _RUNTIME is not None:
        if runtime_key != _RUNTIME_KEY:
            raise ValueError("Use a separate experiment process when changing model or quantization.")

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
            bnb_4bit_use_double_quant=True
        )

    processor = AutoProcessor.from_pretrained(model_id)

    model = Qwen3VLForConditionalGeneration.from_pretrained(
        model_id,
        quantization_config=quantization,
        device_map={"": 0},
        dtype=torch.float16,
        attn_implementation="sdpa"
    )

    model.eval()
    torch.cuda.synchronize()

    load_seconds = perf_counter() - start

    _RUNTIME = {
        "processor": processor,
        "model": model
    }
    _RUNTIME_KEY = runtime_key

    return {
        **_RUNTIME,
        "model_load_seconds": load_seconds,
        "model_reused": False
    }