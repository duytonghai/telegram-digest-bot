"""Checks AI output against the messages it was given."""

from ..ai_providers.base import AnalysisResult
from ..prompts import get_item_limits

SUMMARY_TYPES = {"reported", "opinion", "rumor"}
FACT_STATUSES = {
    "corroborated_in_chat",
    "conflicting_in_chat",
    "single_source",
    "not_checkable",
}
SENTIMENTS = {"positive", "negative", "neutral", "mixed"}
LANGUAGES = {"vi", "en", "mixed"}
TOPICS = {"Crypto", "Finance", "Economy", "Politics", "Geopolitics", "Society", "Other"}

# The prompt rubric calls 0.0-0.2 chatter.
MIN_IMPORTANCE = 0.2
MAX_CONFIDENCE_ONE_MESSAGE = 0.4
MAX_CONFIDENCE_ONE_ORIGIN = 0.6


def _clamp(value: float) -> float:
    return min(1.0, max(0.0, value))


def _pick(value, allowed: set[str], default: str) -> str:
    """Return value if allowed. AI output can hold any JSON type here."""
    return value if isinstance(value, str) and value in allowed else default


def _has_text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _known_sources(sources, origins: dict[str, str]) -> list[str]:
    """Keep citations of real messages, in order, without duplicates."""
    if not isinstance(sources, list):
        sources = [sources]
    kept = []
    for source in sources:
        key = str(source).strip().strip("[]")
        if key in origins and key not in kept:
            kept.append(key)
    return kept


def _check_fact(item, origins: dict[str, str]) -> None:
    """Make status and confidence match what the citations can support."""
    item.status = _pick(item.status, FACT_STATUSES, "not_checkable")

    independent = len({origins[s] for s in item.sources}) >= 2
    if independent:
        item.confidence = _clamp(item.confidence)
        return

    if item.status == "corroborated_in_chat":
        item.status = "single_source"
    limit = MAX_CONFIDENCE_ONE_ORIGIN if len(item.sources) > 1 else MAX_CONFIDENCE_ONE_MESSAGE
    item.confidence = min(_clamp(item.confidence), limit)


def sanitize_result(result: AnalysisResult, records: list[dict]) -> AnalysisResult:
    """Remove or correct AI output that the messages do not support.

    Items with no valid citation are dropped. Two messages count as independent
    only if they differ in forward origin, or in sender when not forwarded.

    Args:
        result: Parsed AI result.
        records: The prompt records this result was built from.

    Returns:
        The same result, corrected in place.
    """
    origins = {
        str(r["id"]): r.get("forwarded_from") or r["sender"]
        for r in records
    }
    limits = get_item_limits(len(records))

    summary = []
    for item in result.summary:
        item.sources = _known_sources(item.sources, origins)
        if item.sources and _has_text(item.text):
            # An unknown label must not read as a stronger claim.
            item.type = "reported" if item.type == "fact" else item.type
            item.type = _pick(item.type, SUMMARY_TYPES, "opinion")
            summary.append(item)
    result.summary = summary[:limits["summary"]]

    assessment = []
    for item in result.assessment:
        item.evidence_sources = _known_sources(item.evidence_sources, origins)
        if item.evidence_sources and _has_text(item.text):
            assessment.append(item)
    result.assessment = assessment[:limits["assessment"]]

    fact_check = []
    for item in result.fact_check:
        item.sources = _known_sources(item.sources, origins)
        if item.sources and _has_text(item.claim):
            _check_fact(item, origins)
            fact_check.append(item)
    result.fact_check = fact_check[:limits["fact_check"]]

    result.importance_score = _clamp(result.importance_score)
    result.sentiment = _pick(result.sentiment, SENTIMENTS, "neutral")
    result.language = _pick(result.language, LANGUAGES, "mixed")
    topics = result.topics if isinstance(result.topics, list) else []
    result.topics = [t for t in topics if _pick(t, TOPICS, "")] or ["Other"]
    unknowns = result.unknowns if isinstance(result.unknowns, list) else []
    result.unknowns = unknowns[:limits["unknowns"]]
    return result


def has_signal(result: AnalysisResult) -> bool:
    """Return True if the result is worth sending."""
    return bool(result.summary) and result.importance_score >= MIN_IMPORTANCE
