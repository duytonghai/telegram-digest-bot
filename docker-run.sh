#!/bin/bash

# Docker run script for Telegram Digest Bot

echo "🐳 Telegram Digest Bot - Docker Runner"
echo "======================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create .env file with required credentials."
    exit 1
fi

# Check if sessions directory exists
if [ ! -d sessions ]; then
    echo "⚠️  Warning: sessions/ directory not found. Creating..."
    mkdir -p sessions
fi

# Check if telegram session file exists
if [ ! -f sessions/telegram_user.session ]; then
    echo "⚠️  Warning: No Telegram session found!"
    echo "You need to authenticate first:"
    echo "  1. Run: source .venv/bin/activate"
    echo "  2. Run: python -m src.auth"
    echo "  3. Complete authentication"
    echo "  4. Then run this script again"
    exit 1
fi

# Check if data directory exists
if [ ! -d data ]; then
    echo "📁 Creating data/ directory..."
    mkdir -p data
fi

# Parse command
COMMAND=${1:-up}

case $COMMAND in
    up|start)
        echo "🚀 Starting Telegram Digest Bot..."
        echo ""
        if [ "$COMMAND" = "up" ]; then
            # First time or rebuild
            echo "Building and starting containers..."
            docker compose up -d --build
        else
            # Just start existing containers
            echo "Starting existing containers..."
            docker compose start
        fi
        echo ""
        echo "✅ Bot is running in the background!"
        echo ""
        echo "📋 Useful commands:"
        echo "  - View logs:    docker compose logs -f"
        echo "  - Stop bot:     docker compose stop"
        echo "  - Restart:      docker compose restart"
        echo "  - Stop & remove: docker compose down"
        ;;

    stop)
        echo "🛑 Stopping Telegram Digest Bot..."
        docker compose stop
        echo "✅ Bot stopped (containers preserved)"
        ;;

    restart)
        echo "🔄 Restarting Telegram Digest Bot..."
        docker compose restart
        echo "✅ Bot restarted"
        ;;

    logs)
        echo "📋 Showing bot logs (Ctrl+C to exit)..."
        docker compose logs -f
        ;;

    down)
        echo "⚠️  Stopping and removing containers..."
        docker compose down
        echo "✅ Containers removed (data and sessions preserved in volumes)"
        ;;

    rebuild)
        echo "🔨 Rebuilding and restarting..."
        docker compose down
        docker compose up -d --build
        echo "✅ Rebuild complete!"
        ;;

    status)
        echo "📊 Container status:"
        docker compose ps
        ;;

    *)
        echo "Usage: ./docker-run.sh [command]"
        echo ""
        echo "Commands:"
        echo "  up       - Build and start (first time)"
        echo "  start    - Start existing containers (2nd time onwards) ⭐"
        echo "  stop     - Stop containers (preserves state)"
        echo "  restart  - Restart containers"
        echo "  logs     - View live logs"
        echo "  down     - Stop and remove containers"
        echo "  rebuild  - Rebuild from scratch"
        echo "  status   - Show container status"
        echo ""
        echo "💡 Recommended workflow:"
        echo "  1st run:  ./docker-run.sh up"
        echo "  2nd+ run: ./docker-run.sh start"
        ;;
esac
