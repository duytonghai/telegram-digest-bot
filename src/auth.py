"""Telegram authentication - creates Telethon session interactively."""

import asyncio
from telethon import TelegramClient
from .config import config

SESSION_PATH = "sessions/telegram_user"


async def authenticate():
    """Run interactive authentication to create session file."""
    if not config.telegram.phone or not config.telegram.phone.startswith("+"):
        print("❌ Error: TELEGRAM_PHONE must be set in .env with format +1234567890")
        return

    print(f"Phone: {config.telegram.phone}")
    print(f"API ID: {config.telegram.api_id}")
    print()

    client = TelegramClient(
        SESSION_PATH,
        config.telegram.api_id,
        config.telegram.api_hash,
    )

    await client.start(phone=config.telegram.phone)

    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"✅ Authenticated as: {me.first_name} (@{me.username})")
        print(f"📁 Session saved to: {SESSION_PATH}.session")
    else:
        print("❌ Authentication failed")

    await client.disconnect()


def main():
    """Entry point for authentication."""
    # Ensure sessions directory exists
    import os
    os.makedirs("sessions", exist_ok=True)

    print("🔐 Telegram Authentication")
    print("-" * 40)
    asyncio.run(authenticate())


if __name__ == "__main__":
    main()
