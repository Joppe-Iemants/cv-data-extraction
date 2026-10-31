from time import perf_counter

_RUNTIME = None
_RUNTIME_KEY = None

def get_vlm_runtime(model_id: str, load_in_4bit: bool, allow_cpu_offload: bool = False,
                    expand_kv_for_sdpa: bool = False) -> dict:
    global _RUNTIME, _RUNTIME_KEY

    runtime_key = (model_id, load_in_4bit, allow_cpu_offload, expand_kv_for_sdpa)

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
            # Transformers also requires this flag for mixed GPU/CPU 4-bit loading.
            llm_int8_enable_fp32_cpu_offload=allow_cpu_offload
        )

    placement = {"device_map": {"": 0}}
    if allow_cpu_offload:
        import psutil

        # Leave space for image activations and the generation KV cache.
        reserve_bytes = 2 * 1024 ** 3
        max_memory = {0: max(0, torch.cuda.mem_get_info(0)[0] - reserve_bytes)}
        max_memory["cpu"] = int(psutil.virtual_memory().available * 0.8)
        placement = {"device_map": "auto", "max_memory": max_memory}

    processor = AutoProcessor.from_pretrained(model_id)

    attention = 'sdpa'
    if expand_kv_for_sdpa:
        from .vlm_attention import register_expanded_kv_sdpa
        attention = register_expanded_kv_sdpa()

    model = Qwen3VLForConditionalGeneration.from_pretrained(
        model_id,
        quantization_config=quantization,
        **placement,
        dtype=torch.float16,
        attn_implementation=attention
    )

    model.eval()
    torch.cuda.synchronize(0)

    device_map = getattr(model, "hf_device_map", {"": str(model.device)})
    if any(str(device) == "disk" for device in device_map.values()):
        raise RuntimeError("The VLM exceeds the GPU/CPU memory budget; disk offloading is not enabled.")

    # Offloaded weights can reside on CPU while Accelerate executes them on GPU.
    # model.device alone can therefore point at the wrong device for the inputs.
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
