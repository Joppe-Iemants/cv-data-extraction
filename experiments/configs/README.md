# Experiment configurations

| Directory | Purpose |
| --- | --- |
| `text_baseline/` | Native PDF text → joined text → structured CV using Ollama |
| `vision/` | Rendered PDF pages → structured CV using Qwen3-VL |
| `component_checks/` | Partial pipelines that check text extraction or rendering without a model |

Each JSON file contains the full executable stage sequence and experiment
settings. Model, resolution and other variants belong beside the baseline for
their approach. Keep the `name` field descriptive when creating a new variant.

Moved configurations (contents unchanged):

| Previous path under `configs/` | Current path |
| --- | --- |
| `text_baseline.json` | `text_baseline/baseline.json` |
| `vision_extraction.json` | `vision/baseline.json` |
| `pdf_text_sorted.json` | `component_checks/pdf_text.json` |
| `vision_render_test.json` | `component_checks/pdf_render.json` |

See the [pipeline guides](../../src/cv_extraction/extraction/pipelines/README.md)
to follow each configuration into its implementation.
