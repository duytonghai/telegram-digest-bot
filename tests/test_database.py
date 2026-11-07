"""Unprocessed messages must exclude stale ones."""

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


if __name__ == "__main__":
    unittest.main()
