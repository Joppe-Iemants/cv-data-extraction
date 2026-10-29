# cv-data-extraction
Bachelor’s thesis exploring efficient CV data extraction using PDF parsing, OCR, and vision-language models on limited hardware.

## Source layout

| Location under `src/cv_extraction/` | Responsibility |
| --- | --- |
| `extraction/pipeline.py`, `stages.py`, `methods/` | Execute extraction stages and their implementations |
| `evaluation/runner.py` | Load saved runs/references and write accuracy reports |
| `evaluation/matching.py` | Align reference and predicted records |
| `evaluation/scoring.py` | Compare facts, calculate metrics and prepare manual review |
| `evaluation/normalization.py` | Normalize text for matching and comparison |
| `evaluation/__main__.py` | Evaluation command-line entry point |
| `monitoring/hardware.py`, `memory.py`, `reporting.py` | Hardware capture, memory monitoring and timing summaries |
| `schemas.py`, `config.py`, `storage.py` | Shared data contract, configuration validation and JSON storage |

Notebooks and generated evaluation results stay in the top-level `evaluation/`
directory. Experiment entry points/configurations stay in `experiments/`.

```powershell
pipenv run experiment --config experiments/configs/pdf_text_llm.json
pipenv run evaluate --run-ids RUN_ID --allow-draft
```
