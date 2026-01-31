# Telegram AI Digest Bot - Copilot Instructions

## Project Overview

A Telegram bot that collects messages from private groups via Telethon (user client), analyzes them using AI providers, and sends daily digests via python-telegram-bot. Uses SQLite for message storage.

## Architecture Pattern

**Dual-client architecture**: Two separate Telegram connections:

1. **User Client (Telethon)** - Reads messages from private groups as a member
2. **Bot Client (python-telegram-bot)** - Sends formatted digests to destination group

Data flows: Private Groups → Telethon Collector → SQLite → AI Processor → Bot Client → Digest Group

## Directory Structure (To Be Implemented)

```
src/
├── main.py              # Entry point, orchestration
├── auth.py              # Telethon session auth (phone + code)
├── config.py            # Environment loading
├── collector/           # Message collection from groups
├── database/            # SQLite operations
├── ai_providers/        # Pluggable AI provider pattern
├── analyzer/            # Message analysis orchestration
├── digest/              # Digest formatting and sending
└── scheduler/           # APScheduler for daily cron jobs
```

## AI Provider Pattern

All AI providers must extend `BaseAIProvider` abstract class:

- Implement `analyze(messages: list[str], context: dict) -> AnalysisResult`
- Return structured data: summary (max 500 words), fact-check with confidence, sentiment, topics, importance score
- Providers: Perplexity (primary), Gemini (fallback), OpenAI (fallback)
- Registration in `ai_providers/manager.py`

## Key Technical Decisions

- **Async throughout**: Use `asyncio` with async/await for Telethon and HTTP calls
- **Telethon sessions**: Persist in `sessions/` directory, requires one-time interactive auth
- **Chat IDs**: All Telegram group IDs use `-100` prefix format
- **Config**: All secrets via `.env` file, never hardcoded
- **Scheduling**: Cron format via APScheduler, default `0 0 * * *` (midnight UTC)

## Analysis Categories

When implementing AI prompts, include these topic categories:

- Crypto, Finance, Geopolitics

Analysis must produce: summarization, fact-checking (with confidence score), sentiment analysis, topic categorization, importance scoring.

## Docker Deployment

- SQLite database in `data/` volume
- Session files in `sessions/` volume
- First run requires local `python -m src.auth` for interactive Telegram auth before containerizing
