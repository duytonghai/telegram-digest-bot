# Telegram AI Digest Bot

A powerful Telegram bot that collects messages from private groups, analyzes them using multiple AI providers, and sends you a daily digest with summaries, fact-checking, and insights.

## Features

- 📥 **Message Collection**: Collects all messages from monitored private groups
- 🤖 **Multi-AI Analysis**: Pluggable architecture supporting Perplexity, Gemini, OpenAI, and more
- 📊 **Comprehensive Analysis**:
  - Summarization (max 500 words)
  - Fact-checking with confidence scores
  - Sentiment analysis
  - Topic categorization (Crypto, Finance, Geopolitics)
  - Importance scoring
- 📬 **Daily Digest**: Automated delivery at 0:00 UTC
- 🐳 **Docker Ready**: Fully containerized for easy deployment
- 💾 **SQLite Storage**: Lightweight message history

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRIVATE TELEGRAM GROUPS                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              USER CLIENT (Telethon)                              │
│         • Reads messages as group member                         │
│         • Collects text + links                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SQLite DATABASE                               │
│         • Message storage                                        │
│         • Analysis history                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 AI PROCESSOR (Pluggable)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  Perplexity  │  │    Gemini    │  │   OpenAI     │           │
│  │  (Primary)   │  │  (Fallback)  │  │  (Fallback)  │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              BOT CLIENT (python-telegram-bot)                    │
│         • Sends daily digest to your review group                │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Get API Credentials

#### Telegram API (for reading private groups)

1. Go to https://my.telegram.org
2. Log in with your phone number
3. Click "API development tools"
4. Create an application
5. Save your **API ID** and **API Hash**

#### Telegram Bot Token

1. Message @BotFather on Telegram
2. Send `/newbot` and follow instructions
3. Save the **Bot Token**

#### AI API Keys

- **Perplexity**: https://www.perplexity.ai/settings/api
- **Gemini** (optional): https://makersuite.google.com/app/apikey
- **OpenAI** (optional): https://platform.openai.com/api-keys

### 2. Setup Environment

```bash
# Clone and enter project
git clone <your-repo-url>
cd telegram-digest-bot

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Credentials

```bash
# Copy example config
cp .env.example .env

# Edit with your credentials
nano .env  # or use any editor
```

Required settings in `.env`:

- `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` - From my.telegram.org
- `TELEGRAM_PHONE` - Your phone number with country code
- `TELEGRAM_BOT_TOKEN` - From @BotFather
- `PERPLEXITY_API_KEY` - From Perplexity settings

### 4. Authenticate Telegram

```bash
# Make sure venv is activated
source .venv/bin/activate

# Run interactive auth (enter phone code when prompted)
python -m src.auth
```

This creates a session file in `sessions/` directory.

### 5. Get Chat IDs

```bash
# List all your Telegram chats with IDs
python -m src.utils.get_chat_ids
```

Copy the IDs and update `.env`:

- `SOURCE_GROUP_IDS` - Groups to monitor (comma-separated)
- `DIGEST_CHAT_ID` - Where to send digests

### 6. Run the Bot

#### Local Development

```bash
source .venv/bin/activate
python -m src.main
```

#### Docker (Production)

```bash
docker-compose up -d
```

> **Note:** Run steps 4-5 locally first before Docker deployment. The session files will be mounted from `sessions/` volume.

## Configuration

Edit `.env` file:

```env
# Telegram User Client (for reading messages)
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=+84xxxxxxxxx

# Telegram Bot (for sending digests)
TELEGRAM_BOT_TOKEN=your_bot_token
DIGEST_CHAT_ID=-100xxxxxxxxxx

# Source Groups to Monitor (comma-separated)
SOURCE_GROUP_IDS=-100xxxxxxxxxx

# AI Providers
PERPLEXITY_API_KEY=your_key
GEMINI_API_KEY=optional
OPENAI_API_KEY=optional

# Primary AI Provider (perplexity, gemini, openai)
PRIMARY_AI_PROVIDER=perplexity

# Schedule (cron format)
DIGEST_SCHEDULE=0 0 * * *
```

## Getting Chat IDs

1. Add your bot to the destination group
2. Run: `python -m src.utils.get_chat_ids`
3. Or forward a message from the group to @userinfobot

## Project Structure

```
telegram-digest-bot/
├── src/
│   ├── __init__.py
│   ├── main.py                 # Entry point
│   ├── auth.py                 # Telegram authentication
│   ├── config.py               # Configuration management
│   ├── collector/
│   │   ├── __init__.py
│   │   └── message_collector.py
│   ├── database/
│   │   ├── __init__.py
│   │   └── db.py
│   ├── ai_providers/
│   │   ├── __init__.py
│   │   ├── base.py             # Abstract base class
│   │   ├── perplexity.py
│   │   ├── gemini.py
│   │   ├── openai_provider.py
│   │   └── manager.py          # AI provider manager
│   ├── analyzer/
│   │   ├── __init__.py
│   │   └── message_analyzer.py
│   ├── digest/
│   │   ├── __init__.py
│   │   └── digest_sender.py
│   └── scheduler/
│       ├── __init__.py
│       └── job_scheduler.py
├── data/                       # SQLite database
├── sessions/                   # Telegram session files
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## Adding New AI Providers

1. Create a new file in `src/ai_providers/`
2. Extend `BaseAIProvider` class
3. Implement required methods
4. Register in `src/ai_providers/manager.py`

Example:

```python
from .base import BaseAIProvider, AnalysisResult

class MyCustomProvider(BaseAIProvider):
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.name = "custom"

    async def analyze(self, messages: list[str], context: dict) -> AnalysisResult:
        # Your implementation
        pass
```

## License

MIT License
