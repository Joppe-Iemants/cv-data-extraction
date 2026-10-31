# Vision extraction

Render every PDF page, then send all page images together to Qwen3-VL in one
request to produce a structured CV. Native PDF text is not used.

| Stage name | Registered method | Implementation |
| --- | --- | --- |
| `render_pages` | `render_pdf` | [Render page PNGs](../../../src/cv_extraction/extraction/components/pdf/render_pages.py) |
| `structure_cv` | `vlm_structuring` | [Structure CV from images](../../../src/cv_extraction/extraction/components/structuring/from_images.py) |

- [Baseline config](../../../experiments/configs/vision/baseline.json)
- [Vision prompt](../../../src/cv_extraction/extraction/prompts/vision.py)
- [Qwen model runtime](../../../src/cv_extraction/extraction/backends/qwen_vl.py)
- [Shared output schema](../../../src/cv_extraction/schemas.py)

The image component builds the CV prompt, validates the response and records
metrics and artifacts. The backend loads the model, processes page images, places
tensors on the execution device, generates and decodes text, and measures model
execution. It also handles quantization, placement and reuse within the process.
CUDA is required even when CPU offloading is enabled.

Run from the repository root:

```powershell
pipenv run experiment --config experiments/configs/vision/baseline.json
```

For rendering without loading a model, use
`experiments/configs/component_checks/pdf_render.json`.

The baseline config currently uses 120 DPI, Qwen3-VL-4B-Instruct, 4-bit loading,
an 8,192-token output limit and CPU offloading disabled. Change model or placement
settings in a separate experiment process because the backend caches its runtime.
