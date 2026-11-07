"""Abstract base class for AI providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..prompts import get_base_system_prompt


def _to_float(value, default: float) -> float:
    """Read a number from AI output. Fall back when it is not numeric."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass
class SummaryItem:
    """A single summary item with source attribution."""
    type: str  # reported, opinion, rumor
    text: str
    sources: list[str] = field(default_factory=list)
    raw_quotes: list[str] = field(default_factory=list)


@dataclass
class AssessmentItem:
    """A single assessment/insight item."""
    label: str  # e.g., "Risk signal", "Potential opportunity"
    text: str
    evidence_sources: list[str] = field(default_factory=list)


@dataclass
class FactCheckItem:
    """A single fact-check claim."""
    claim: str
    sources: list[str] = field(default_factory=list)
    status: str = "not_checkable"  # corroborated_in_chat, conflicting_in_chat, single_source, not_checkable
    confidence: float = 0.0


@dataclass
class AnalysisResult:
    """Structured result from AI analysis."""
    summary: list[SummaryItem]  # Up to 12 items with source attribution
    assessment: list[AssessmentItem]  # Up to 8 AI insights/risks/opportunities
    fact_check: list[FactCheckItem]  # Verifiable claims with confidence
    sentiment: str  # positive, negative, neutral, mixed
    topics: list[str]  # e.g., ["Crypto", "Finance", "Geopolitics"]
    importance_score: float  # 0.0-1.0
    language: str = "vi"  # vi, en, mixed
    unknowns: list[str] = field(default_factory=list)  # Missing key details
    raw_response: str = ""  # Original AI response for debugging
    metadata: dict = field(default_factory=dict)


class BaseAIProvider(ABC):
    """Abstract base class for AI providers.

    All AI providers must extend this class and implement the analyze method.

    Example:
        class MyProvider(BaseAIProvider):
            def __init__(self, api_key: str):
                super().__init__(api_key)
                self.name = "my_provider"

            async def analyze(self, messages, context) -> AnalysisResult:
                # Implementation
                pass
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.name = "base"

    @abstractmethod
    async def analyze(
        self, messages: list[dict], context: dict
    ) -> AnalysisResult:
        """Analyze messages and return structured result.

        Args:
            messages: Message dicts to analyze.
            context: Additional context (e.g., group name, date range).

        Returns:
            AnalysisResult with summary, fact-check, sentiment, etc.
        """
        pass

    def get_system_prompt(self, topic_types: list[str] = None) -> str:
        """Get system prompt with specialized rules based on topic types.

        Args:
            topic_types: List of topic types (e.g., ["crypto", "finance"]).

        Returns:
            str: System prompt with merged specialized rules.
        """
        from ..prompts import get_system_prompt

        if not topic_types or topic_types == ["general"]:
            return get_base_system_prompt()

        # Start with base prompt
        base = get_base_system_prompt()

        # Collect all specialized rules
        specialized_rules = []

        if "crypto" in topic_types:
            crypto_rules = """
CRYPTO-SPECIFIC RULES (apply in addition to base rules)
- Preserve price strings EXACTLY as posted (e.g., "$45,123.45", "45k", "45123").
- If timeframe is stated (e.g., 24h, 7d), include it; otherwise mark unknown.
- Distinguish spot vs futures ONLY if explicitly stated.
- If an exchange is mentioned, include it in the summary item.
- Any "signal/call/entry/exit" must be labeled as opinion (type="opinion" or "rumor")."""
            specialized_rules.append(crypto_rules.strip())

        if "finance" in topic_types:
            finance_rules = """
