from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from openai import AsyncOpenAI


class TextToSpeech(ABC):
    @abstractmethod
    def stream_speech(self, text: str) -> AsyncIterator[bytes]: ...


class OpenAITTS(TextToSpeech):
    def __init__(self, api_key: str, model: str = "tts-1", voice: str = "alloy") -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._voice = voice

    async def stream_speech(self, text: str) -> AsyncIterator[bytes]:
        async with self._client.audio.speech.with_streaming_response.create(
            model=self._model,
            voice=self._voice,
            input=text,
            response_format="mp3",
        ) as response:
            async for chunk in response.iter_bytes(4096):
                yield chunk
