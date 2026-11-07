"""Main entry point - orchestrates all components."""

import asyncio
import signal
from datetime import datetime, timezone

from .config import config
from .database.db import get_database
from .collector.message_collector import MessageCollector
from .analyzer.message_analyzer import MessageAnalyzer
from .digest.digest_sender import DigestSender
from .scheduler.job_scheduler import JobScheduler
from .analyzer.result_validator import has_signal
from .ai_providers.factory import build_ai_manager


async def run_digest():
    """Run a single digest cycle: collect, analyze, send."""
    print(f"\n{'='*50}")
    print(f"🚀 Starting digest run at {datetime.now(timezone.utc)}")
    print(f"{'='*50}\n")

    # Initialize components
    db = await get_database()

    try:
        # Setup AI providers
        ai_manager = build_ai_manager()

        # Collect messages
        print("📥 Collecting messages...")
        collector = MessageCollector(db)
        await collector.connect()
        message_count = await collector.collect_messages(hours_back=24)
        await collector.disconnect()
        print(f"✅ Collected {message_count} messages")

        if message_count == 0:
            print("ℹ️ No new messages to analyze")
            return

        # Analyze messages by group
        print("\n🤖 Analyzing messages by group...")
        analyzer = MessageAnalyzer(db, ai_manager)
        results = await analyzer.analyze_recent_messages()

        if not results:
            print("ℹ️ No groups with sufficient messages to analyze (minimum 3 per group)")
            return

        # Send separate digest for each group
        print(f"\n📤 Sending {len(results)} digests...")
        sender = DigestSender()

        for group_name, result, msg_count in results:
            if not has_signal(result):
                print(f"  ⏭️  Skipping '{group_name}' (no news value)")
                await db.record_digest(msg_count, f"{group_name}: skipped, no news value")
                continue

            print(f"  📨 Sending digest for '{group_name}' ({msg_count} messages, importance: {result.importance_score:.0%})")
            await sender.send_digest(result, msg_count, group_name)

            # Record digest for this group
            await db.record_digest(msg_count, f"{group_name}: {result.summary[:300]}")

        print("✅ All digests sent!")

    finally:
        await db.close()

    print(f"\n{'='*50}")
    print(f"✅ Digest run complete")
    print(f"{'='*50}\n")


async def main():
    """Main entry point with scheduler."""
    print("🤖 Telegram AI Digest Bot")
    print(f"Primary AI: {config.ai.primary_provider}")
    print(f"Source groups: {len(config.telegram.source_group_ids)}")
    print(f"Digest schedule: {config.digest_schedule}")
    print()

    # Get current event loop
    loop = asyncio.get_running_loop()

    # Setup scheduler with the event loop
    scheduler = JobScheduler(event_loop=loop)
    scheduler.add_digest_job(run_digest)
    scheduler.start()
    scheduler.show_next_run()

    # Run initial digest
    try:
        await run_digest()
    except Exception as e:
        print(f"❌ Initial digest failed: {e}")

    # Keep running indefinitely
    stop_event = asyncio.Event()

    def signal_handler():
        print("\n🛑 Shutting down...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    print("\n✅ Bot is running. Waiting for scheduled jobs...")
    print("   Press Ctrl+C to stop.\n")

    # Wait forever until signal
    try:
        await stop_event.wait()
    finally:
        scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
