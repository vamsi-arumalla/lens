import base64
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from anthropic import AsyncAnthropic

SYSTEM_PROMPT = (
    "You are Lens, a real-time vision assistant. The user is pointing a camera "
    "at the world and speaking to you. Answer from the attached frame(s). Your "
    "answer is read aloud: default to a single short spoken sentence, two only "
    "when truly needed — no markdown, no lists, no preamble. If the frame "
    "doesn't show what's asked, say so briefly."
)

MEMORY_ADDENDUM = (
    " You also have a search_memory tool over everything the user previously "
    "captured (photos with captions and heard speech). Use it whenever the "
    "question refers to the past or to something not visible in the current "
    "frame — 'where did I…', 'what was…', 'have I seen…'. Answer from the "
    "returned moments and say when the moment was from."
)

CAPTION_PROMPT = (
    "Describe this photo in one line of at most 20 words: the main objects, "
    "WHERE they are (which room or surface, if inferable), and any readable "
    "text. Reply with just that line."
)

SEARCH_MEMORY_TOOL = {
    "name": "search_memory",
    "description": (
        "Search the user's captured moments (photos + transcribed speech) by "
        "natural-language query. Returns the best-matching moments with their "
        "timestamps, captions, and thumbnail images."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to look for"},
            "limit": {"type": "integer", "description": "Max moments (default 3)"},
        },
        "required": ["query"],
    },
}

# async (query, limit) -> [{caption, transcript, question, answer, when, thumb_jpeg}]
MemorySearch = Callable[[str, int], Awaitable[list[dict[str, Any]]]]


def _image_block(jpeg: bytes) -> dict:
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/jpeg",
            "data": base64.b64encode(jpeg).decode(),
        },
    }


def _moments_to_tool_content(moments: list[dict[str, Any]]) -> list[dict]:
    if not moments:
        return [{"type": "text", "text": "No matching moments found."}]
    content: list[dict] = []
    for i, m in enumerate(moments, 1):
        lines = [f"Moment {i} — captured {m['when']}: {m['caption']}"]
        if m.get("transcript"):
            lines.append(f"Heard: {m['transcript']}")
        if m.get("question"):
            lines.append(f"User asked: {m['question']} Answer: {m.get('answer', '')}")
        content.append({"type": "text", "text": "\n".join(lines)})
        content.append(_image_block(m["thumb_jpeg"]))
    return content


class VisionLanguageModel(ABC):
    @abstractmethod
    def stream_answer(
        self,
        question: str,
        images_jpeg: list[bytes],
        memory_search: MemorySearch | None = None,
    ) -> AsyncIterator[str]: ...

    @abstractmethod
    async def caption(self, images_jpeg: list[bytes]) -> str: ...


class AnthropicVLM(VisionLanguageModel):
    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int = 150,
        caption_model: str | None = None,
    ) -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens
        self._caption_model = caption_model or model

    async def stream_answer(
        self,
        question: str,
        images_jpeg: list[bytes],
        memory_search: MemorySearch | None = None,
    ) -> AsyncIterator[str]:
        content: list[dict] = [_image_block(img) for img in images_jpeg]
        content.append({"type": "text", "text": question})
        messages: list[dict] = [{"role": "user", "content": content}]

        system = SYSTEM_PROMPT
        kwargs: dict[str, Any] = {}
        if memory_search is not None:
            system += MEMORY_ADDENDUM
            kwargs["tools"] = [SEARCH_MEMORY_TOOL]

        # Tool-use loop: capped so a confused model can't search forever
        for _round in range(4):
            async with self._client.messages.stream(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                messages=messages,
                **kwargs,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
                final = await stream.get_final_message()

            if final.stop_reason != "tool_use" or memory_search is None:
                return

            messages.append({"role": "assistant", "content": final.content})
            results = []
            for block in final.content:
                if block.type == "tool_use":
                    moments = await memory_search(
                        str(block.input.get("query") or question),
                        int(block.input.get("limit") or 3),
                    )
                    results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": _moments_to_tool_content(moments),
                        }
                    )
            messages.append({"role": "user", "content": results})

    async def caption(self, images_jpeg: list[bytes]) -> str:
        content: list[dict] = [_image_block(img) for img in images_jpeg]
        content.append({"type": "text", "text": CAPTION_PROMPT})
        response = await self._client.messages.create(
            model=self._caption_model,
            max_tokens=60,
            messages=[{"role": "user", "content": content}],
        )
        return response.content[0].text.strip()
