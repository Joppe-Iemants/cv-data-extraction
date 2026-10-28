import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

from pydantic import BaseModel, ValidationError

from .schemas import RawCV
from .storage import save_json


IGNORED = {
    "entry_id",
    "source_pages",
    "source_heading",
    "source_text",
    "related_experience_ids",
    "related_position_ids",
    "scale_description"
}

MANUAL = {
    "profiles",
    "additional_sections",
    "declarations",
    "description",
    "responsibilities",
    "achievements",
    "objectives",
    "contributions",
    "statement",
    "locations",
    "desired_locations",
    "label"
}

IDENTITIES = {
    "work_experience": ("organization.name",),
    "volunteering": ("organization.name",),
    "military_service": ("organization.name",),
    "positions": ("title", "dates.start", "dates.end"),
    "projects": ("name", "organization.name"),
    "education": ("institution.name", "degree", "fields_of_study"),
    "skills": ("name",),
    "languages": ("name",),
    "certifications": ("name", "issuer.name", "credential_id"),
    "training": ("name", "provider.name"),
    "awards": ("name", "issuer.name"),
    "publications": ("title",),
    "presentations": ("title", "event"),
    "memberships": ("organization.name", "role"),
    "interests": ("name",),
    "references": ("name",),
    "contacts": ("type", "value"),
    "weblinks": ("platform", "url"),
    "theses": ("title",),
    "identifiers": ("type", "value"),
    "driving_licenses": ("category", "country"),
    "work_authorizations": ("country", "status"),
    "security_clearances": ("level", "authority")
}

MONTHS = {
    "jan": "january",
    "feb": "february",
    "mar": "march",
    "apr": "april",
    "jun": "june",
    "jul": "july",
    "aug": "august",
    "sep": "september",
    "sept": "september",
    "oct": "october",
    "nov": "november",
    "dec": "december"
}

DATE_FIELDS = {
    "start",
    "end",
    "date",
    "date_of_birth",
    "date_achieved",
    "expiration_date",
    "date_issued",
    "start_date",
    "valid_until"
}


def empty(value):
    return (
        value is None
        or (
            isinstance(value, (str, list, dict))
            and len(value) == 0
        )
        or (
            isinstance(value, str)
            and not value.strip()
        )
    )


def normalize(value, field=""):
    if isinstance(value, str):
        text = " ".join(
            unicodedata.normalize("NFC", value).split()
        )

        if field not in {
            "url", "value", "credential_id", "membership_id"
        }:
            text = text.casefold()

        if field == "end" and text in {
            "present", "ongoing", "current"
        }:
            text = "present"

        if field in DATE_FIELDS:
            text = re.sub(
                r"\b(" + "|".join(MONTHS) + r")\.?(?=\s|$)",
                lambda match: MONTHS[match.group(1)],
                text
            )

        return ("text", text)

    if isinstance(value, bool):
        return ("boolean", value)

    if isinstance(value, (float, int)):
        return ("number", value)

    if isinstance(value, list):
        return tuple(
            sorted(
                (normalize(item, field) for item in value),
                key=repr
            )
        )

    return ("other", repr(value))


def project(value, manual, path=""):
    if isinstance(value, BaseModel):
        result = {}

        for key in type(value).model_fields:
            item = getattr(value, key)
            item_path = f"{path}.{key}" if path else key

            if key in IGNORED:
                continue

            if key in MANUAL:
                if not empty(item):
                    manual.append({
                        "path": item_path,
                        "value": json.loads(
                            json.dumps(
                                item,
                                default=lambda obj: obj.model_dump(
                                    mode="json",
                                    exclude_defaults=True
                                )
                            )
                        )
                    })

                continue

            if type(value).__name__ == "DateRange":
                if key == "raw_text" and any(
                    getattr(value, name) is not None
                    for name in (
                        "start", "end", "is_current", "duration"
                    )
                ):
                    continue

            if type(value).__name__ == "Proficiency":
                if key == "type":
                    continue

                if key == "raw_value" and (
                    value.value is not None
                    or value.cefr_level is not None
                ):
                    continue

            cleaned = project(item, manual, item_path)

            if not empty(cleaned):
                result[key] = cleaned

        return result

    if isinstance(value, list):
        result = []

        for index, item in enumerate(value):
            cleaned = project(
                item,
                manual,
                f"{path}[{index}]"
            )

            if not empty(cleaned):
                result.append(cleaned)

        return result

    return value


