# Evaluation
Compares extracted data against reference answers

Run this to evaluate a run by its Id
```powershell
pipenv run evaluate --run-ids 20261029T215235_8e602a1a
```

## Found Problems
### Text baseline
Run: `20261029T215235_8e602a1a`

- **Results:** 122/170 attempts completed, 28 errored and 20 returned empty text.
- **Repetition loops:** 18 attempts reached the 8,192-token output limit (CV007, CV008, CV010, CV030).
- **Server errors:** CV009 failed all five attempts because the token repetition limit was reached.
- **Timeouts:** CV037, a 12-page CV, exceeded the 30-minute timeout in all five attempts.
- **Missing text:** Handwritten CVs CV033–CV036 returned no native text and require OCR or vision.
- **Unsupported output:** CV030 exposed only parser-directed instructions, while the model invented CV information and repeated skills.
- **Inconsistent completion:** CV008 and CV010 each completed only once across five repetitions.

- It appears CV30 is a deliberate prompt injection.

### Vision extraction

| Measurement | Before | After |
|---|---:|---:|
| Structuring stage, including model loading | 65 minutes | 1.93 minutes |
| Generation speed | 0.43 tokens/s | 19.97 tokens/s |
| Peak allocated GPU memory during generation | 8.59 GiB | 3.70 GiB |
| Parsed extraction | Same | Same |


#### **Efficient attention adapter**
  
| Measurement | Original baseline | Adapter + forced efficient SDPA |
|---|---:|---:|
| Structuring time, including loading | 65 minutes | **87 seconds** |
| Generation time | 3,884 seconds | **74 seconds** |
| Generation speed | 0.43 tokens/s | **22.72 tokens/s** |
| Peak allocated GPU memory | 8.59 GiB | **3.70 GiB** |
| Input tokens | 4,207 | 4,207 |
| Output tokens | 1,672 | 1,672 |
| Parsed extraction | Identical | Identical |

#### **logits_to_keep=1**

  - Test separately, then combine with the attention adapter.
  - Measure processing time and peak GPU memory.

- **Image resolution control**
  - Group the pixel limit and smaller-image retries together.
  - Measure processing time, memory, extraction accuracy, and success rate.

- **GPU memory allocation cap**
  - Test separately.
  - Measure memory use and out-of-memory failures.

- **Batch reliability**
  - Group process isolation, timeouts, progress saving, logging, and sleep prevention together.
  - Measure batch completion, failure recovery, and model-reloading overhead.