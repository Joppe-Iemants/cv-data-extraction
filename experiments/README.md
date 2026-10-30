# Experiments
Runs comparisons using reusable components

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