def get_value(record, path):
    value = record

    for key in path.split("."):
        if not isinstance(value, dict):
            return None

        value = value.get(key)

    return value


def match_records(expected, actual, fields):
    scores = []

    for left in expected:
        row = []

        for right in actual:
            score = sum(
                not empty(get_value(left, field))
                and not empty(get_value(right, field))
                and normalize(
                    get_value(left, field),
                    field.split(".")[-1]
                )
                == normalize(
                    get_value(right, field),
                    field.split(".")[-1]
                )
                for field in fields
            )

            row.append(score)

        scores.append(row)

    if not expected or not actual:
        return [], scores

    # Find a maximum-score one-to-one assignment.
    # Dummy columns allow unmatched reference records.
    n = len(expected)
    m = max(len(expected), len(actual))

    u = [0] * (n + 1)
    v = [0] * (m + 1)
    owner = [0] * (m + 1)
    previous = [0] * (m + 1)

    for row in range(1, n + 1):
        owner[0] = row
        column = 0
        distances = [float("inf")] * (m + 1)
        used = [False] * (m + 1)

        while True:
            used[column] = True
            current_row = owner[column]
            delta = float("inf")
            next_column = 0

            for candidate in range(1, m + 1):
                if used[candidate]:
                    continue

                weight = (
                    scores[current_row - 1][candidate - 1]
                    if candidate <= len(actual)
                    else 0
                )

                cost = (
                    -weight
                    - u[current_row]
                    - v[candidate]
                )

                if cost < distances[candidate]:
                    distances[candidate] = cost
                    previous[candidate] = column

                if distances[candidate] < delta:
                    delta = distances[candidate]
                    next_column = candidate

            for candidate in range(m + 1):
                if used[candidate]:
                    u[owner[candidate]] += delta
                    v[candidate] -= delta
                else:
                    distances[candidate] -= delta

            column = next_column

            if owner[column] == 0:
                break

        while column:
            prior = previous[column]
            owner[column] = owner[prior]
            column = prior

    pairs = [
        (owner[column] - 1, column - 1)
        for column in range(1, len(actual) + 1)
        if owner[column]
        and scores[owner[column] - 1][column - 1] > 0
    ]

    return pairs, scores


def summarize(counts):
    correct = counts["correct"]

    predicted = (
        correct
        + counts["unexpected"]
        + counts["incorrect"]
    )

    expected = (
        correct
        + counts["missing"]
        + counts["incorrect"]
    )

    return {
        **{
            key: counts[key]
            for key in (
                "correct", "missing", "unexpected", "incorrect"
            )
        },
        "expected_fields": expected,
        "predicted_fields": predicted,
        "precision": correct / predicted if predicted else None,
        "recall": correct / expected if expected else None,
        "f1": (
            2 * correct / (predicted + expected)
            if predicted + expected
            else None
        )
    }


