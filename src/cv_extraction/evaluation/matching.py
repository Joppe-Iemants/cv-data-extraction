"""One-to-one record alignment; similarity does not award factual credit."""

from difflib import SequenceMatcher

from .normalization import link_identity, normalized

IDENTITIES = {
    "work_experience": ("employer", "role", "dates.start", "dates.end"),
    "projects": ("name", "organization", "role"),
    "education": ("institution", "qualification", "dates.start", "dates.end"),
    "skills": ("name",), "languages": ("name",),
    "certifications": ("name", "issuer", "date"),
    "training": ("name", "provider", "dates.start"),
    "weblinks": ("url", "platform"),
}


def get_value(record, path):
    if path == "url" and isinstance(record, dict):
        return link_identity(record)
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
