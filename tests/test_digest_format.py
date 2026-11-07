"""Digest HTML must stay valid when AI text has special characters."""

import unittest
from html.parser import HTMLParser

from src.ai_providers.base import (
    AnalysisResult,
    AssessmentItem,
    FactCheckItem,
    SummaryItem,
)
from src.digest.digest_sender import DigestSender

NASTY = 'P&L < $100 > <script> </b> "AT&T"'
ALLOWED_TAGS = {"b", "i", "code"}


class TagChecker(HTMLParser):
    """Records tags that are not allowed or not balanced."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []
        self.text = ""

    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED_TAGS:
            self.errors.append(f"bad tag <{tag}>")
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack.pop() != tag:
            self.errors.append(f"unbalanced </{tag}>")

    def handle_data(self, data):
        self.text += data


def check(html: str) -> TagChecker:
    checker = TagChecker()
    checker.feed(html)
    checker.close()
    return checker


def make_result(text: str, sources: list) -> AnalysisResult:
    return AnalysisResult(
        summary=[SummaryItem("reported", text, sources)],
        assessment=[AssessmentItem(text, text, sources)],
        fact_check=[FactCheckItem(text, sources, "single_source", 0.4)],
        sentiment=text,
        topics=[text],
        importance_score=0.5,
        unknowns=[text],
    )


class DigestFormatTest(unittest.TestCase):
    def setUp(self):
        self.sender = DigestSender.__new__(DigestSender)

    def test_special_characters_are_escaped_everywhere(self):
        html = self.sender._format_digest(make_result(NASTY, [NASTY]), 3, NASTY)
        checker = check(html)
        self.assertEqual(checker.errors, [])
        self.assertEqual(checker.stack, [])
        self.assertIn("P&L < $100", checker.text)

    def test_integer_sources_do_not_crash(self):
        html = self.sender._format_digest(make_result("ok text", [1, 2]), 3, "Group")
        self.assertIn("1, 2", html)

    def test_long_digest_splits_into_valid_chunks(self):
        items = [SummaryItem("reported", f"{NASTY} {i} " + "x" * 300) for i in range(40)]
        result = make_result("ok", [])
        result.summary = items
        chunks = self.sender._split_message(self.sender._format_digest(result, 3, "G"))
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 4096)
            checker = check(chunk)
            self.assertEqual(checker.errors, [])
            self.assertEqual(checker.stack, [])


if __name__ == "__main__":
    unittest.main()
