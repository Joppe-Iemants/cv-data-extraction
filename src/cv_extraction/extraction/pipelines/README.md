# Extraction pipelines

Start here to follow an extraction approach through the code. The JSON configs
are the executable stage definitions; these pages describe their composition.

| Pipeline | Stage sequence | Guide |
| --- | --- | --- |
| Text baseline | PDF → native page text → joined text → structured CV | [Text baseline](text_baseline/README.md) |
| Vision | PDF → page images → structured CV | [Vision](vision/README.md) |

## Where code belongs

- `pipelines/`: documentation and any future code unique to one approach.
- `components/`: reusable processing steps, grouped by PDF, text and structuring.
- `backends/`: model loading and service transport.
- `prompts/`: extraction instructions supplied to models.
- [registry.py](../registry.py): stage method names, functions, input/output kinds and settings.
- [engine.py](../engine.py): shared execution, timing, optional RAM monitoring and error handling.
- [Experiment configs](../../../../experiments/configs/): document selection, repetitions and stage settings.

All structured pipelines use [RawCV](../../schemas.py) and the same evaluation
code. Stage method names and output formats remain stable across the directory
reorganization, so saved run configs can still be replayed.

## Adding an approach

1. Add a config folder under `experiments/configs/` and compose existing stages.
2. Implement new reusable steps under `components/` and register them in `registry.py`.
3. Add a backend only when new model-loading or transport code is needed.
4. Add a pipeline guide here linking its config, components, prompts and backend.

For example, OCR can reuse PDF rendering and text structuring; multimodal
extraction can reuse text extraction and rendering; visual correction can reuse
the text baseline before introducing a correction step. These approaches are
not implemented yet.
