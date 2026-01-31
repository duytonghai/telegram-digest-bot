"""Message analyzer - orchestrates AI analysis of collected messages."""

from datetime import datetime

from ..database.db import Database, Message
from ..ai_providers.manager import AIProviderManager
from ..ai_providers.base import AnalysisResult, SummaryItem, AssessmentItem, FactCheckItem


# Maximum messages per chunk to avoid token overflow
MAX_MESSAGES_PER_CHUNK = 300


class MessageAnalyzer:
    """Orchestrates message analysis using AI providers."""

    def __init__(self, database: Database, ai_manager: AIProviderManager):
        self.db = database
        self.ai_manager = ai_manager

    async def analyze_recent_messages(self) -> list[tuple[str, AnalysisResult, int]] | None:
        """Analyze unprocessed messages grouped by source.

        Returns:
            List of tuples (group_name, AnalysisResult, message_count) for each group,
            or None if no messages to analyze.
        """
        messages = await self.db.get_unprocessed_messages()

        if not messages:
            return None

        return await self.analyze_messages_by_group(messages)

    async def analyze_messages_by_group(
        self, messages: list[Message]
    ) -> list[tuple[str, AnalysisResult, int]]:
        """Analyze messages separately for each group.

        Args:
            messages: List of Message objects to analyze.

        Returns:
            List of tuples (group_name, AnalysisResult, message_count) for each group.
        """
        # Group messages by source group
        groups = {}
        for msg in messages:
            if msg.group_name not in groups:
                groups[msg.group_name] = []
            groups[msg.group_name].append(msg)

        results = []

        # Analyze each group separately
        for group_name, group_messages in groups.items():
            print(f"  🔍 Analyzing {len(group_messages)} messages from '{group_name}'...")
            result = await self.analyze_single_group(group_messages)
            results.append((group_name, result, len(group_messages)))

        return results

    async def analyze_single_group(self, messages: list[Message]) -> AnalysisResult:
        """Analyze messages from a single group with chunking support.

        Args:
            messages: List of Message objects from the same group.

        Returns:
            AnalysisResult from AI provider (merged if chunked).
        """
        # Prepare message texts
        message_texts = [msg.text for msg in messages if msg.text]

        # Check if chunking is needed
        if len(message_texts) <= MAX_MESSAGES_PER_CHUNK:
            return await self._analyze_chunk(message_texts, messages)

        # Chunk messages and analyze separately, then merge
        print(f"    📦 Large batch ({len(message_texts)} msgs), splitting into chunks of {MAX_MESSAGES_PER_CHUNK}...")
        chunks = [
            message_texts[i:i + MAX_MESSAGES_PER_CHUNK]
            for i in range(0, len(message_texts), MAX_MESSAGES_PER_CHUNK)
        ]

        chunk_results = []
        for i, chunk in enumerate(chunks, 1):
            print(f"    📊 Analyzing chunk {i}/{len(chunks)} ({len(chunk)} messages)...")
            result = await self._analyze_chunk(chunk, messages)
            chunk_results.append(result)

        # Merge results from all chunks
        return self._merge_results(chunk_results)

    async def _analyze_chunk(self, message_texts: list[str], messages: list[Message]) -> AnalysisResult:
        """Analyze a single chunk of messages.

        Args:
            message_texts: List of message text strings.
            messages: Original Message objects (for context).

        Returns:
            AnalysisResult from AI provider.
        """
        # Get topic types for this group
        from ..config import config
        group_id = messages[0].group_id if messages else None
        topic_types = config.telegram.source_groups.get(group_id, ["general"])

        context = {
            "group_name": messages[0].group_name if messages else "Unknown",
            "date_range": self._get_date_range(messages),
            "message_count": len(message_texts),
            "topic_types": topic_types,  # Pass topic types to AI provider
        }

        return await self.ai_manager.analyze(message_texts, context)

    def _merge_results(self, results: list[AnalysisResult]) -> AnalysisResult:
        """Merge multiple AnalysisResults into one.

        Args:
            results: List of AnalysisResult objects to merge.

        Returns:
            Single merged AnalysisResult.
        """
        if not results:
            return AnalysisResult(
                summary=[],
                assessment=[],
                fact_check=[],
                sentiment="neutral",
                topics=[],
                importance_score=0.0,
            )

        if len(results) == 1:
            return results[0]

        # Merge summaries (dedupe by text similarity)
        all_summaries = []
        seen_texts = set()
        for r in results:
            for item in r.summary:
                # Simple dedup by first 50 chars
                key = item.text[:50].lower()
                if key not in seen_texts:
                    seen_texts.add(key)
                    all_summaries.append(item)

        # Merge assessments (dedupe by text similarity)
        all_assessments = []
        seen_texts = set()
        for r in results:
            for item in r.assessment:
                key = item.text[:50].lower()
                if key not in seen_texts:
                    seen_texts.add(key)
                    all_assessments.append(item)

        # Merge fact checks (dedupe by claim)
        all_fact_checks = []
        seen_claims = set()
        for r in results:
            for item in r.fact_check:
                key = item.claim[:50].lower()
                if key not in seen_claims:
                    seen_claims.add(key)
                    all_fact_checks.append(item)

        # Merge topics (unique)
        all_topics = list(set(topic for r in results for topic in r.topics))

        # Merge unknowns (unique)
        all_unknowns = list(set(u for r in results for u in r.unknowns))

        # Calculate average importance and determine overall sentiment
        avg_importance = sum(r.importance_score for r in results) / len(results)
        sentiments = [r.sentiment for r in results]
        if len(set(sentiments)) == 1:
            overall_sentiment = sentiments[0]
        else:
            overall_sentiment = "mixed"

        # Use first result's language
        language = results[0].language

        return AnalysisResult(
            summary=all_summaries[:12],  # Cap at 12 items
            assessment=all_assessments[:8],  # Cap at 8 items
            fact_check=all_fact_checks[:5],  # Cap at 5 items
            sentiment=overall_sentiment,
            topics=all_topics,
            importance_score=avg_importance,
            language=language,
            unknowns=all_unknowns[:5],
            raw_response="[Merged from multiple chunks]",
        )

    def _get_date_range(self, messages: list[Message]) -> str:
        """Get human-readable date range from messages."""
        if not messages:
            return "No messages"

        timestamps = [msg.timestamp for msg in messages]
        min_time = min(timestamps)
        max_time = max(timestamps)

        if min_time.date() == max_time.date():
            return min_time.strftime("%Y-%m-%d")
        else:
            return f"{min_time.strftime('%Y-%m-%d')} to {max_time.strftime('%Y-%m-%d')}"
