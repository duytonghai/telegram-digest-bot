"""Configuration management - loads environment variables."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class TelegramConfig:
    """Telegram API configuration."""
    api_id: int
    api_hash: str
    phone: str
    bot_token: str
    digest_chat_id: int
    source_group_ids: list[int]


@dataclass
class AIConfig:
    """AI providers configuration."""
    perplexity_api_key: str | None
    gemini_api_key: str | None
    openai_api_key: str | None
    primary_provider: str


@dataclass
class Config:
    """Application configuration."""
    telegram: TelegramConfig
    ai: AIConfig
    digest_schedule: str


def load_config() -> Config:
    """Load configuration from environment variables."""
    # Parse source group IDs (comma-separated)
    source_ids_str = os.getenv("SOURCE_GROUP_IDS", "")
    source_group_ids = []
    if source_ids_str and not source_ids_str.startswith("-100x"):
        source_group_ids = [
            int(gid.strip()) for gid in source_ids_str.split(",") if gid.strip()
        ]

    # Parse digest chat ID
    digest_chat_id_str = os.getenv("DIGEST_CHAT_ID", "0")
    digest_chat_id = 0
    if digest_chat_id_str and not digest_chat_id_str.startswith("-100x"):
        digest_chat_id = int(digest_chat_id_str)

    telegram_config = TelegramConfig(
        api_id=int(os.getenv("TELEGRAM_API_ID", "0")),
        api_hash=os.getenv("TELEGRAM_API_HASH", ""),
        phone=os.getenv("TELEGRAM_PHONE", ""),
        bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        digest_chat_id=digest_chat_id,
        source_group_ids=source_group_ids,
    )

    ai_config = AIConfig(
        perplexity_api_key=os.getenv("PERPLEXITY_API_KEY"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        primary_provider=os.getenv("PRIMARY_AI_PROVIDER", "perplexity"),
    )

    return Config(
        telegram=telegram_config,
        ai=ai_config,
        digest_schedule=os.getenv("DIGEST_SCHEDULE", "0 0 * * *"),
    )


# Global config instance
config = load_config()
