import io
from abc import ABC, abstractmethod

import anyio.to_thread


class SpeechToText(ABC):
    @abstractmethod
    async def transcribe(self, audio: bytes) -> str: ...


class FasterWhisperSTT(SpeechToText):
    """Local faster-whisper. Model loads lazily on first request; audio
    decoding (webm/m4a/wav) is handled by its bundled PyAV, no system ffmpeg
    needed."""

    def __init__(self, model_size: str = "base") -> None:
        self._model_size = model_size
        self._model = None

    def _load(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(self._model_size, compute_type="int8")
        return self._model

    async def transcribe(self, audio: bytes) -> str:
        return await anyio.to_thread.run_sync(self._transcribe_sync, audio)

    def _transcribe_sync(self, audio: bytes) -> str:
        segments, _info = self._load().transcribe(io.BytesIO(audio))
        return " ".join(s.text.strip() for s in segments).strip()
