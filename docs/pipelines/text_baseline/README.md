# Text baseline

Extract native PDF text, join the pages, then ask a text model to produce a CV.
Image-only PDFs need another approach because this pipeline does not perform OCR.

| Stage name | Registered method | Implementation |
| --- | --- | --- |
| `read_pdf` | `pdf_text` | [PDF text extraction and stage wrapper](../../../src/cv_extraction/extraction/components/pdf/extract_text.py) |
| `prepare_text` | `join_page_text` | [Join page text](../../../src/cv_extraction/extraction/components/text/join_pages.py) |
| `structure_cv` | `llm_structuring` | [Structure CV from text](../../../src/cv_extraction/extraction/components/structuring/from_text.py) |

- [Baseline config](../../../experiments/configs/text_baseline/baseline.json)
- [Text prompt](../../../src/cv_extraction/extraction/prompts/text.py)
- [Ollama HTTP transport](../../../src/cv_extraction/extraction/backends/ollama.py)
- [Shared output schema](../../../src/cv_extraction/schemas.py)

The structuring component builds the CV request, checks backend completion,
validates the response and records metrics and artifacts. The backend sends the
HTTP request. The shared engine executes the stages in config order.

Run from the repository root:

```powershell
pipenv run experiment --config experiments/configs/text_baseline/baseline.json
```

For text extraction without a model, use
`experiments/configs/component_checks/pdf_text.json`.
