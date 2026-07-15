import base64
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from anthropic import AsyncAnthropic

SYSTEM_PROMPT = (
    "You are Lens, a real-time vision assistant. The user is pointing a camera "
    "at the world and speaking to you. Answer from the attached frame(s). Your "
    "answer is read aloud: default to a single short spoken sentence, two only "
    "when truly needed — no markdown, no lists, no preamble. If the frame "
    "doesn't show what's asked, say so briefly."
)


class VisionLanguageModel(ABC):
    @abstractmethod
    def stream_answer(
        self, question: str, images_jpeg: list[bytes]
    ) -> AsyncIterator[str]: ...


class AnthropicVLM(VisionLanguageModel):
    def __init__(self, api_key: str, model: str, max_tokens: int = 300) -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    async def stream_answer(
        self, question: str, images_jpeg: list[bytes]
    ) -> AsyncIterator[str]:
        content: list[dict] = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": base64.b64encode(img).decode(),
                },
            }
            for img in images_jpeg
        ]
        content.append({"type": "text", "text": question})
        async with self._client.messages.stream(
            model=self._model,
            max_tokens=self._max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
        ) as stream:
            async for text in stream.text_stream:
                yield text
