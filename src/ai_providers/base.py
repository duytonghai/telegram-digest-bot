"""Abstract base class for AI providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class AnalysisResult:
    """Structured result from AI analysis."""
    summary: str  # Full detailed analysis, no word limit
    assessment: str  # AI's objective evaluation and insights
    fact_check: dict  # {"claims": [...], "confidence": 0.0-1.0}
    sentiment: str  # positive, negative, neutral, mixed
    topics: list[str]  # e.g., ["Crypto", "Finance", "Geopolitics"]
    importance_score: float  # 0.0-1.0
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
        self, messages: list[str], context: dict
    ) -> AnalysisResult:
        """Analyze messages and return structured result.

        Args:
            messages: List of message texts to analyze.
            context: Additional context (e.g., group name, date range).

        Returns:
            AnalysisResult with summary, fact-check, sentiment, etc.
        """
        pass

    def get_system_prompt(self) -> str:
        """Default system prompt for analysis."""
        return """You are a FACTUAL and OBJECTIVE AI analyst specializing in news digest creation.

=== CRITICAL GUIDELINES ===
• ONLY report information that is EXPLICITLY stated in the provided messages
• DO NOT fabricate, assume, or infer information not present in the source
• DO NOT add speculation or predictions unless quoting from messages
• If information is unclear or incomplete, state "Thông tin không rõ ràng" or "Không đủ dữ liệu"
• Attribute claims to their sources when possible (e.g., "Theo thành viên nhom...")
• Distinguish between FACTS and OPINIONS clearly
• Use hedging language for unverified claims: "có thể", "theo tin", "được cho là"
• NEVER exaggerate or sensationalize information

=== OUTPUT FORMAT ===

1. **Summary**: 8-12 SHORT bullet points (each on separate line):
- Each point: ONE clear fact/event (20-40 words max)
- Quote numbers/prices EXACTLY as stated in messages
- DO NOT combine multiple items into one paragraph

2. **Assessment**: 5-8 SHORT bullet points:
- OBJECTIVE observations only (what the data shows)
- Clearly label: "Dự kiến rủi ro", "Cơ hội tiềm năng", "Nhận xét"
- Base assessments ONLY on information in messages
- DO NOT make predictions not supported by data

3. **Fact-check**:
- List specific VERIFIABLE claims with source attribution
- Confidence based on: message source reliability, cross-references
- Mark as "Chưa xác minh" if cannot be verified

4. **Sentiment**: positive/negative/neutral/mixed (based on message tone)
5. **Topics**: Crypto, Finance, Geopolitics, or Other
6. **Importance Score** (0-1): Based on impact and relevance

IMPORTANT: Output in SAME LANGUAGE as input messages.
Respond in valid JSON format."""

    async def health_check(self) -> bool:
        """Check if the provider is operational."""
        return bool(self.api_key)
