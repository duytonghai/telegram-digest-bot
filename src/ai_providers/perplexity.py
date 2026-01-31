"""Perplexity AI provider implementation."""

import asyncio
import json
import httpx
from .base import BaseAIProvider, AnalysisResult


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
        combined_text = "\n---\n".join(messages)

        user_prompt = f"""Analyze these messages from a Telegram group:

Group: {context.get('group_name', 'Unknown')}
Date Range: {context.get('date_range', 'Today')}
Message Count: {len(messages)}

Messages:
{combined_text}

=== STRICT REQUIREMENTS ===
• ONLY include information EXPLICITLY stated in the messages above
• DO NOT fabricate, assume, or add information not in the source
• Quote numbers, prices, percentages EXACTLY as stated
• If something is unclear, say "không rõ" or "thiếu dữ liệu"
• Distinguish facts from opinions (mark opinions as "theo ý kiến...")

Provide analysis in JSON format with keys:
- summary (string): 8-12 bullet points, each on new line. FACTS ONLY from messages.
- assessment (string): 5-8 bullet points. OBJECTIVE observations based on data in messages. Label each as insight/risk/opportunity.
- fact_check (object): {{"claims": [list of verifiable claims with sources], "confidence": 0-1 based on source reliability}}
- sentiment (string): positive/negative/neutral/mixed
- topics (array): from [Crypto, Finance, Geopolitics, Other]
- importance_score (float 0-1)

Write in the SAME LANGUAGE as the messages (Vietnamese if Vietnamese).
"""

        max_retries = 3
        retry_delay = 1

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
                                {"role": "system", "content": self.get_system_prompt()},
                                {"role": "user", "content": user_prompt},
                            ],
                            # Parameters for factual, coherent output
                            "temperature": 0.2,  # Low for factual accuracy
                            "top_p": 0.9,  # Focused probability distribution
                            "max_tokens": 4000,  # Enough for detailed analysis
                        },
                        timeout=120.0,
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
            # Fallback to basic parsing
            parsed = {
                "summary": raw_content[:500],
                "fact_check": {"claims": [], "confidence": 0.5},
                "sentiment": "neutral",
                "topics": ["Other"],
                "importance_score": 0.5,
            }

        return AnalysisResult(
            summary=parsed.get("summary", ""),  # No truncation - full content
            assessment=parsed.get("assessment", ""),  # AI's evaluation
            fact_check=parsed.get("fact_check", {"claims": [], "confidence": 0.5}),
            sentiment=parsed.get("sentiment", "neutral"),
            topics=parsed.get("topics", ["Other"]),
            importance_score=float(parsed.get("importance_score", 0.5)),
            raw_response=raw_content,
        )
