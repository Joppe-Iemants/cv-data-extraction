"""Text equivalences used for alignment and factual comparison."""

import re
import unicodedata
from urllib.parse import urlsplit


def link_identity(record):
    """Compare known profile URLs with source handles without guessing domains."""
    value = normalized(record.get("url"), "url")
    platform = normalized(record.get("platform"), "platform")
    if not isinstance(value, str):
        return value
    hosts = {"twitter.com": "twitter", "x.com": "twitter",
             "github.com": "github", "gitlab.com": "gitlab",
             "linkedin.com": "linkedin", "orcid.org": "orcid"}
    parsed = urlsplit(value if "://" in value else "//" + value)
    host = (parsed.hostname or "").removeprefix("www.")
    if platform == "mastodon":
        if "://" in value and parsed.path.startswith("/@") and not parsed.query and not parsed.fragment:
            handle = parsed.path[2:].rstrip("/")
            if handle and "/" not in handle:
                return (platform, handle, host)
        if value.startswith("@") and value.count("@") == 2:
            handle, domain = value[1:].split("@")
            if handle and domain:
                return (platform, handle, domain.lower())
    if host in hosts and not parsed.query and not parsed.fragment:
        platform = hosts[host]
        handle = parsed.path.strip("/")
        if platform == "linkedin" and handle.startswith("in/"):
            handle = handle[3:]
        if handle and "/" not in handle:
            return (platform, handle.removeprefix("@"))
    # A bare identifier is meaningful only with an explicit known platform.
    if platform in set(hosts.values()) and not any(c in value for c in "/:?#"):
        return (platform, value.removeprefix("@"))
    return value

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
    if field == "platform" and text in {"x", "twitter"}:
        return "twitter"
    if field == "end" and text in {"present", "ongoing", "current"}:
        return "present"
    if field in {"start", "end", "date"}:
        text = re.sub(
            r"\b(" + "|".join(MONTHS) + r")\.?(?=\s|$)",
            lambda match: MONTHS[match[1]], text,
        )
    return text
