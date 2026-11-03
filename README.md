# CV Data Extraction
Bachelor’s thesis comparing methods for extracting structured data from CVs, with a focus on reducing processing time and hardware requirements.

## Pipelines 
✅ Supported · ❌ Unsupported · ⚠️ Not always · ❓ Needs testing

| Pipeline | Native PDF text | Image-only scans | Columns and reading order | Graphical ratings | Charts and diagrams | Implemented? | Tested? |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Text baseline** | ✅ | ❌ | ⚠️ | ⚠️ | ❌ | ✅ | ✅ |
| **Layout-aware text** | ❓ | ❓ | ❓ | ❓ | ❓ | ✅ | ⬜ |
| **OCR extraction** | ❓ | ❓ | ❓ | ❓ | ❓ | ✅ | ⬜ |
| **Vision extraction** | ❓ | ❓ | ❓ | ❓ | ❓ | ✅ | ⬜ |
| **Multimodal extraction** | ❓ | ❓ | ❓ | ❓ | ❓ | ⬜ | ⬜ |
| **Visual correction** | ❓ | ❓ | ❓ | ❓ | ❓ | ⬜ | ⬜ |
| **Targeted vision** | ❓ | ❓ | ❓ | ❓ | ❓ | ⬜ | ⬜ |
| **Adaptive extraction** | ❓ | ❓ | ❓ | ❓ | ❓ | ⬜ | ⬜ |


| Name | Description |
| --- | --- |
| **Text baseline** | Extract native PDF text, combine the page text and use an LLM to structure the CV data. |
| **Layout-aware text** | Extract positioned text blocks, reconstruct columns and reading order, then use an LLM to structure the data. |
| **OCR extraction** | Render PDF pages as images, recognise text with OCR and use an LLM to structure the data. |
| **Vision extraction** | Render PDF pages as images and use a VLM to extract structured CV data directly. |
| **Multimodal extraction** | Supply native PDF text and page images together to a VLM for structured extraction. |
| **Visual correction** | Extract an initial structured representation using the text baseline, then use a VLM to review and correct it against page images. |
| **Targeted vision** | Extract native text and use a VLM on selected graphical regions, then combine the information into structured CV data. |
| **Adaptive extraction** | Inspect each document and route it through text extraction, OCR or vision processing based on its characteristics. |


## Layout
Start with the [pipeline guides](docs/pipelines/README.md)
to follow an approach from its config to its components, prompt and backend.

| Repository directory | Purpose |
| --- | --- |
| `data/` | CV source files, reference annotations and archived runs |
| `docs/pipelines/` | Guides showing how each extraction approach is composed |
| `experiments/` | Experiment configurations and execution entry point |
| `results/` | Extraction outputs and reports from experiment runs |
| `evaluation/` | Accuracy reports and notebooks for analysing evaluation results |
| `src/` | Python implementation of extraction, evaluation and monitoring |

| Directory under `src/cv_extraction/` | Purpose |
| --- | --- |
| `extraction/` | Extract and structure CV data |
| `evaluation/` | Compare extracted data against references and generate accuracy reports |
| `monitoring/` | Monitor hardware, memory usage and execution times |

| Directory under `extraction/` | Purpose |
| --- | --- |
| `components/pdf/` | Native PDF text extraction and page rendering |
| `components/text/` | Text preparation |
| `components/structuring/` | Convert text or images into the shared CV schema |
| `backends/` | Ollama HTTP transport and Qwen model loading, input processing and generation |
| `prompts/` | Text and vision extraction instructions |

`extraction/engine.py` executes stages; `extraction/registry.py` registers their
functions and settings. [Experiment configs](experiments/configs/README.md) are
grouped by approach, with model-free checks in `component_checks/`.

```powershell
pipenv run experiment --config experiments/configs/text_baseline/baseline.json
pipenv run evaluate --run-ids RUN_ID
```

