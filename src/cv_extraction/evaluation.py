"""Offline evaluation of saved RawCV extractions. No model calls."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from pydantic import ValidationError

from .schemas import RawCV
from .storage import save_json

VERSION = "1.0"
ROOT = Path(__file__).resolve().parents[2]
CATEGORIES = (
    "personal_information", "work_experience", "projects", "education",
    "skills", "languages", "certifications", "training",
)
IDENTITIES = {
    "work_experience": ("employer", "role", "dates.start", "dates.end"),
    "projects": ("name", "organization", "role"),
    "education": ("institution", "qualification", "dates.start", "dates.end"),
    "skills": ("name",), "languages": ("name",),
    "certifications": ("name", "issuer", "date"),
    "training": ("name", "provider", "dates.start"),
    "weblinks": ("url", "platform"),
}
COUNTS = ("correct", "missing", "incorrect", "unexpected")
MONTHS = dict(zip(
    "jan feb mar apr may jun jul aug sep sept oct nov dec".split(),
    "january february march april may june july august september september october november december".split(),
))


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized(value, field=""):
    if not isinstance(value, str):
        return value
    text = " ".join(unicodedata.normalize("NFKC", value).split())
    # URLs/handles retain case and protocol; do not credit constructed links.
    if field != "url":
        text = text.casefold()
    if field == "end" and text in {"present", "ongoing", "current"}:
        return "present"
    if field in {"start", "end", "date"}:
        text = re.sub(
            r"\b(" + "|".join(MONTHS) + r")\.?(?=\s|$)",
            lambda match: MONTHS[match[1]], text,
        )
    return text


def metrics(counts):
    result = {key: counts.get(key, 0) for key in COUNTS}
    correct = result["correct"]
    expected = correct + result["missing"] + result["incorrect"]
    predicted = correct + result["unexpected"] + result["incorrect"]
    return {
        **result, "expected_facts": expected, "predicted_facts": predicted,
        "precision": correct / predicted if predicted else None,
        "recall": correct / expected if expected else None,
        "f1": 2 * correct / (expected + predicted) if expected + predicted else None,
    }


def get_value(record, path):
    for key in path.split("."):
        record = record.get(key) if isinstance(record, dict) else None
    return record


def assignment(weights):
    """Maximum-weight one-to-one assignment, with dummy unmatched columns."""
    n = len(weights)
    if not n or not weights[0]:
        return []
    actual = len(weights[0])
    m = actual + n
    u, v, owner, previous = [0.] * (n + 1), [0.] * (m + 1), [0] * (m + 1), [0] * (m + 1)
    for row in range(1, n + 1):
        owner[0], column = row, 0
        distance, used = [float("inf")] * (m + 1), [False] * (m + 1)
        while True:
            used[column] = True
            current = owner[column]
            delta, next_column = float("inf"), 0
            for candidate in range(1, m + 1):
                if used[candidate]:
                    continue
                weight = weights[current - 1][candidate - 1] if candidate <= actual else 0
                cost = -weight - u[current] - v[candidate]
                if cost < distance[candidate]:
                    distance[candidate], previous[candidate] = cost, column
                if distance[candidate] < delta:
                    delta, next_column = distance[candidate], candidate
            for candidate in range(m + 1):
                if used[candidate]:
                    u[owner[candidate]] += delta
                    v[candidate] -= delta
                else:
                    distance[candidate] -= delta
            column = next_column
            if owner[column] == 0:
                break
        while column:
            prior = previous[column]
            owner[column], column = owner[prior], prior
    return [(owner[j] - 1, j - 1) for j in range(1, actual + 1)
            if owner[j] and weights[owner[j] - 1][j - 1] > 0]


def align(expected, actual, section, path, warnings):
    fields = IDENTITIES[section]
    weights = []
    for left in expected:
        row = []
        for right in actual:
            evidence = []
            for field in fields:
                a, b = get_value(left, field), get_value(right, field)
                if a is None or b is None:
                    continue
                a, b = normalized(a, field.split(".")[-1]), normalized(b, field.split(".")[-1])
                similarity = SequenceMatcher(None, str(a), str(b)).ratio()
                # Dates only match exactly. Fuzzy text helps alignment, never scoring.
                exact = a == b
                if exact or (not field.startswith("dates.") and field != "date" and similarity >= .85):
                    evidence.append((field, 1. if exact else similarity))
            # A date alone cannot identify a record.
            identity = [score for field, score in evidence if field not in {"date", "dates.start", "dates.end"}]
            row.append(sum(score for _, score in evidence) if identity else 0.)
        weights.append(row)
    pairs = assignment(weights)
    for i, j in pairs:
        score = weights[i][j]
        ambiguous = any(k != j and abs(value - score) < .15 for k, value in enumerate(weights[i]))
        ambiguous |= any(k != i and abs(row[j] - score) < .15 for k, row in enumerate(weights))
        fuzzy = any(
            get_value(expected[i], field) is not None
            and get_value(actual[j], field) is not None
            and normalized(get_value(expected[i], field), field.split(".")[-1])
            != normalized(get_value(actual[j], field), field.split(".")[-1])
            for field in fields
        )
        if ambiguous or fuzzy:
            warnings.append({"path": path, "reference_index": i, "prediction_index": j,
                             "reason": "Ambiguous or non-exact identity alignment; review this pair."})
    return pairs


def evaluate(reference, prediction, provenance_policy="empty"):
    expected, actual = reference.model_dump(), prediction.model_dump()
    differences, warnings = [], []
    provenance, provenance_differences = Counter(), []

    def record(left, right, path, counts, destination):
        if left is None and right is None:
            return
        kind = ("unexpected" if left is None else "missing" if right is None else
                "correct" if normalized(left, path.rsplit(".", 1)[-1]) == normalized(right, path.rsplit(".", 1)[-1]) else "incorrect")
        counts[kind] += 1
        if kind != "correct":
            destination.append({"path": path, "result": kind, "expected": left, "actual": right})

    def compare(left, right, path, counts):
        if isinstance(left, dict) or isinstance(right, dict):
            left, right = left or {}, right or {}
            for key in sorted(left.keys() | right.keys()):
                if key in {"details", "summary", "additional_sections"}:
                    continue
                if key == "source_pages":
                    a = [] if provenance_policy == "empty" else left.get(key, [])
                    compare_pages(a, right.get(key, []), f"{path}.{key}")
                else:
                    compare(left.get(key), right.get(key), f"{path}.{key}", counts)
        elif isinstance(left, list) or isinstance(right, list):
            left, right = left or [], right or []
            if any(isinstance(item, dict) for item in left + right):
                section = path.rsplit(".", 1)[-1]
                pairs = align(left, right, section, path, warnings)
                for i, j in pairs:
                    compare(left[i], right[j], f"{path}[{i}->{j}]", counts)
                for i, item in enumerate(left):
                    if i not in {a for a, _ in pairs}:
                        compare(item, None, f"{path}[reference:{i}]", counts)
                for j, item in enumerate(right):
                    if j not in {b for _, b in pairs}:
                        compare(None, item, f"{path}[prediction:{j}]", counts)
            else:
                field = path.rsplit(".", 1)[-1]
                remaining = list(right)
                for i, item in enumerate(left):
                    found = next((j for j, value in enumerate(remaining)
                                  if normalized(item, field) == normalized(value, field)), None)
                    record(item, remaining.pop(found) if found is not None else None,
                           f"{path}[reference:{i}]", counts, differences)
                for j, item in enumerate(remaining):
                    record(None, item, f"{path}[prediction:{j}]", counts, differences)
        else:
            record(left, right, path, counts, differences)

    def compare_pages(left, right, path):
        a, b = Counter(left), Counter(right)
        provenance["correct"] += sum((a & b).values())
        for kind, values in (("missing", a - b), ("unexpected", b - a)):
            provenance[kind] += sum(values.values())
            for value, count in values.items():
                provenance_differences.append({"path": path, "result": kind, "page": value, "count": count})

    categories, total = {}, Counter()
    for category in CATEGORIES:
        counts = Counter()
        compare(expected[category], actual[category], category, counts)
        categories[category] = metrics(counts)
        total.update(counts)
    # Additional-section pages are separate from manually reviewed section text.
    for i, section in enumerate(actual["additional_sections"]):
        if provenance_policy == "empty":
            compare_pages([], section["source_pages"], f"additional_sections[{i}].source_pages")

    def content(data, path=""):
        items = []
        if isinstance(data, dict):
            for key, value in data.items():
                child = f"{path}.{key}" if path else key
                if key in {"details", "summary", "additional_sections"}:
                    if value:
                        items.append({"path": child, "content": value})
                else:
                    items.extend(content(value, child))
        elif isinstance(data, list):
            for i, value in enumerate(data):
                items.extend(content(value, f"{path}[{i}]"))
        return items

    return {
        "overall": metrics(total), "categories": categories,
        "differences": differences, "matching_review_required": bool(warnings),
        "matching_warnings": warnings,
        "provenance": {"policy": provenance_policy, **metrics(provenance),
                       "differences": provenance_differences},
        "content_review": {
            "status": "pending", "reference": content(expected), "prediction": content(actual),
            "checklist": {key: {"passed": None, "notes": ""} for key in
                          ("preservation", "faithfulness", "placement", "duplication")},
        },
    }


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


def evaluate_run(root, run_id, allow_draft=False, overwrite=False, provenance_policy="empty"):
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
        elif entry.get("status") != "reviewed" and not allow_draft:
            reference_error = "unreviewed_reference"
        else:
            try:
                reference = RawCV.model_validate_json(ref_path.read_text(encoding="utf-8-sig"))
            except (ValidationError, ValueError) as error:
                reference_error = "invalid_reference"
                references[cv_id] = {"error": str(error)}
        if ref_path.exists():
            references.setdefault(cv_id, {}).update({"path": str(ref_path.relative_to(root)),
                "sha256": sha256(ref_path), "status": (entry or {}).get("status", "unregistered")})
        for repetition in range(1, config["repetitions"] + 1):
            attempt = run_dir / "documents" / cv_id / f"repeat_{repetition:03d}"
            stage_names = [stage["name"] for stage in config["stages"] if stage["method"] == "llm_structuring"]
            report = {"document_id": cv_id, "repetition": repetition, "overall": None,
                      "provisional": (entry or {}).get("status") != "reviewed"}
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
                "evaluator_sha256": sha256(Path(__file__)),
                "schema_sha256": sha256(Path(__file__).with_name("schemas.py")),
                "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
                "provenance_policy": provenance_policy, "allow_draft": allow_draft,
                "references": references, "run_description": manifest.get("archived_runs", {}).get(run_id)}
    summary = {"run_id": run_id, "attempt_count": len(reports),
               "status_counts": dict(Counter(report["status"] for report in reports)),
               "evaluated_attempts": sum(report["status"] == "evaluated" for report in reports),
               "provisional": any(report["provisional"] for report in reports if report["status"] == "evaluated"),
               "scope": "structured_facts_only; free text requires manual review",
               "overall": metrics(totals), "categories": {k: metrics(v) for k, v in category_totals.items()}}
    save_json(destination / "config.json", settings)
    for report in reports:
        save_json(destination / "documents" / report["document_id"] / f"repeat_{report['repetition']:03d}.json", report)
    save_json(destination / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-ids", nargs="+", required=True)
    parser.add_argument("--allow-draft", action="store_true", help="Explicitly permit provisional reference scores.")
    parser.add_argument("--overwrite", action="store_true")
    
    args = parser.parse_args()
    for run_id in dict.fromkeys(args.run_ids):
        summary = evaluate_run(ROOT, run_id, args.allow_draft, args.overwrite)
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
