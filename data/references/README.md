# Reference annotations

All 41 PDFs listed in `../manifest.json` have a `CVxxx.json` reference in the project's `RawCV` (`compact-v1`) schema. CV013-CV016 are not in this dataset. Existing CV001, CV002 and CV012 JSON annotations were preserved; 38 references were added on 2026-10-30.

## Sources and review

- CV003-CV011, CV017-CV024 and CV039-CV045: source PDF transcriptions, with graphical labels checked on rendered pages. Shared template content is represented consistently, while dates, wording and layout-specific content remain separate.
- CV025-CV036: adapted from the local Careerflow ResumeExtractBench `ground_truth` labels in `CV-research-collection/sources/Careerflow__ResumeExtractBench/`. Visible employment dates, qualifications and selected other facts were supplemented from the PDFs, including handwritten scans. Publisher labels are not complete transcriptions; an independent exhaustive human review is still needed before treating these as a final gold-standard dataset.
- CV037: core career and education records transcribed; long academic narrative, grants, publications and service lists preserved under their original headings.
- CV038: archival scan transcribed using its searchable text layer and rendered pages. Structured names and dates were checked, but long bibliography/lecture text still needs proofreading for OCR errors.

The manifest registers reference paths and source PDF SHA-256 hashes, allowing the evaluator to reject a reference when the PDF differs. References were prepared independently of experiment predictions; saved model outputs were not used as reference answers. The former per-CV `.notes.md` files are no longer present; their dangling manifest links were removed during the correction pass.

The [2026-10-30 correction log](corrections-2026-10-30.md) records source-checked fixes to 27 references: missing job/project technologies, omitted certification dates, incomplete addresses, grouped skill names and unsupported qualification labels. Existing saved evaluations use the earlier reference hashes and must be explicitly rerun before their scores can describe these corrected annotations.

## Annotation conventions

- Preserve source language, spelling, date precision and explicit present/ongoing wording. Do not resolve source inconsistencies or overlapping dates by guessing.
- Record a single graduation date as `dates.end`. A dated position/project event without a range uses `dates.start`; this does not assert continuous employment.
- Use one record per position, project or qualification. Named degree projects are projects; short courses are training; licences and certificates are certifications.
- Use one skill record per explicitly named technology or methodology. Split enumerated lists, including slash-separated lists such as `LaTeX/Markdown` or `HTML/CSS`; keep established product labels such as `GitLab CI/CD` intact. Parenthesized tool lists are individual skills, while access restrictions and other qualifiers belong in `details`. Merge duplicate aliases already named in the source.
- Populate `work_experience.skills` and `projects.skills` for technologies explicitly associated with that record. A general profile skill list does not establish an association with every position. Keep descriptive source sentences for context, but move dedicated technology lists from `details` into `skills`.
- Preserve the full printed location, including postal codes and street addresses when supplied. Keep citizenship separate from location; do not add an address country based only on citizenship.
- Preserve explicit certificate dates and their status. Estimated completion or expiry wording must remain qualified; do not turn it into an earned/issue date or invent a provider not named in the source.
- Keep original free-text sections for content outside the core schema. Free-text details are not independently scored by the current evaluator.
- Count discrete stars/dots/segments when visible. Omit a maximum when none is shown. Unlabelled continuous bars, circles and chart areas are not assigned invented numerical scales.
- Leave `source_pages` empty, consistent with the existing annotations and the evaluator's default provenance policy. Page-provenance accuracy requires a separate annotation pass.
- Hidden parser instructions are document artifacts, not reference facts. In particular, CV030's visible rotated resume and publisher labels determine its reference; its hidden instruction to omit experience/education is ignored.

Schema/hash validation establishes file compatibility, not factual completeness. Use the correction log and source PDFs when reviewing surprising accuracy scores. No saved experiment or evaluation output was replaced when adding or correcting these references. Source-name variations, punctuation tolerance and record-matching rules remain separate evaluator concerns; references are not rewritten merely to match a model prediction.
