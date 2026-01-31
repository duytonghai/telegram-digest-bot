"""Test script to regenerate digest with new prompts."""

import asyncio
from src.database.db import get_database
from src.ai_providers.manager import AIProviderManager
from src.ai_providers.perplexity import PerplexityProvider
from src.analyzer.message_analyzer import MessageAnalyzer
from src.digest.digest_sender import DigestSender
from src.config import config


async def test_digest():
    """Test digest generation with all messages from database."""
    db = await get_database()

    try:
        # Setup AI provider
        ai_manager = AIProviderManager()
        if config.ai.perplexity_api_key:
            ai_manager.register(
                PerplexityProvider(config.ai.perplexity_api_key),
                is_primary=True,
            )

        # Get all messages from last 7 days (to ensure we get data)
        from datetime import datetime, timedelta
        since = datetime.utcnow() - timedelta(days=3)
        messages = await db.get_messages_since(since)

        if not messages:
            print("No messages found in the last 24 hours")
            return

        print(f"Found {len(messages)} messages to analyze")

        # Analyze
        analyzer = MessageAnalyzer(db, ai_manager)
        result = await analyzer.analyze_messages(messages)

        print(f"\n✅ Analysis complete (importance: {result.importance_score:.0%})")
        print(f"\n📊 Topics: {', '.join(result.topics)}")
        print(f"😊 Sentiment: {result.sentiment}")
        print(f"\n📝 Summary (first 500 chars):")
        print(result.summary[:500] + "...")

        # Send digest
        sender = DigestSender()
        await sender.send_digest(result, len(messages))
        print("\n✅ Digest sent to Telegram!")

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(test_digest())