def evaluate(reference: RawCV, prediction: RawCV) -> dict:
    manual_reference = []
    manual_prediction = []

    expected = project(reference, manual_reference)
    actual = project(prediction, manual_prediction)

    details = []
    warnings = []
    sections = {}
    totals = Counter()

    def compare(left, right, path, counts):
        if isinstance(left, dict) or isinstance(right, dict):
            left = left or {}
            right = right or {}

            for key in sorted(left.keys() | right.keys()):
                compare(
                    left.get(key),
                    right.get(key),
                    f"{path}.{key}",
                    counts
                )

            return

        if isinstance(left, list) or isinstance(right, list):
            left = left or []
            right = right or []

            if any(
                isinstance(item, dict)
                for item in left + right
            ):
                fields = IDENTITIES.get(
                    path.rsplit(".", 1)[-1]
                )

                if fields is None:
                    raise ValueError(
                        f"No record matching policy for {path}"
                    )

                pairs, scores = match_records(
                    left,
                    right,
                    fields
                )

                for i, j in pairs:
                    weight = scores[i][j]

                    if (
                        scores[i].count(weight) > 1
                        or sum(
                            row[j] == weight
                            for row in scores
                        ) > 1
                    ):
                        warnings.append({
                            "path": path,
                            "reason": (
                                "Ambiguous identity match; "
                                "review alignment"
                            ),
                            "reference_index": i,
                            "prediction_index": j
                        })

                    compare(
                        left[i],
                        right[j],
                        f"{path}[{i}->{j}]",
                        counts
                    )

            else:
                pairs = []
                available = set(range(len(right)))
                field = path.rsplit(".", 1)[-1]

                for i, value in enumerate(left):
                    for j in sorted(available):
                        if normalize(value, field) == normalize(
                            right[j],
                            field
                        ):
                            pairs.append((i, j))
                            available.remove(j)
                            break

                for i, j in pairs:
                    compare(
                        left[i],
                        right[j],
                        f"{path}[{i}->{j}]",
                        counts
                    )

            matched_left = {i for i, j in pairs}
            matched_right = {j for i, j in pairs}

            for i, item in enumerate(left):
                if i not in matched_left:
                    compare(
                        item,
                        None,
                        f"{path}[reference:{i}]",
                        counts
                    )

            for j, item in enumerate(right):
                if j not in matched_right:
                    compare(
                        None,
                        item,
                        f"{path}[prediction:{j}]",
                        counts
                    )

            return

        if empty(left) and empty(right):
            return

        if empty(left):
            kind = "unexpected"
        elif empty(right):
            kind = "missing"
        elif normalize(
            left,
            path.rsplit(".", 1)[-1]
        ) == normalize(
            right,
            path.rsplit(".", 1)[-1]
        ):
            kind = "correct"
        else:
            kind = "incorrect"

        counts[kind] += 1

        if kind != "correct":
            details.append({
                "path": path,
                "result": kind,
                "expected": left,
                "actual": right
            })

    for section in sorted(expected.keys() | actual.keys()):
        counts = Counter()

        compare(
            expected.get(section),
            actual.get(section),
            section,
            counts
        )

        sections[section] = summarize(counts)
        totals.update(counts)

    return {
        "status": "completed",
        "scope": "structured_fields_only",
        "matching_review_required": bool(warnings),
        "overall": summarize(totals),
        "sections": sections,
        "differences": details,
        "matching_warnings": warnings,
        "manual_review": {
            "reference": manual_reference,
            "prediction": manual_prediction
        }
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--reference",
        type=Path,
        required=True
    )
    parser.add_argument(
        "--prediction",
        type=Path,
        required=True
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True
    )

    args = parser.parse_args()

    if args.output.resolve() in {
        args.reference.resolve(),
        args.prediction.resolve()
    }:
        parser.error("Output must not overwrite either input.")

    reference_text = args.reference.read_text(
        encoding="utf-8-sig"
    )
    reference = RawCV.model_validate_json(reference_text)

    report = {
        "reference": str(args.reference.resolve()),
        "prediction": str(args.prediction.resolve()),
        "reference_sha256": hashlib.sha256(
            args.reference.read_bytes()
        ).hexdigest()
    }

    stage_report_path = (
        args.prediction.parent / "report.json"
    )

    stage_report = (
        json.loads(
            stage_report_path.read_text(
                encoding="utf-8-sig"
            )
        )
        if stage_report_path.exists()
        else {}
    )

    report["extraction_status"] = stage_report.get(
        "execution_status",
        "unknown"
    )

    try:
        if report["extraction_status"] not in {
            "completed", "unknown"
        }:
            report.update(
                status="extraction_failed",
                overall=None
            )

        elif not args.prediction.exists():
            report.update(
                status="missing_output",
                overall=None
            )

        else:
            text = args.prediction.read_text(
                encoding="utf-8-sig"
            )

            report["prediction_sha256"] = hashlib.sha256(
                args.prediction.read_bytes()
            ).hexdigest()

            json.loads(text)
            report["json_valid"] = True

            prediction = RawCV.model_validate_json(text)
            report["schema_valid"] = True

            report.update(
                evaluate(reference, prediction)
            )

    except json.JSONDecodeError as error:
        report.update(
            status="invalid_json",
            json_valid=False,
            overall=None,
            error=str(error)
        )

    except ValidationError as error:
        report.update(
            status="invalid_schema",
            schema_valid=False,
            overall=None,
            error=str(error)
        )

    save_json(args.output, report)

    print(
        json.dumps(
            {
                "status": report["status"],
                "overall": report["overall"],
                "output": str(args.output)
            },
            indent=2
        )
    )


if __name__ == "__main__":
    main()