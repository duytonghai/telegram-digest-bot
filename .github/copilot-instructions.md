# Telegram AI Digest Bot - Copilot Instructions

## Project Overview

A Telegram bot that collects messages from private groups via Telethon (user client), analyzes them using AI providers with strict objectivity guidelines, and sends separate formatted digests per group via python-telegram-bot. Uses SQLite with automatic deduplication for message storage.

## Architecture Pattern

**Dual-client architecture**: Two separate Telegram connections:

1. **User Client (Telethon)** - Reads messages from private groups as a member (with retry logic)
2. **Bot Client (python-telegram-bot)** - Sends separate formatted digest per group (with retry logic)

Data flows: Private Groups → Telethon Collector (with deduplication) → SQLite → AI Processor (analyzes each group separately) → Bot Client → Separate Digests per Group

**Key Flow**: Each group is processed independently to avoid information mixing. Each gets its own analysis and formatted digest message.

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
- Return structured data:
  - `summary` (string): 8-12 bullet points, NO WORD LIMIT, comprehensive analysis
  - `assessment` (string): 5-8 bullet points with AI's objective insights/risks/opportunities
  - `fact_check` (dict): Verifiable claims with source attribution and confidence (0-1)
  - `sentiment` (string): positive/negative/neutral/mixed
  - `topics` (list): Crypto, Finance, Geopolitics, Other
  - `importance_score` (float): 0.0-1.0
- Providers: Perplexity (primary, temp=0.2, top_p=0.9), Gemini (fallback), OpenAI (fallback)
- Registration in `ai_providers/manager.py`

**Critical: AI Objectivity Requirements**

- ONLY report information explicitly stated in messages
- DO NOT fabricate, assume, or infer information
- Use hedging language for unverified claims
- Distinguish facts from opinions clearly
- Quote numbers/prices exactly as stated

## Key Technical Decisions

- **Async throughout**: Use `asyncio` with async/await for Telethon and HTTP calls
- **Retry logic**: Exponential backoff for API calls, message collection, and digest sending
  - FloodWaitError handling for Telegram rate limits
  - 3 retries with 1s → 2s → 4s backoff
  - Separate retry mechanisms for collection, AI analysis, and sending
- **Telethon sessions**: Persist in `sessions/` directory, requires one-time interactive auth
- **Chat IDs**: All Telegram group IDs use `-100` prefix format
- **Database**: SQLite with `UNIQUE(group_id, message_id)` constraint for automatic deduplication
- **Group separation**: Each group analyzed and sent separately to avoid information mixing
- **Config**: All secrets via `.env` file, never hardcoded
- **Scheduling**: Cron format via APScheduler, default `0 0 * * *` (midnight UTC), immediate run on start for testing
- **AI parameters**: Temperature 0.2, Top-P 0.9 for factual, coherent output
- **Output formatting**: HTML with numbered lists (`<b>1.</b> Item`) for readability
- **Language preservation**: Output in same language as input (Vietnamese/English)

## Analysis Categories & Output Structure

When implementing AI prompts, include these topic categories:

- Crypto, Finance, Geopolitics, Other

Analysis must produce:

1. **Summary** (📝 PHÂN TÍCH CHI TIẾT): 8-12 numbered points, each 20-40 words, facts only from messages
2. **Assessment** (🤖 NHẬN ĐỊNH CỦA AI): 5-8 numbered points (insights/risks/opportunities), objective observations
3. **Fact-check** (✓ KIỂM TRA SỰ THẬT): Specific verifiable claims with confidence score
4. **Sentiment**: Overall tone based on message content
5. **Topics**: Categorized themes
6. **Importance Score**: 0-100% relevance

**Format Requirements**:

- Each section uses numbered lists: `<b>1.</b> Point`
- Double newline between items for readability
- Vietnamese output if input is Vietnamese
- NO paragraphs - only concise bullet points

## Docker Deployment

- SQLite database in `data/` volume (with UNIQUE constraint for deduplication)
- Session files in `sessions/` volume
- First run requires local `python -m src.auth` for interactive Telegram auth before containerizing
- Use `docker-run.sh` helper script:
  - `./docker-run.sh up` - First time build and start
  - `./docker-run.sh start` - Subsequent runs (fast, no rebuild)
  - `./docker-run.sh logs` - View live logs
  - `./docker-run.sh restart` - Restart container
  - `./docker-run.sh down` - Stop and remove
- Docker Compose v2 syntax: `docker compose` (without hyphen)
- Restart policy: `unless-stopped` for production reliability
- See `DOCKER.md` for complete deployment guide
