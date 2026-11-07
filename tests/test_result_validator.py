"""AI output must be checked against the messages it came from."""

import unittest

from src.ai_providers.base import (
    AnalysisResult,
    AssessmentItem,
    BaseAIProvider,
    FactCheckItem,
    SummaryItem,
)
from src.analyzer.result_validator import has_signal, sanitize_result


def records(*senders: str, forwarded: str | None = None) -> list[dict]:
    rows = []
    for i, sender in enumerate(senders, 1):
        row = {"id": i, "sender": sender, "time": "t", "text": "x"}
        if forwarded:
            row["forwarded_from"] = forwarded
        rows.append(row)
    return rows


def result(**kwargs) -> AnalysisResult:
    values = dict(summary=[], assessment=[], fact_check=[], sentiment="neutral",
                  topics=["Finance"], importance_score=0.5)
    return AnalysisResult(**{**values, **kwargs})


def fact(sources: list, status: str = "corroborated_in_chat", confidence: float = 0.9):
    return FactCheckItem("claim", sources, status, confidence)


class CitationTest(unittest.TestCase):
    def test_drops_invalid_citations_and_items_left_without_one(self):
        checked = sanitize_result(result(
            summary=[SummaryItem("reported", "a", ["1", "99"]), SummaryItem("reported", "b", ["99"])],
            assessment=[AssessmentItem("Nhận xét", "c", ["abc"])],
            fact_check=[fact([])],
        ), records("A", "B"))
        self.assertEqual([i.text for i in checked.summary], ["a"])
        self.assertEqual(checked.summary[0].sources, ["1"])
        self.assertEqual(checked.assessment, [])
        self.assertEqual(checked.fact_check, [])

    def test_accepts_integer_and_bracket_citations(self):
        checked = sanitize_result(
            result(summary=[SummaryItem("reported", "a", [1, "[2]", 1])]), records("A", "B")
        )
        self.assertEqual(checked.summary[0].sources, ["1", "2"])


class CorroborationTest(unittest.TestCase):
    def check(self, item, rows):
        return sanitize_result(result(fact_check=[item]), rows).fact_check[0]

    def test_different_senders_keep_corroboration(self):
        item = self.check(fact(["1", "2"]), records("A", "B", "C"))
        self.assertEqual((item.status, item.confidence), ("corroborated_in_chat", 0.9))

    def test_one_message_cannot_corroborate(self):
        item = self.check(fact(["1"]), records("A", "B", "C"))
        self.assertEqual((item.status, item.confidence), ("single_source", 0.4))

    def test_same_sender_cannot_corroborate(self):
        item = self.check(fact(["1", "2"]), records("A", "A", "B"))
        self.assertEqual((item.status, item.confidence), ("single_source", 0.6))

    def test_same_forward_origin_cannot_corroborate(self):
        item = self.check(fact(["1", "2"]), records("A", "B", "C", forwarded="Channel"))
        self.assertEqual((item.status, item.confidence), ("single_source", 0.6))


class EnumAndLimitTest(unittest.TestCase):
    def test_bad_values_fall_back_to_safe_ones(self):
        checked = sanitize_result(result(
            summary=[SummaryItem("fact", "a", ["1"]), SummaryItem("breaking", "b", ["1"])],
            fact_check=[fact(["1"], "confirmed", 7.0)],
            sentiment="bullish", topics=["Weather"], importance_score=5.0, language="fr",
        ), records("A", "B", "C"))
        self.assertEqual([i.type for i in checked.summary], ["reported", "opinion"])
        self.assertEqual(checked.fact_check[0].status, "not_checkable")
        self.assertEqual(checked.fact_check[0].confidence, 0.4)
        self.assertEqual((checked.sentiment, checked.topics), ("neutral", ["Other"]))
        self.assertEqual((checked.importance_score, checked.language), (1.0, "mixed"))

    def test_caps_items_to_batch_size(self):
        items = [SummaryItem("reported", str(i), ["1"]) for i in range(20)]
        checked = sanitize_result(
            result(summary=items, unknowns=list("abcdef")), records("A", "B", "C")
        )
        self.assertEqual(len(checked.summary), 3)
        self.assertEqual(len(checked.unknowns), 3)


class HasSignalTest(unittest.TestCase):
    def test_needs_items_and_importance(self):
        item = SummaryItem("reported", "a", ["1"])
        self.assertTrue(has_signal(result(summary=[item], importance_score=0.2)))
        self.assertFalse(has_signal(result(summary=[item], importance_score=0.1)))
        self.assertFalse(has_signal(result(summary=[], importance_score=0.9)))


class StubProvider(BaseAIProvider):
    async def analyze(self, messages, context):
        raise NotImplementedError


class MalformedOutputTest(unittest.TestCase):
    def test_wrong_json_types_do_not_crash_the_check(self):
        checked = sanitize_result(result(
            summary=[SummaryItem(["x"], "a", ["1"]), SummaryItem("reported", None, ["1"])],
            fact_check=[FactCheckItem(None, ["1"])],
            sentiment=["bad"], topics=[{"a": 1}, "Finance"], language=None,
        ), records("A"))
        self.assertEqual([i.type for i in checked.summary], ["opinion"])
        self.assertEqual(checked.fact_check, [])
        self.assertEqual((checked.sentiment, checked.topics), ("neutral", ["Finance"]))

    def test_text_confidence_does_not_crash_parsing(self):
        provider = StubProvider("key")
        parsed = {
            "fact_check": [{"claim": "c", "sources": ["1"], "confidence": "high"}],
            "importance_score": None,
        }
        built = provider._build_result(parsed, "")
        self.assertEqual(built.fact_check[0].confidence, 0.0)
        self.assertEqual(built.importance_score, 0.5)


if __name__ == "__main__":
    unittest.main()
