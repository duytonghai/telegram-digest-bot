"""Unprocessed messages must exclude stale ones."""

import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from src.database.db import Database, Message


def make_message(message_id: int, age: timedelta) -> Message:
    now = datetime.utcnow()
    return Message(None, 1, "G", message_id, "S", "text", (now - age).replace(microsecond=0), now)


class UnprocessedMessagesTest(unittest.IsolatedAsyncioTestCase):
    async def test_skips_messages_older_than_24_hours(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / "test.db")
            await db.connect()
            await db.save_message(make_message(1, timedelta(days=200)))
            await db.save_message(make_message(2, timedelta(hours=23)))
            await db.save_message(make_message(3, timedelta(hours=25)))
            messages = await db.get_unprocessed_messages()
            await db.close()
        self.assertEqual([m.message_id for m in messages], [2])

    async def test_stores_forward_source(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / "test.db")
            await db.connect()
            message = make_message(1, timedelta(hours=1))
            message.forward_from = "Channel"
            await db.save_message(message)
            messages = await db.get_unprocessed_messages()
            await db.close()
        self.assertEqual(messages[0].forward_from, "Channel")

    async def test_adds_forward_column_to_old_database(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "old.db"
            old = sqlite3.connect(path)
            old.execute(
                """CREATE TABLE messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, group_id INTEGER NOT NULL,
                    group_name TEXT NOT NULL, message_id INTEGER NOT NULL,
                    sender_name TEXT, text TEXT NOT NULL, timestamp DATETIME NOT NULL,
                    collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(group_id, message_id))"""
            )
            old.execute(
                "INSERT INTO messages (group_id, group_name, message_id, text, timestamp)"
                " VALUES (1, 'G', 1, 'text', datetime('now'))"
            )
            old.commit()
            old.close()

            db = Database(path)
            await db.connect()
            await db.connect()  # A second start must not add the column again.
            messages = await db.get_unprocessed_messages()
            await db.close()
        self.assertEqual(len(messages), 1)
        self.assertIsNone(messages[0].forward_from)


if __name__ == "__main__":
    unittest.main()
