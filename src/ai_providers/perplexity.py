"""Perplexity AI provider implementation."""

import asyncio
import json
import httpx
from .base import (
    BaseAIProvider,
    AnalysisResult,
    SummaryItem,
    AssessmentItem,
    FactCheckItem,
)
from ..prompts import get_analysis_user_prompt, get_ai_parameters, get_api_config


class PerplexityProvider(BaseAIProvider):
    """Perplexity AI provider for message analysis."""

    API_URL = "https://api.perplexity.ai/chat/completions"

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.name = "perplexity"
        # Use valid Perplexity model
        self.model = "sonar-pro"

    async def analyze(
        self, messages: list[str], context: dict
    ) -> AnalysisResult:
        """Analyze messages using Perplexity API."""
        # Get topic types from context
        topic_types = context.get('topic_types', ['general'])

        # Generate user prompt from template
        user_prompt = get_analysis_user_prompt(
            messages=messages,
            group_name=context.get('group_name', 'Unknown'),
            date_range=context.get('date_range', 'Today'),
        )

        # Get system prompt with specialized rules based on topics
        system_prompt = self.get_system_prompt(topic_types)

        # Get configuration from prompts module
        api_config = get_api_config('perplexity')
        ai_params = get_ai_parameters('factual')

        max_retries = api_config['max_retries']
        retry_delay = api_config['retry_delay']

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.API_URL,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self.model,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            # Parameters from prompt config
                            **ai_params,
                        },
                        timeout=api_config['timeout'],
                    )

                    # Better error handling
                    if response.status_code != 200:
                        error_text = response.text
                        raise Exception(f"Perplexity API error {response.status_code}: {error_text}")

                    data = response.json()
                    break  # Success, exit retry loop

            except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadTimeout) as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    print(f"⚠️ API timeout/error: {e}")
                    print(f"   Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"❌ Failed after {max_retries} attempts")
                    raise
            except Exception as e:
                if attempt < max_retries - 1 and "429" in str(e):  # Rate limit
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"⚠️ Rate limit hit, waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    raise

        raw_content = data["choices"][0]["message"]["content"]

        # Parse JSON from response
        try:
            # Try to extract JSON from markdown code blocks
            if "```json" in raw_content:
                json_str = raw_content.split("```json")[1].split("```")[0]
            elif "```" in raw_content:
                json_str = raw_content.split("```")[1].split("```")[0]
            else:
                json_str = raw_content

            parsed = json.loads(json_str.strip())
        except json.JSONDecodeError:
            # Fallback to basic parsing with default structure
            parsed = {
                "summary": [{"type": "fact", "text": raw_content[:500], "sources": [], "raw_quotes": []}],
                "assessment": [],
                "fact_check": [],
                "sentiment": "neutral",
                "topics": ["Other"],
                "importance_score": 0.5,
                "language": "vi",
                "unknowns": ["Failed to parse AI response"],
            }

        # Parse summary items
        summary_items = []
        raw_summary = parsed.get("summary", [])
        if isinstance(raw_summary, list):
            for item in raw_summary:
                if isinstance(item, dict):
                    summary_items.append(SummaryItem(
                        type=item.get("type", "fact"),
                        text=item.get("text", ""),
                        sources=item.get("sources", []),
                        raw_quotes=item.get("raw_quotes", []),
                    ))
                elif isinstance(item, str):
                    summary_items.append(SummaryItem(type="fact", text=item, sources=[], raw_quotes=[]))
        elif isinstance(raw_summary, str):
            # Legacy format: split string into items
            for line in raw_summary.split("\n"):
                if line.strip():
                    summary_items.append(SummaryItem(type="fact", text=line.strip(), sources=[], raw_quotes=[]))

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
                        confidence=float(item.get("confidence", 0.0)),
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
                        confidence=float(claim.get("confidence", default_confidence)),
                    ))
                elif isinstance(claim, str):
                    fact_check_items.append(FactCheckItem(
                        claim=claim,
                        sources=[],
                        status="single_source",
                        confidence=float(default_confidence),
                    ))

        return AnalysisResult(
            summary=summary_items,
            assessment=assessment_items,
            fact_check=fact_check_items,
            sentiment=parsed.get("sentiment", "neutral"),
            topics=parsed.get("topics", ["Other"]),
            importance_score=float(parsed.get("importance_score", 0.5)),
            language=parsed.get("language", "vi"),
            unknowns=parsed.get("unknowns", []),
            raw_response=raw_content,
        )
