"""Text equivalences used for alignment and factual comparison."""

import re
import unicodedata

MONTHS = dict(zip(
    "jan feb mar apr may jun jul aug sep sept oct nov dec".split(),
    "january february march april may june july august september september october november december".split(),
))


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
