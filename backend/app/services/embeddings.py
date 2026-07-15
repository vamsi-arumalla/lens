import io
import threading
from abc import ABC, abstractmethod

import anyio.to_thread

IMAGE_DIM = 512  # open-clip ViT-B-32
TEXT_DIM = 384  # all-MiniLM-L6-v2


class Embeddings(ABC):
    @abstractmethod
    async def embed_image(self, jpeg: bytes) -> list[float]: ...

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]: ...

    @abstractmethod
    async def embed_query_for_images(self, text: str) -> list[float]:
        """Embed a text query into the *image* embedding space (CLIP text
        tower), so a natural-language query can match stored frames."""

    def warm_up(self) -> None: ...


class LocalEmbeddings(Embeddings):
    """open-clip for images (and image-space queries) + sentence-transformers
    for text. Runs on CPU in-process; both models load lazily."""

    def __init__(self, clip_model: str, clip_pretrained: str, text_model: str) -> None:
        self._clip_name = clip_model
        self._clip_pretrained = clip_pretrained
        self._text_name = text_model
        self._lock = threading.Lock()
        self._clip = None
        self._st = None

    def _load(self):
        with self._lock:
            if self._clip is None:
                import open_clip
                from sentence_transformers import SentenceTransformer

                model, _, preprocess = open_clip.create_model_and_transforms(
                    self._clip_name, pretrained=self._clip_pretrained
                )
                model.eval()
                tokenizer = open_clip.get_tokenizer(self._clip_name)
                self._clip = (model, preprocess, tokenizer)
                self._st = SentenceTransformer(self._text_name, device="cpu")
        return self._clip, self._st

    def warm_up(self) -> None:
        self._load()

    def _embed_image_sync(self, jpeg: bytes) -> list[float]:
        import torch
        from PIL import Image

        (model, preprocess, _), _ = self._load()
        image = preprocess(Image.open(io.BytesIO(jpeg)).convert("RGB")).unsqueeze(0)
        with torch.no_grad():
            features = model.encode_image(image)
            features /= features.norm(dim=-1, keepdim=True)
        return features[0].tolist()

    def _embed_clip_text_sync(self, text: str) -> list[float]:
        import torch

        (model, _, tokenizer), _ = self._load()
        tokens = tokenizer([text])
        with torch.no_grad():
            features = model.encode_text(tokens)
            features /= features.norm(dim=-1, keepdim=True)
        return features[0].tolist()

    def _embed_text_sync(self, text: str) -> list[float]:
        _, st = self._load()
        return st.encode([text], normalize_embeddings=True)[0].tolist()

    async def embed_image(self, jpeg: bytes) -> list[float]:
        return await anyio.to_thread.run_sync(self._embed_image_sync, jpeg)

    async def embed_text(self, text: str) -> list[float]:
        return await anyio.to_thread.run_sync(self._embed_text_sync, text)

    async def embed_query_for_images(self, text: str) -> list[float]:
        return await anyio.to_thread.run_sync(self._embed_clip_text_sync, text)
