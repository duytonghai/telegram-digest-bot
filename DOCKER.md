# Docker Deployment Guide

## 📋 Overview

This guide shows how to run the Telegram Digest Bot using Docker Compose.

## 🚀 Quick Start

### Prerequisites

1. **Docker & Docker Compose** installed
2. **Telegram session authenticated** (run locally first):
   ```bash
   source .venv/bin/activate
   python -m src.auth
   # Complete phone authentication
   ```
3. **`.env` file** configured with credentials
4. **`sessions/telegram_user.session`** file exists

### First Time Setup

```bash
# Make the script executable (one time only)
chmod +x docker-run.sh

# Build and start (1st time)
./docker-run.sh up
```

This will:

- Build the Docker image (~30 seconds)
- Create container `telegram-digest-bot`
- Mount volumes for `data/` and `sessions/`
- Start the bot in background
- Schedule daily digest at midnight UTC

### Subsequent Runs (2nd time onwards)

**⭐ Recommended command to avoid recreating containers:**

```bash
./docker-run.sh start
```

This will:

- Start existing container (no rebuild)
- Much faster (< 1 second)
- Preserves container state

## 📋 Common Commands

### View Live Logs

```bash
./docker-run.sh logs
# or
docker compose logs -f telegram-digest-bot
```

### Stop Bot (preserve container)

```bash
./docker-run.sh stop
```

### Restart Bot

```bash
./docker-run.sh restart
```

### Check Status

```bash
./docker-run.sh status
# or
docker compose ps
```

### Stop and Remove Container

```bash
./docker-run.sh down
```

⚠️ **Note**: This removes containers but preserves data in `data/` and `sessions/` volumes

### Rebuild from Scratch

```bash
./docker-run.sh rebuild
```

## 📁 Volume Mappings

| Host Path     | Container Path   | Purpose                       |
| ------------- | ---------------- | ----------------------------- |
| `./data/`     | `/app/data/`     | SQLite database (messages.db) |
| `./sessions/` | `/app/sessions/` | Telegram session files        |

## 🔄 Workflow Summary

```bash
# 1st time: Build + Start
./docker-run.sh up

# View logs
./docker-run.sh logs

# Stop for changes
./docker-run.sh stop

# 2nd+ times: Just start (fast)
./docker-run.sh start

# When code changes
./docker-run.sh rebuild
```

## ⏰ Scheduling

By default, bot runs digest at:

- **Cron**: `0 0 * * *` (midnight UTC)
- **Immediate run**: On container start (for testing)

To change schedule, edit `.env`:

```env
DIGEST_SCHEDULE=0 9 * * *  # 9 AM UTC daily
```

## 🐛 Troubleshooting

### Issue: "No messages to analyze"

**Cause**: Database has old messages outside the 24h window.

**Solution**: Clear database and restart:

```bash
./docker-run.sh stop
rm -f data/messages.db
./docker-run.sh start
```

### Issue: Container exits immediately

**Cause**: Missing session file or .env credentials.

**Solution**: Check logs and ensure:

```bash
# 1. Session exists
ls sessions/telegram_user.session

# 2. .env has valid credentials
cat .env | grep -E "API_ID|API_HASH|BOT_TOKEN"

# 3. View error logs
docker compose logs telegram-digest-bot
```

### Issue: "docker-compose: command not found"

**Cause**: Using Docker Compose v2 (installed via Docker Desktop).

**Solution**: Script already updated to use `docker compose` (without hyphen).

## 🔐 Security Notes

- `.env` file is excluded from Docker image (via `.dockerignore`)
- Credentials passed as environment variables at runtime
- Session files stored in mounted volume (not in image)
- Database stored in mounted volume (persistent)

## 📊 Monitoring

### Check if bot is running

```bash
docker compose ps
```

Expected output:

```
NAME                 COMMAND              SERVICE    STATUS    PORTS
telegram-digest-bot  "python -m src.main" telegram-digest-bot running
```

### Real-time logs

```bash
docker compose logs -f telegram-digest-bot
```

### Check database

```bash
docker compose exec telegram-digest-bot sqlite3 /app/data/messages.db "SELECT COUNT(*) FROM messages;"
```

## 🚀 Production Deployment

For production servers:

1. **Set timezone**:

   ```yaml
   # docker-compose.yml
   environment:
     - TZ=Asia/Ho_Chi_Minh # Your timezone
   ```

2. **Auto-restart on crash**:

   ```yaml
   restart: unless-stopped # Already configured
   ```

3. **Resource limits** (optional):

   ```yaml
   deploy:
     resources:
       limits:
         memory: 512M
         cpus: "0.5"
   ```

4. **Start on system boot**:
   ```bash
   # Add to crontab
   @reboot cd /path/to/telegram-digest-bot && ./docker-run.sh start
   ```

## 🔄 Update Workflow

When you update code:

```bash
# Pull changes
git pull

# Rebuild and restart
./docker-run.sh rebuild

# Verify
./docker-run.sh logs
```

## 📞 Support Commands

```bash
# Help
./docker-run.sh

# Full command reference
./docker-run.sh help
```
