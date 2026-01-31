"""Utility to get Telegram chat IDs."""

import asyncio
from telethon import TelegramClient

from ..config import config

SESSION_PATH = "sessions/telegram_user"


async def list_dialogs():
    """List all dialogs (chats) the user is a member of."""
    client = TelegramClient(
        SESSION_PATH,
        config.telegram.api_id,
        config.telegram.api_hash,
    )

    await client.connect()

    if not await client.is_user_authorized():
        print("❌ Not authorized. Run 'python -m src.auth' first.")
        return

    print("\n📋 Your Telegram Chats:")
    print("-" * 60)
    print(f"{'Name':<40} {'ID':<20}")
    print("-" * 60)

    async for dialog in client.iter_dialogs():
        name = dialog.name or "Unknown"
        chat_id = dialog.id

        # Format ID with -100 prefix for supergroups/channels
        if hasattr(dialog.entity, "megagroup") or hasattr(
            dialog.entity, "broadcast"
        ):
            formatted_id = f"-100{chat_id}"
        elif chat_id < 0:
            formatted_id = str(chat_id)
        else:
            formatted_id = str(chat_id)

        print(f"{name[:39]:<40} {formatted_id:<20}")

    print("-" * 60)
    await client.disconnect()


def main():
    """Entry point."""
    asyncio.run(list_dialogs())


if __name__ == "__main__":
    main()
