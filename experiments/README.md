# Experiments
Runs comparisons using reusable components

## Overnight VLM batch (8-hour maximum)

From the `cv-data-extraction` directory:

```powershell
pipenv run python experiments/run_overnight.py
```

This uses `configs/vision_overnight.json`: all 34 locally available development
CVs (the seven VDAB PDFs are missing and excluded), one repetition, cached
Qwen3-VL-4B in 4-bit, 120-DPI source renders,
and at most 1,400,000 pixels per page supplied to the model (the original
120-DPI A4 page resolution). An opt-in attention adapter expands grouped KV
heads before SDPA, enabling PyTorch's memory-efficient attention kernel on the
installed Windows build instead of its memory-heavy math fallback. The adapter
is tested against native grouped-query attention for prefill, decode, and masks.
On CV002, smoke run `20261030T234353_b83756e0` completed in 118.5 seconds
(including worker startup), versus 3,901 seconds for the original structuring
stage. Generation improved from 0.43 to 19.97 tokens/s; peak allocated GPU
memory fell from 8.59 to 3.70 GiB. The parsed extraction was identical to the
original run, with the same 0.784 F1. This single-page check does not establish
throughput or success rate for the full dataset.
Original vision settings and historical results remain separate.

The supervisor enforces an eight-hour wall-clock deadline, including loading,
and fourteen minutes per document. It can finish earlier if all documents finish.
It does not guarantee successful extraction for all CVs. Each CV gets its own
process, so timeouts and CUDA failures release the model and let the batch
continue. Allocation is capped at 85% of GPU capacity to avoid silently spilling
into shared system memory. On CUDA OOM, a worker retries with half the pixel
budget, down to 65,536 pixels; retries share the same fourteen-minute allowance.
Failed retry artifacts are retained, and final request artifacts record the
actual image limit. Long or very dense documents may still fail or lose detail.

Model loading is offline using the existing Hugging Face cache. Windows sleep
is inhibited while the supervisor runs (keep the machine powered on). It saves
standard results and an incremental summary under `results/RUN_ID`; each attempt
also has `worker.log`. Evaluate normally afterward:

```powershell
pipenv run evaluate --run-ids RUN_ID
```

Limits can be changed with `--hours 8 --document-timeout-seconds 840`.
For a single-document check, use `--config experiments/configs/vision_overnight_smoke.json`.

## How to run
### 1) Make sure you have a config file you want to use.  
   For example:
```json
{
  "name": "pdf_text_baseline",
  "split": "development",
  "document_ids": ["CV001", "CV033"],
  "exclude_sources": ["vdab"],
  "repetitions": 5,
  "monitoring": {
    "memory": false,
    "sample_interval_ms": 10
  },
  "stages": [
    {
      "name": "read_pdf",
      "method": "pdf_text",
      "settings": {
        "sort_text": true
      }
    },
    {
      "name": "prepare_text",
      "method": "join_page_text",
      "settings": {
        "page_separator": "\n\n"
      }
    }
  ]
}
```
"document_ids": null, to select all documents inside the split.
### 2) run the run_experiment.py file  
   For example:
```cmd
python experiments/run_experiment.py --config experiments/configs/pdf_text_sorted.json
```
OR
```cmd
pipenv run experiment --config experiments/configs/pdf_text_sorted.json

pipenv run experiment --config experiments/configs/text_baseline.json

pipenv run experiment --config experiments/configs/vision_extraction.json
```

### 3) Evaluate the run
   For example:
```cmd
pipenv run evaluate --run-ids RUN_ID
```
"--overwrite": lets you overwrite an existing report for the RUN_ID

## VLM CPU offloading

`vision_extraction.json` enables `allow_cpu_offload` for the VLM stage. Accelerate
automatically distributes model weights over GPU 0 and CPU RAM when
needed. CUDA is still required. Set the option to `false` (or omit it) to retain
the original GPU-0-only loading behavior.

Automatic placement reserves 2 GiB of free memory on GPU 0 for image processing
and generation and budgets 80% of currently available system RAM for weights.
These budgets do not guarantee that every image/page count or output length fits
during generation. CPU offloading can substantially increase inference time.

The request records whether offloading is allowed; stage metrics record the actual
device map, input device, CPU placement and weight memory budgets. Compare timing
results with that placement information. This setting does not change the prompt
or evaluator, and existing text-baseline runs do not need to be repeated.
