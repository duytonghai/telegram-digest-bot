"""DeepSeek AI provider (OpenAI-compatible API)."""

import asyncio
import json

from openai import AsyncOpenAI

from .base import BaseAIProvider, AnalysisResult
from ..prompts import get_analysis_user_prompt, get_ai_parameters, get_api_config


class DeepSeekProvider(BaseAIProvider):
    """DeepSeek provider for message analysis."""

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.name = "deepseek"

    async def analyze(
        self, messages: list[str], context: dict
    ) -> AnalysisResult:
        """Analyze messages using the DeepSeek chat completions API."""
        user_prompt = get_analysis_user_prompt(
            messages=messages,
            group_name=context.get('group_name', 'Unknown'),
            date_range=context.get('date_range', 'Today'),
        )
        system_prompt = self.get_system_prompt(context.get('topic_types', ['general']))

        api_config = get_api_config('deepseek')
        ai_params = get_ai_parameters(
            'factual', {"max_tokens": api_config['max_tokens']}
        )
        max_retries = api_config['max_retries']
        retry_delay = api_config['retry_delay']

        # The SDK retries 429, 5xx, and connection errors by itself.
        async with AsyncOpenAI(
            api_key=self.api_key,
            base_url=api_config['base_url'],
            timeout=api_config['timeout'],
            max_retries=max_retries,
        ) as client:
            for attempt in range(max_retries):
                response = await client.chat.completions.create(
                    model=api_config['model'],
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    # Thinking mode ignores temperature, so turn it off.
                    extra_body={"thinking": {"type": "disabled"}},
                    **ai_params,
                )

                choice = response.choices[0]
                if choice.finish_reason == "length":
                    raise RuntimeError(
                        f"DeepSeek output cut off at max_tokens={ai_params['max_tokens']}"
                    )

                # JSON mode can return blank content even with finish_reason=stop.
                raw_content = choice.message.content or ""
                try:
                    return self._build_result(json.loads(raw_content), raw_content)
                except json.JSONDecodeError:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        print(f"⚠️ DeepSeek returned invalid JSON, retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)

        raise RuntimeError(f"DeepSeek returned invalid JSON {max_retries} times")
