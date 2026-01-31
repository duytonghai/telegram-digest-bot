"""Digest sender - formats and sends digests via python-telegram-bot."""

import asyncio
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import RetryAfter, TimedOut, NetworkError

from ..config import config
from ..ai_providers.base import AnalysisResult


class DigestSender:
    """Sends formatted digests to the destination Telegram group."""

    def __init__(self):
        self.bot = Bot(token=config.telegram.bot_token)
        self.chat_id = config.telegram.digest_chat_id

    async def send_digest(self, result: AnalysisResult, message_count: int, group_name: str = None):
        """Format and send the digest with retry logic.

        Args:
            result: Analysis result from AI provider.
            message_count: Number of messages analyzed.
            group_name: Name of the source group (optional).
        """
        # Format the digest message
        digest_text = self._format_digest(result, message_count, group_name)

        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                # Split if too long (Telegram limit is 4096 chars)
                if len(digest_text) > 4000:
                    chunks = self._split_message(digest_text)
                    for chunk in chunks:
                        await self._send_with_retry(chunk)
                else:
                    await self._send_with_retry(digest_text)

                return  # Success

            except RetryAfter as e:
                wait_time = e.retry_after
                print(f"⚠️ Telegram rate limit: waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
            except (TimedOut, NetworkError) as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"⚠️ Network error: {e}")
                    print(f"   Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"❌ Failed to send digest after {max_retries} attempts")
                    raise
            except Exception as e:
                print(f"⚠️ Error sending digest: {e}")
                print(f"💡 Tip: Start a conversation with your bot first by sending /start")
                raise

    async def _send_with_retry(self, text: str, max_retries: int = 2):
        """Send a single message with retry logic.

        Args:
            text: Message text to send.
            max_retries: Maximum retry attempts.
        """
        for attempt in range(max_retries):
            try:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=text,
                    parse_mode=ParseMode.HTML,
                    read_timeout=60,
                    write_timeout=60,
                    connect_timeout=30,
                )
                return  # Success
            except (TimedOut, NetworkError) as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ Send retry {attempt + 1}/{max_retries}: {e}")
                    await asyncio.sleep(2)
                else:
                    raise

    def _format_digest(self, result: AnalysisResult, message_count: int, group_name: str = None) -> str:
        """Format the analysis result into a readable digest."""
        # Importance indicator
        importance_emoji = self._get_importance_emoji(result.importance_score)

        # Sentiment indicator
        sentiment_emoji = {
            "positive": "🟢",
            "negative": "🔴",
            "neutral": "⚪",
            "mixed": "🟡",
        }.get(result.sentiment, "⚪")

        # Topics with emojis
        topic_emojis = {
            "Crypto": "₿",
            "Finance": "💰",
            "Geopolitics": "🌍",
            "Other": "📌"
        }
        topics_formatted = " | ".join(
            f"{topic_emojis.get(t, '📌')} {t}" for t in (result.topics or ["Other"])
        )

        # Group header
        group_header = f"\n📂 <b>Nhóm:</b> {group_name}" if group_name else ""

        # Build digest with improved formatting
        digest = f"""━━━━━━━━━━━━━━━━━━━━━
📰 <b>BÁO CÁO HÀNG NGÀY</b>
━━━━━━━━━━━━━━━━━━━━━{group_header}

<b>📊 Thông tin tổng quan:</b>
  📨 Số tin: <code>{message_count}</code>
  {importance_emoji} Độ quan trọng: <b>{result.importance_score:.0%}</b>
  {sentiment_emoji} Tâm lý: <b>{result.sentiment.title()}</b>
  🏷️ Chủ đề: {topics_formatted}

━━━━━━━━━━━━━━━━━━━━━
<b>📝 PHÂN TÍCH CHI TIẾT</b>
━━━━━━━━━━━━━━━━━━━━━

{self._format_summary_items(result.summary)}

━━━━━━━━━━━━━━━━━━━━━
<b>🤖 NHẬN ĐỊNH CỦA AI</b>
━━━━━━━━━━━━━━━━━━━━━

{self._format_assessment_items(result.assessment)}
"""

        # Add fact-check section if there are claims
        if result.fact_check:
            digest += "\n━━━━━━━━━━━━━━━━━━━━━\n"
            digest += "<b>✓ KIỂM TRA SỰ THẬT</b>\n"
            digest += "━━━━━━━━━━━━━━━━━━━━━\n\n"

            avg_confidence = 0.0
            for i, item in enumerate(result.fact_check[:10], 1):
                status_emoji = {
                    "corroborated_in_chat": "✅",
                    "conflicting_in_chat": "⚠️",
                    "single_source": "📝",
                    "not_checkable": "❓",
                }.get(item.status, "📝")
                digest += f"<b>{i}.</b> {status_emoji} {item.claim}\n"
                if item.sources:
                    digest += f"    <i>Nguồn: [{', '.join(item.sources)}]</i>\n"
                digest += "\n"
                avg_confidence += item.confidence

            if result.fact_check:
                avg_confidence /= len(result.fact_check)
                confidence_emoji = "✅" if avg_confidence >= 0.7 else "⚠️" if avg_confidence >= 0.4 else "❌"
                digest += f"{confidence_emoji} <i>Độ tin cậy trung bình: {avg_confidence:.0%}</i>\n"

        # Add unknowns section if present
        if result.unknowns:
            digest += "\n━━━━━━━━━━━━━━━━━━━━━\n"
            digest += "<b>❓ THÔNG TIN CHƯA RÕ</b>\n"
            digest += "━━━━━━━━━━━━━━━━━━━━━\n\n"
            for unknown in result.unknowns[:5]:
                digest += f"• {unknown}\n"

        digest += "\n━━━━━━━━━━━━━━━━━━━━━"

        return digest

    def _format_summary_items(self, items: list) -> str:
        """Format summary items as numbered list with type indicators."""
        if not items:
            return "<i>Không có dữ liệu</i>"

        formatted = []
        type_emoji = {
            "fact": "📌",
            "opinion": "💭",
            "rumor": "🔮",
        }

        for i, item in enumerate(items, 1):
            emoji = type_emoji.get(item.type, "📌")
            text = f"<b>{i}.</b> {emoji} {item.text}"
            if item.sources:
                text += f" <i>[{', '.join(item.sources)}]</i>"
            formatted.append(text)

        return "\n\n".join(formatted)

    def _format_assessment_items(self, items: list) -> str:
        """Format assessment items as numbered list with labels."""
        if not items:
            return "<i>Không có nhận định</i>"

        formatted = []
        label_emoji = {
            "Nhận xét": "💡",
            "Commentary": "💡",
            "Dấu hiệu rủi ro": "⚠️",
            "Risk signal": "⚠️",
            "Cơ hội tiềm năng": "🎯",
            "Potential opportunity": "🎯",
        }

        for i, item in enumerate(items, 1):
            emoji = label_emoji.get(item.label, "💡")
            text = f"<b>{i}.</b> {emoji} <b>{item.label}:</b> {item.text}"
            if item.evidence_sources:
                text += f" <i>[{', '.join(item.evidence_sources)}]</i>"
            formatted.append(text)

        return "\n\n".join(formatted)

    def _format_bullet_points(self, text: str) -> str:
        """Format text as numbered list (legacy fallback)."""
        if not text:
            return ""

        # Split thành các dòng và lọc bỏ dòng trống
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        # Filter và clean các dòng có nội dung thực
        items = []
        for line in lines:
            # Bỏ qua các header hoặc section markers
            if line.startswith(("**", "##", "Summary:", "Assessment:", "---")):
                continue

            # Remove existing markers (bullets, dashes, numbers)
            cleaned = line
            # Remove leading bullets, dashes, asterisks
            cleaned = cleaned.lstrip("•*-").strip()
            # Remove existing numbers like "1.", "2.", etc.
            import re
            cleaned = re.sub(r'^\d+\.\s*', '', cleaned)

            # Skip quá ngắn (likely headers)
            if len(cleaned) < 10:
                continue

            # Remove bold tags nếu có để check
            cleaned_check = cleaned.replace("<b>", "").replace("</b>", "")
            if cleaned_check and len(cleaned_check) > 10:
                items.append(cleaned)

        # Nếu chỉ có 1-2 items nhưng rất dài (>300 chars), tự động split
        if len(items) <= 2 and any(len(item) > 300 for item in items):
            new_items = []
            for item in items:
                if len(item) > 300:
                    # Split by semicolons first (common separator in Vietnamese)
                    parts = [p.strip() for p in item.split(';') if p.strip()]

                    # Nếu vẫn quá dài, split by specific patterns
                    final_parts = []
                    for part in parts:
                        if len(part) > 200:
                            # Try splitting by common Vietnamese patterns
                            # Pattern 1: "... (details); ... (details)"
                            sub_parts = re.split(r'\)\s*;\s*', part)
                            for i, sub in enumerate(sub_parts):
                                sub = sub.strip()
                                if sub and not sub.endswith(')'):
                                    sub += ')'
                                if len(sub) > 30:
                                    final_parts.append(sub)
                        elif len(part) > 30:
                            final_parts.append(part)

                    new_items.extend(final_parts if final_parts else [item])
                else:
                    new_items.append(item)

            items = new_items

        # Format thành numbered list giống kiểm tra sự thật
        formatted_items = []
        for i, item in enumerate(items, 1):
            # Format: <b>1.</b> Content\n\n (giống fact-check)
            formatted_items.append(f"<b>{i}.</b> {item}")

        # Join với double newline giữa các items (giống fact-check section)
        return "\n\n".join(formatted_items)
    def _get_importance_emoji(self, score: float) -> str:
        """Get emoji based on importance score."""
        if score >= 0.8:
            return "🔥"
        elif score >= 0.6:
            return "⚡"
        elif score >= 0.4:
            return "📌"
        else:
            return "📎"

    def _split_message(self, text: str, max_length: int = 4000) -> list[str]:
        """Split a long message into chunks."""
        chunks = []
        while text:
            if len(text) <= max_length:
                chunks.append(text)
                break

            # Find a good split point
            split_point = text.rfind("\n", 0, max_length)
            if split_point == -1:
                split_point = max_length

            chunks.append(text[:split_point])
            text = text[split_point:].lstrip()

        return chunks
