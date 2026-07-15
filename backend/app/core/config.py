from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="LENS_", extra="ignore"
    )

    api_key: str = "dev-key"
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    vlm_model: str = "claude-sonnet-4-6"
    vlm_max_tokens: int = 150
    tts_model: str = "tts-1"
    tts_voice: str = "alloy"
    whisper_model: str = "base"
    max_image_edge: int = 1280
    max_frames: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
