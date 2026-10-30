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
```

### 3) Evaluate the run
   For example:
```cmd
pipenv run evaluate --run-ids RUN_ID
```
"--overwrite": lets you overwrite an existing report for the RUN_ID