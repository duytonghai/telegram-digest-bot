"""Message collector - collects messages from Telegram groups via Telethon."""

import asyncio
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.tl.types import Message as TelethonMessage
from telethon.errors import FloodWaitError, ServerError, TimedOutError

from ..config import config
from ..database.db import Database, Message


class MessageCollector:
    """Collects messages from Telegram groups using Telethon user client."""

    SESSION_PATH = "sessions/telegram_user"

    def __init__(self, database: Database):
        self.db = database
        self.client: TelegramClient | None = None

    async def connect(self):
        """Connect to Telegram using existing session."""
        self.client = TelegramClient(
            self.SESSION_PATH,
            config.telegram.api_id,
            config.telegram.api_hash,
        )
        await self.client.connect()

        if not await self.client.is_user_authorized():
            raise RuntimeError(
                "Not authorized. Run 'python -m src.auth' first."
            )

    async def disconnect(self):
        """Disconnect from Telegram."""
        if self.client:
            await self.client.disconnect()

    async def collect_messages(
        self,
        hours_back: int = 24,
        limit_per_group: int = 1000,
    ) -> int:
        """Collect messages from all configured source groups.

        Args:
            hours_back: How many hours back to collect messages.
            limit_per_group: Maximum messages per group.

        Returns:
            Total number of new messages collected.
        """
        since = datetime.utcnow() - timedelta(hours=hours_back)
        total_collected = 0

        for group_id in config.telegram.source_group_ids:
            collected = await self._collect_from_group(
                group_id, since, limit_per_group
            )
            total_collected += collected
            print(f"Collected {collected} messages from {group_id}")

        return total_collected

    async def _collect_from_group(
        self,
        group_id: int,
        since: datetime,
        limit: int,
        max_retries: int = 3,
    ) -> int:
        """Collect messages from a single group with retry logic.

        Args:
            group_id: Telegram group ID (with -100 prefix).
            since: Collect messages after this time.
            limit: Maximum number of messages.
            max_retries: Maximum number of retry attempts.

        Returns:
            Number of messages collected.
        """
        for attempt in range(max_retries):
            try:
                return await self._collect_from_group_impl(group_id, since, limit)
            except FloodWaitError as e:
                wait_time = e.seconds
                print(f"⚠️ FloodWait: waiting {wait_time}s before retry...")
                await asyncio.sleep(wait_time)
            except (ServerError, TimedOutError, ConnectionError) as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    print(f"⚠️ Error collecting from {group_id}: {e}")
                    print(f"   Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"❌ Failed to collect from {group_id} after {max_retries} attempts")
                    raise
            except Exception as e:
                print(f"❌ Unexpected error collecting from {group_id}: {e}")
                raise

        return 0

    async def _collect_from_group_impl(
        self,
        group_id: int,
        since: datetime,
        limit: int,
    ) -> int:
        """Internal implementation of message collection from a single group.

        Args:
            group_id: Telegram group ID (with -100 prefix).
            since: Collect messages after this time.
            limit: Maximum number of messages.

        Returns:
            Number of messages collected.
        """
        try:
            entity = await self.client.get_entity(group_id)
            group_name = getattr(entity, "title", str(group_id))
        except Exception as e:
            print(f"Could not get entity for {group_id}: {e}")
            return 0

        collected = 0
        async for msg in self.client.iter_messages(
            entity,
            limit=limit,
            offset_date=None,
            reverse=False,
        ):
            # Skip if older than our cutoff
            if msg.date.replace(tzinfo=None) < since:
                break

            # Skip non-text messages
            if not isinstance(msg, TelethonMessage) or not msg.text:
                continue

            # Get sender name
            sender_name = "Unknown"
            if msg.sender:
                sender_name = getattr(
                    msg.sender, "first_name", None
                ) or getattr(msg.sender, "title", "Unknown")

            # Save to database
            message = Message(
                id=None,
                group_id=group_id,
                group_name=group_name,
                message_id=msg.id,
                sender_name=sender_name,
                text=msg.text,
                timestamp=msg.date.replace(tzinfo=None),
                collected_at=datetime.utcnow(),
            )

            await self.db.save_message(message)
            collected += 1

        return collected
