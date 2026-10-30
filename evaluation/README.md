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