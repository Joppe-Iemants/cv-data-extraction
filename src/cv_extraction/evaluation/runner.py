"""Load saved runs and references, evaluate attempts and save reports."""

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from pydantic import ValidationError

from ..schemas import RawCV
from ..storage import save_json
from .scoring import CATEGORIES, COUNTS, evaluate, metrics
from ..extraction.stages import STAGE_METHODS

VERSION = "1.2"
ROOT = Path(__file__).resolve().parents[3]

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_run(root, manifest, run_id):
    if Path(run_id).name != run_id or run_id in {".", ".."}:
        raise ValueError("Run IDs must be folder names.")
    active = root / "results" / run_id
    selected = manifest.get("archived_runs", {}).get(run_id, {})
    saved = root / "data" / selected.get("path", f"archived_runs/{run_id}")
    if not saved.resolve().is_relative_to((root / "data").resolve()):
        raise ValueError("Archived-run paths must stay within data.")
    candidates = [path for path in (active, saved) if (path / "config.json").is_file()]
    if not candidates:
        raise FileNotFoundError(f"Run not found: {run_id}")
    # An explicitly registered preserved copy is authoritative; active results
    # may be removed later without changing the source used for evaluation.
    return saved if selected and saved in candidates else candidates[0]


def evaluate_run(root, run_id, overwrite=False, provenance_policy="empty"):
    manifest = read_json(root / "data/manifest.json")
    run_dir = resolve_run(root, manifest, run_id)
    config_path = run_dir / "config.json"
    config = read_json(config_path)
    destination = root / "evaluation/results" / run_id
    if destination.exists() and not overwrite:
        raise FileExistsError(f"{destination} already exists. Use --overwrite to replace it.")
    reports, references = [], {}
    catalog = manifest.get("references", {})
    for document in config["inputs"]:
        cv_id = document["id"]
        entry = catalog.get(cv_id)
        ref_path = root / "data" / (entry or {}).get("path", f"references/{cv_id}.json")
        reference, reference_error = None, None
        if not entry or not ref_path.exists():
            reference_error = "missing_reference"
        elif entry.get("pdf_sha256") != document["sha256"]:
            reference_error = "reference_source_mismatch"
        else:
            try:
                reference = RawCV.model_validate_json(ref_path.read_text(encoding="utf-8-sig"))
            except (ValidationError, ValueError) as error:
                reference_error = "invalid_reference"
                references[cv_id] = {"error": str(error)}
        if ref_path.exists():
            references.setdefault(cv_id, {}).update({"path": str(ref_path.relative_to(root)),
                "sha256": sha256(ref_path)})
        for repetition in range(1, config["repetitions"] + 1):
            attempt = run_dir / "documents" / cv_id / f"repeat_{repetition:03d}"
            stage_names = [
                stage["name"]
                for stage in config["stages"]
                if STAGE_METHODS.get(stage["method"], {}).get("output_kind") == "cv"
            ]
            report = {"document_id": cv_id, "repetition": repetition, "overall": None}
            attempt_report = read_json(attempt / "report.json") if (attempt / "report.json").exists() else {}
            prediction_path = attempt / stage_names[-1] / "extraction.json" if stage_names else None
            report["extraction_status"] = attempt_report.get("status", "incomplete")
            if report["extraction_status"] not in {"completed", "success"}:
                report["status"] = "extraction_failed" if attempt_report else "incomplete_attempt"
            elif prediction_path is None:
                report["status"] = "no_structuring_stage"
            elif not prediction_path.exists():
                report["status"] = "missing_output"
            else:
                report["prediction_sha256"] = sha256(prediction_path)
                try:
                    raw = read_json(prediction_path)
                    report["json_valid"] = True
                    prediction = RawCV.model_validate(raw)
                    report["schema_valid"] = True
                    if reference_error:
                        report["status"] = reference_error
                    else:
                        report.update(evaluate(reference, prediction, provenance_policy))
                        report["status"] = "evaluated"
                except json.JSONDecodeError as error:
                    report.update(status="invalid_json", json_valid=False, error=str(error))
                except ValidationError as error:
                    report.update(status="invalid_schema", schema_valid=False, error=str(error))
            reports.append(report)
    totals = Counter()
    category_totals = {category: Counter() for category in CATEGORIES}
    for report in reports:
        if report["status"] == "evaluated":
            totals.update({key: report["overall"][key] for key in COUNTS})
            for category in CATEGORIES:
                category_totals[category].update({key: report["categories"][category][key] for key in COUNTS})
    settings = {"source_run_id": run_id, "source_path": str(run_dir.relative_to(root)),
                "source_config_sha256": sha256(config_path), "evaluator_version": VERSION,
                "evaluator_files_sha256": {
                    name: sha256(Path(__file__).with_name(name))
                    for name in ("runner.py", "scoring.py", "matching.py", "normalization.py")
                },
                "schema_sha256": sha256(Path(__file__).parents[1] / "schemas.py"),
                "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
                "provenance_policy": provenance_policy,
                "references": references, "run_description": manifest.get("archived_runs", {}).get(run_id)}
    summary = {"run_id": run_id, "attempt_count": len(reports),
               "status_counts": dict(Counter(report["status"] for report in reports)),
               "evaluated_attempts": sum(report["status"] == "evaluated" for report in reports),
               "scope": "structured_facts_only; free text requires manual review",
               "overall": metrics(totals), "categories": {k: metrics(v) for k, v in category_totals.items()}}
    save_json(destination / "config.json", settings)
    for report in reports:
        save_json(destination / "documents" / report["document_id"] / f"repeat_{report['repetition']:03d}.json", report)
    save_json(destination / "summary.json", summary)
    return summary
