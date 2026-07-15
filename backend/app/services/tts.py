import asyncio
import threading
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from openai import AsyncOpenAI


class TextToSpeech(ABC):
    @abstractmethod
    def stream_speech(self, text: str) -> AsyncIterator[bytes]: ...

    def warm_up(self) -> None:
        """Optional: pay one-time model-load costs at startup, not first request."""


class KokoroTTS(TextToSpeech):
    """Local neural TTS (hexgrad/Kokoro-82M). No network round-trip: first
    audio for a short sentence lands in a few hundred ms on Apple Silicon.
    Segments are encoded to mp3 so the client contract stays audio/mpeg."""

    SAMPLE_RATE = 24000

    def __init__(self, voice: str = "af_heart", device: str = "auto") -> None:
        self._voice = voice
        self._device = device
        self._pipeline = None
        self._lock = threading.Lock()

    def _load(self):
        with self._lock:
            if self._pipeline is None:
                import torch
                from kokoro import KPipeline

                device = self._device
                if device == "auto":
                    device = "mps" if torch.backends.mps.is_available() else "cpu"
                self._pipeline = KPipeline(
                    lang_code="a", repo_id="hexgrad/Kokoro-82M", device=device
                )
        return self._pipeline

    def warm_up(self) -> None:
        pipeline = self._load()
        for _ in pipeline("Ready.", voice=self._voice):
            pass

    def _encode_mp3(self, audio) -> bytes:
        import lameenc
        import numpy as np

        pcm = (audio.numpy() * 32767).astype(np.int16).tobytes()
        encoder = lameenc.Encoder()
        encoder.set_bit_rate(96)
        encoder.set_in_sample_rate(self.SAMPLE_RATE)
        encoder.set_channels(1)
        encoder.set_quality(5)
        encoder.silence()
        return bytes(encoder.encode(pcm)) + bytes(encoder.flush())

    async def stream_speech(self, text: str) -> AsyncIterator[bytes]:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[bytes | None] = asyncio.Queue()

        def synth() -> None:
            try:
                pipeline = self._load()
                for _graphemes, _phonemes, audio in pipeline(text, voice=self._voice):
                    chunk = self._encode_mp3(audio)
                    loop.call_soon_threadsafe(queue.put_nowait, chunk)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        threading.Thread(target=synth, daemon=True).start()
        while (chunk := await queue.get()) is not None:
            if chunk:
                yield chunk


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
