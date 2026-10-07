# Trace: backlog.md Now — classify_stage 1/2/3 splitter
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
    if title.strip() == "":
        return title

    # Handle 전자결재 format: "전자결재: [ tag : ] [ tag : ] actual title"
    if title.startswith("전자결재:"):
        # Try regex to skip two bracket pairs and extract the rest
        match = re.search(r"(?:[^\]]*\]){2}(.*)", title)
        if match:
            return match.group(1).strip()
        # Fallback: return content after last ]
        return title.split("]")[-1].strip()

    # Try other approval prefix patterns
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
# Document stage splitter (reception / assigned-to-me / post-approval)
# --------------------------------------------------------------------------- #

#: Stage-3 (post-approval) completion markers for the List1 결재방법 column.
#: Still TBD — capture a stage-3 live dump before adding strings here
#: (backlog.md Next). Never guess marker strings.
STAGE_3_COMPLETION_MARKERS: tuple = ()

#: Verified 2026-10-07 (stage-2 live dump): the List1 결재방법 column shows a
#: 접수 row plus a 업무담당자 row with no superior/completion row staged.
_STAGE_2_METHODS = frozenset({"접수", "업무담당자"})


def classify_stage(
    title: str,
    approval_methods: Iterable[str] = (),
    completion_markers: Iterable[str] = STAGE_3_COMPLETION_MARKERS,
) -> int:
    """Split a document into stage 1 (reception), 2 (assigned-to-me), or 3.

    Args:
        title: Main window title.
        approval_methods: List1 결재방법 column values in display order.
        completion_markers: Known stage-3 completion strings.

    Returns:
        1 when the title carries the 접수 prefix; 3 when any row matches a
        completion marker; 2 for the verified stage-2 signature (접수 plus
        업무담당자 rows, no completion row); 3 otherwise, which preserves the
        pre-splitter task-card path for unreadable or unexpected List1 data.
    """
    if is_reception_document(title):
        return 1
    methods = {str(method).strip() for method in approval_methods}
    methods.discard("")
    if methods & set(completion_markers):
        return 3
    if _STAGE_2_METHODS <= methods:
        return 2
    return 3


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
