"""Category scores, field differences, provenance and content-review checklists."""

from collections import Counter

from .matching import align
from .normalization import normalized

CATEGORIES = (
    "personal_information", "work_experience", "projects", "education",
    "skills", "languages", "certifications", "training",
)


COUNTS = ("correct", "missing", "incorrect", "unexpected")


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
