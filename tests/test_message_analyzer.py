"""Analyzer must give the AI stable ids and check what comes back."""

import unittest
from datetime import datetime
from types import SimpleNamespace

from src.ai_providers.base import AnalysisResult, SummaryItem
from src.analyzer import message_analyzer
from src.analyzer.message_analyzer import MessageAnalyzer
from src.collector.message_collector import _forward_source
from src.database.db import Message


def message(message_id: int, forward_from: str | None = None, sender: str = "Real Name") -> Message:
    now = datetime(2026, 11, 7, 3, 0)
    return Message(None, 1, "G", message_id, sender, f"text {message_id}", now, now, forward_from)


class FakeManager:
    def __init__(self):
        self.batches = []

    async def analyze(self, records, context):
        self.batches.append(records)
        return AnalysisResult(
            summary=[SummaryItem("reported", f"item {records[0]['id']}", [records[0]["id"], 9999])],
            assessment=[], fact_check=[], sentiment="neutral", topics=["Other"],
            importance_score=0.5,
        )


class AnalyzerTest(unittest.IsolatedAsyncioTestCase):
    async def test_records_carry_sender_time_and_forward(self):
        manager = FakeManager()
        await MessageAnalyzer(None, manager).analyze_single_group([message(1, "Channel"), message(2)])
        first, second = manager.batches[0]
        self.assertEqual(first, {
            "id": 1, "sender": "member_1", "time": "2026-11-07 03:00",
            "text": "text 1", "forwarded_from": "Channel",
        })
        self.assertNotIn("forwarded_from", second)

    async def test_member_names_never_reach_the_ai(self):
        manager = FakeManager()
        await MessageAnalyzer(None, manager).analyze_single_group([
            message(1, sender="Real Name"),
            message(2, sender="Other Name"),
            message(3, sender="Real Name"),
            message(4, "private:12345", sender="Other Name"),
            message(5, "Public Channel", sender="Other Name"),
        ])
        batch = manager.batches[0]
        self.assertEqual(
            [r["sender"] for r in batch],
            ["member_1", "member_2", "member_1", "member_2", "member_2"],
        )
        self.assertEqual(batch[3]["forwarded_from"], "member_3")
        self.assertEqual(batch[4]["forwarded_from"], "Public Channel")
        self.assertNotIn("Real Name", str(batch))
        self.assertNotIn("12345", str(batch))

    async def test_ids_continue_across_chunks_and_results_are_checked(self):
        manager = FakeManager()
        original = message_analyzer.MAX_MESSAGES_PER_CHUNK
        message_analyzer.MAX_MESSAGES_PER_CHUNK = 2
        self.addCleanup(setattr, message_analyzer, "MAX_MESSAGES_PER_CHUNK", original)

        merged = await MessageAnalyzer(None, manager).analyze_single_group(
            [message(i) for i in range(1, 5)]
        )
        self.assertEqual([[r["id"] for r in b] for b in manager.batches], [[1, 2], [3, 4]])
        self.assertEqual([i.sources for i in merged.summary], [["1"], ["3"]])


class ForwardSourceTest(unittest.TestCase):
    def source(self, **fields):
        values = dict(chat=None, chat_id=None, sender_id=None, from_name=None)
        return _forward_source(SimpleNamespace(forward=SimpleNamespace(**{**values, **fields})))

    def test_not_forwarded(self):
        self.assertIsNone(_forward_source(SimpleNamespace(forward=None)))

    def test_channel_keeps_its_title(self):
        chat = SimpleNamespace(title="Public Channel")
        self.assertEqual(self.source(chat=chat, chat_id=-100), "Public Channel")

    def test_people_are_marked_private(self):
        person = SimpleNamespace(first_name="Real Name")
        self.assertEqual(self.source(sender=person, sender_id=7), "private:7")
        self.assertEqual(self.source(from_name="Hidden Name"), "private:Hidden Name")


if __name__ == "__main__":
    unittest.main()
