"""SQLite database operations using aiosqlite."""

import aiosqlite
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass


DATABASE_PATH = Path("data/messages.db")


# Marks a forward origin that is not a named channel, such as a person.
# The analyzer replaces these values with an alias before calling the AI.
PRIVATE_FORWARD_PREFIX = "private:"


@dataclass
class Message:
    """Stored message from a Telegram group."""
    id: int | None
    group_id: int
    group_name: str
    message_id: int
    sender_name: str
    text: str
    timestamp: datetime
    collected_at: datetime
    forward_from: str | None = None


def _row_to_message(row) -> Message:
    """Convert a messages row into a Message."""
    return Message(
        id=row[0],
        group_id=row[1],
        group_name=row[2],
        message_id=row[3],
        sender_name=row[4],
        text=row[5],
        timestamp=datetime.fromisoformat(row[6]),
        collected_at=datetime.fromisoformat(row[7]),
        forward_from=row[8],
    )


class Database:
    """Async SQLite database handler."""

    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = db_path
        self._connection: aiosqlite.Connection | None = None

    async def connect(self):
        """Initialize database connection and create tables."""
        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._connection = await aiosqlite.connect(self.db_path)
        await self._create_tables()

    async def close(self):
        """Close database connection."""
        if self._connection:
            await self._connection.close()

    async def _create_tables(self):
        """Create database tables if they don't exist."""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                group_name TEXT NOT NULL,
                message_id INTEGER NOT NULL,
                sender_name TEXT,
                text TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                forward_from TEXT,
                UNIQUE(group_id, message_id)
            )
        """)

        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS digests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                message_count INTEGER,
                summary TEXT,
                sent_at DATETIME
            )
        """)

        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_timestamp
            ON messages(timestamp)
        """)

        # Databases made before forward tracking lack this column.
        cursor = await self._connection.execute("PRAGMA table_info(messages)")
        columns = [row[1] for row in await cursor.fetchall()]
        if "forward_from" not in columns:
            await self._connection.execute(
                "ALTER TABLE messages ADD COLUMN forward_from TEXT"
            )

        await self._connection.commit()

    async def save_message(self, message: Message) -> int:
        """Save a message to the database.

        Returns:
            The ID of the inserted message.
        """
        cursor = await self._connection.execute(
            """
            INSERT OR IGNORE INTO messages
            (group_id, group_name, message_id, sender_name, text, timestamp, forward_from)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message.group_id,
                message.group_name,
                message.message_id,
                message.sender_name,
                message.text,
                message.timestamp,
                message.forward_from,
            ),
        )
        await self._connection.commit()
        return cursor.lastrowid

    async def get_messages_since(
        self, since: datetime, group_id: int | None = None
    ) -> list[Message]:
        """Get messages since a given timestamp.

        Args:
            since: Get messages after this time.
            group_id: Optional filter by group.

        Returns:
            List of Message objects.
        """
        if group_id:
            cursor = await self._connection.execute(
                """
                SELECT id, group_id, group_name, message_id, sender_name,
                       text, timestamp, collected_at, forward_from
                FROM messages
                WHERE timestamp >= ? AND group_id = ?
                ORDER BY timestamp ASC
                """,
                (since, group_id),
            )
        else:
            cursor = await self._connection.execute(
                """
                SELECT id, group_id, group_name, message_id, sender_name,
                       text, timestamp, collected_at, forward_from
                FROM messages
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
                """,
                (since,),
            )

        rows = await cursor.fetchall()
        return [_row_to_message(row) for row in rows]

    async def get_unprocessed_messages(self) -> list[Message]:
        """Get undigested messages from the last 24 hours. Older ones are stale."""
        cursor = await self._connection.execute(
            """
            SELECT id, group_id, group_name, message_id, sender_name,
                   text, timestamp, collected_at, forward_from
            FROM messages
            WHERE collected_at > (
                SELECT COALESCE(MAX(created_at), '1970-01-01') FROM digests
            )
            AND timestamp >= datetime('now', '-1 day')
            ORDER BY timestamp ASC
            """
        )

        rows = await cursor.fetchall()
        return [_row_to_message(row) for row in rows]

    async def record_digest(self, message_count: int, summary: str):
        """Record that a digest was created."""
        await self._connection.execute(
            """
            INSERT INTO digests (message_count, summary, sent_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
            (message_count, summary),
        )
        await self._connection.commit()


# Convenience function for context manager pattern
async def get_database() -> Database:
    """Get a connected database instance."""
    db = Database()
    await db.connect()
    return db
