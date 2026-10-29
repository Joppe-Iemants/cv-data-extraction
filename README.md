# cv-data-extraction
Bachelor’s thesis exploring efficient CV data extraction using PDF parsing, OCR, and vision-language models on limited hardware.

## Layout
| Repository directory | Purpose |
| --- | --- |
| `data/` | CV source files, reference annotations and archived runs |
| `experiments/` | Experiment configurations and execution entry point |
| `results/` | Extraction outputs and reports from experiment runs |
| `evaluation/` | Accuracy reports and notebooks for analysing evaluation results |
| `src/` | Python implementation of extraction, evaluation and monitoring |

| Directory under `src/cv_extraction/` | Purpose |
| --- | --- |
| `extraction/` | Extract and structure CV data |
| `evaluation/` | Compare extracted data against references and generate accuracy reports |
| `monitoring/` | Monitor hardware, memory usage and execution times |

```powershell
pipenv run experiment --config experiments/configs/pdf_text_llm.json
pipenv run evaluate --run-ids RUN_ID --allow-draft
```
