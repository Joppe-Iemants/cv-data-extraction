# Experiments
Runs comparisons using reusable components

## How to run
1) Make sure you have a config file you want to use.  
   For example:
```json
{
  "name": "pdf_text_baseline",
  "method": "pdf_text",
  "settings": {
    "sort_text": false
  },
  "document_ids": null,
  "repetitions": 5
}
```
1) run the run_experiment.py file  
   For example:
```cmd
python experiments/run_experiment.py --config experiments/configs/pdf_text_sorted.json
```