FINANCE-SPECIFIC RULES (apply in addition to base rules)
- Preserve rates/percentages EXACTLY as posted (e.g., "0.25%").
- Distinguish announced vs implemented ONLY if explicitly stated.
- If a statement is "analyst expectations / forecasts / guidance", label as opinion.
- Include dates if explicitly stated; otherwise mark unknown."""
            specialized_rules.append(finance_rules.strip())

        # Merge specialized rules into base prompt
        if specialized_rules:
            merged_rules = "\n\n".join(specialized_rules)
            return base.replace(
                "Return ONLY the JSON object.",
                merged_rules + "\n\nReturn ONLY the JSON object."
            )

        return base

    def _build_result(self, parsed: dict, raw_content: str) -> AnalysisResult:
        """Convert parsed AI JSON into an AnalysisResult."""
        # Parse summary items
        summary_items = []
        raw_summary = parsed.get("summary", [])
        if isinstance(raw_summary, list):
            for item in raw_summary:
                if isinstance(item, dict):
                    summary_items.append(SummaryItem(
                        type=item.get("type", "reported"),
                        text=item.get("text", ""),
                        sources=item.get("sources", []),
                        raw_quotes=item.get("raw_quotes", []),
                    ))
                elif isinstance(item, str):
                    summary_items.append(SummaryItem(type="reported", text=item, sources=[], raw_quotes=[]))
        elif isinstance(raw_summary, str):
            # Legacy format: split string into items
            for line in raw_summary.split("\n"):
                if line.strip():
                    summary_items.append(SummaryItem(type="reported", text=line.strip(), sources=[], raw_quotes=[]))

        # Parse assessment items
        assessment_items = []
        raw_assessment = parsed.get("assessment", [])
        if isinstance(raw_assessment, list):
            for item in raw_assessment:
                if isinstance(item, dict):
                    assessment_items.append(AssessmentItem(
                        label=item.get("label", "Nhận xét"),
                        text=item.get("text", ""),
                        evidence_sources=item.get("evidence_sources", []),
                    ))
                elif isinstance(item, str):
                    assessment_items.append(AssessmentItem(label="Nhận xét", text=item, evidence_sources=[]))
        elif isinstance(raw_assessment, str):
            for line in raw_assessment.split("\n"):
                if line.strip():
                    assessment_items.append(AssessmentItem(label="Nhận xét", text=line.strip(), evidence_sources=[]))

        # Parse fact-check items
        fact_check_items = []
        raw_fact_check = parsed.get("fact_check", [])
        if isinstance(raw_fact_check, list):
            for item in raw_fact_check:
                if isinstance(item, dict):
                    fact_check_items.append(FactCheckItem(
                        claim=item.get("claim", ""),
                        sources=item.get("sources", []),
                        status=item.get("status", "not_checkable"),
                        confidence=_to_float(item.get("confidence"), 0.0),
                    ))
        elif isinstance(raw_fact_check, dict):
            # Legacy format: {"claims": [...], "confidence": 0.5}
            claims = raw_fact_check.get("claims", [])
            default_confidence = raw_fact_check.get("confidence", 0.5)
            for claim in claims:
                if isinstance(claim, dict):
                    fact_check_items.append(FactCheckItem(
                        claim=claim.get("claim", str(claim)),
                        sources=claim.get("sources", []),
                        status=claim.get("status", "single_source"),
                        confidence=_to_float(claim.get("confidence"), default_confidence),
                    ))
                elif isinstance(claim, str):
                    fact_check_items.append(FactCheckItem(
                        claim=claim,
                        sources=[],
                        status="single_source",
                        confidence=_to_float(default_confidence, 0.5),
                    ))

        return AnalysisResult(
            summary=summary_items,
            assessment=assessment_items,
            fact_check=fact_check_items,
            sentiment=parsed.get("sentiment", "neutral"),
            topics=parsed.get("topics", ["Other"]),
            importance_score=_to_float(parsed.get("importance_score"), 0.5),
            language=parsed.get("language", "vi"),
            unknowns=parsed.get("unknowns", []),
            raw_response=raw_content,
        )

    async def health_check(self) -> bool:
        """Check if the provider is operational."""
        return bool(self.api_key)
