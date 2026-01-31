"""Message analyzer - orchestrates AI analysis of collected messages."""

from datetime import datetime

from ..database.db import Database, Message
from ..ai_providers.manager import AIProviderManager
from ..ai_providers.base import AnalysisResult


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
        """Analyze messages from a single group.

        Args:
            messages: List of Message objects from the same group.

        Returns:
            AnalysisResult from AI provider.
        """
        # Prepare message texts
        message_texts = [msg.text for msg in messages if msg.text]

        # Build context for this specific group
        context = {
            "group_name": messages[0].group_name if messages else "Unknown",
            "date_range": self._get_date_range(messages),
            "message_count": len(messages),
        }

        # Run analysis
        result = await self.ai_manager.analyze(message_texts, context)

        return result

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
