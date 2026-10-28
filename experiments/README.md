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
```

### 3) Evaluate the run
   For example:
```cmd
pipenv run python -m cv_extraction.evaluation --reference data/references/CV001.json --prediction results/RUN_ID/documents/CV001/repeat_001/structure_cv/extraction.json --output results/RUN_ID/documents/CV001/repeat_001/structure_cv/evaluation.json
```
