"""
Text utility helpers used across the automation project.

The implementation preserves the legacy behaviours that our unit tests assert,
while keeping the newer helper functions introduced during the Supabase
migration.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from typing import Iterable, List

# --------------------------------------------------------------------------- #
# Identifier helpers
# --------------------------------------------------------------------------- #


def generate_document_id(title: str, namespace: uuid.UUID = uuid.NAMESPACE_DNS) -> str:
    """Generate a deterministic UUID5 for a given title."""
    return str(uuid.uuid5(namespace, title))


def generate_cache_key(text: str, encoding: str = "utf-8") -> str:
    """Return a SHA256 hash that can be used as a cache key."""
    return hashlib.sha256(text.encode(encoding)).hexdigest()


# --------------------------------------------------------------------------- #
# Title processing helpers
# --------------------------------------------------------------------------- #

_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*]')
_UNSAFE_PUNCTUATION = re.compile(r"[!@#$%^&+=`~]")
_NON_ALLOWED_CHARS = re.compile(r"[^가-힣A-Za-z0-9\s\-\._\(\)\[\]]")
_MULTIPLE_SPACES = re.compile(r"\s+")
_APPROVAL_PREFIXES = [
    r"^\s*\[(?P<tag>[^\]]+)\]\s*(?P<body>.+)$",
    r"^\s*(?P<prefix>접수요청|접수|승인요청|승인 요청|결재요청|결재 요청)\s*[:\-]\s*(?P<body>.+)$",
    r"^\s*(?P<prefix>제목)\s*[:\-]\s*(?P<body>.+)$",
]
_RECEPTION_PREFIX = re.compile(r"^\s*접수[가-힣\s]*[:\-]\s*", re.IGNORECASE)


def clean_document_title(title: str) -> str:
    """Normalise document titles by removing prefixes and unsafe characters."""
    if not title:
        return ""

    cleaned = title.strip()
    cleaned = _RECEPTION_PREFIX.sub("", cleaned)
    cleaned = re.sub(r"^\s*승인요청\s*[:\-]\s*", "", cleaned)

    cleaned = _INVALID_FILENAME_CHARS.sub("", cleaned)
    cleaned = _UNSAFE_PUNCTUATION.sub("", cleaned)
    cleaned = _NON_ALLOWED_CHARS.sub(" ", cleaned)
    cleaned = _MULTIPLE_SPACES.sub(" ", cleaned).strip()
    return cleaned


def extract_title_from_approval(title: str) -> str:
    """Extract the human friendly portion from an approval/reception text."""
    if title is None:
        return ""
    if title.strip() == "":
        return title

    for pattern in _APPROVAL_PREFIXES:
        match = re.match(pattern, title)
        if match:
            body = match.group("body")
            return body

    return title.strip()


def is_reception_document(title: str) -> bool:
    """Return True when the supplied title looks like a reception document."""
    if not title or not isinstance(title, str):
        return False
    return bool(_RECEPTION_PREFIX.match(title))


def is_approval_document(title: str) -> bool:
    """Return True if the text looks like an approval request."""
    if not title or not isinstance(title, str):
        return False
    return bool(re.match(r"^\s*승인요청\s*[:\-]", title))


# --------------------------------------------------------------------------- #
# Formatting helpers
# --------------------------------------------------------------------------- #


def normalize_text(text: str) -> str:
    """Trim whitespace and collapse runs of spaces inside the text."""
    if not text:
        return ""
    return _MULTIPLE_SPACES.sub(" ", text.strip())


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to the requested length with a suffix."""
    if not text or len(text) <= max_length:
        return text
    if max_length <= len(suffix):
        return suffix[:max_length]
    return text[: max_length - len(suffix)] + suffix


def extract_keywords(text: str, min_length: int = 2) -> List[str]:
    """Extract simple keywords from a block of text."""
    if not text:
        return []

    words = re.findall(r"[가-힣A-Za-z0-9]+", text)
    return [word for word in words if len(word) >= min_length]


def remove_numbers_from_title(title: str) -> str:
    """Strip digits from a title while keeping spacing tidy."""
    if not title:
        return ""
    without_numbers = re.sub(r"\d+", " ", title)
    return _MULTIPLE_SPACES.sub(" ", without_numbers).strip()


def format_option_display(options: Iterable[str], separator: str = " / ") -> str:
    """Format selectable options for display to the user."""
    return separator.join(f"[{idx}] {option}" for idx, option in enumerate(options))


def format_numbered_list(
    items: List[str], start_num: int = 1, zero_padded: bool = True
) -> List[str]:
    """Return a list of numbered strings for display purposes."""
    if not items:
        return []

    max_index = len(items) + start_num - 1
    if zero_padded:
        width = len(str(max_index))
        template = f"[{{:0{width}d}}] {{}}"
    else:
        template = "[{}] {}"

    return [template.format(index, item) for index, item in enumerate(items, start_num)]
