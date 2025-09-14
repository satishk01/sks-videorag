from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="kubrick-mcp/.env", extra="ignore", env_file_encoding="utf-8")

    # --- OPIK Configuration ---
    OPIK_API_KEY: str
    OPIK_WORKSPACE: str = "default"
    OPIK_PROJECT: str = "kubrick-mcp"

    # --- OPENAI Configuration ---
    OPENAI_API_KEY: Optional[str] = None
    AUDIO_TRANSCRIPT_MODEL: str = "gpt-4o-mini-transcribe"  # Whisper tiny model 37M
    IMAGE_CAPTION_MODEL: str = "gpt-4o-mini"

    # --- AWS Bedrock Configuration ---
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_SESSION_TOKEN: Optional[str] = None

    # --- Provider Selection ---
    VISION_PROVIDER: str = "openai"  # openai | bedrock
    TRANSCRIPTION_PROVIDER: str = "openai"  # openai | bedrock
    EMBEDDINGS_PROVIDER: str = "openai"  # openai | bedrock

    # --- Bedrock Model Configuration ---
    BEDROCK_CLAUDE_MODEL: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    BEDROCK_EMBEDDINGS_MODEL: str = "amazon.titan-embed-text-v1"

    # --- Video Ingestion Configuration ---
    SPLIT_FRAMES_COUNT: int = 45
    AUDIO_CHUNK_LENGTH: int = 10
    AUDIO_OVERLAP_SECONDS: int = 1
    AUDIO_MIN_CHUNK_DURATION_SECONDS: int = 1

    # --- Transcription Similarity Search Configuration ---
    TRANSCRIPT_SIMILARITY_EMBD_MODEL: str = "text-embedding-3-small"

    # --- Image Similarity Search Configuration ---
    IMAGE_SIMILARITY_EMBD_MODEL: str = "openai/clip-vit-base-patch32"

    # --- Image Captioning Configuration ---
    IMAGE_RESIZE_WIDTH: int = 1024
    IMAGE_RESIZE_HEIGHT: int = 768
    CAPTION_SIMILARITY_EMBD_MODEL: str = "text-embedding-3-small"

    # --- Caption Similarity Search Configuration ---
    CAPTION_MODEL_PROMPT: str = "Describe what is happening in the image"
    DELTA_SECONDS_FRAME_INTERVAL: float = 5.0

    # --- Video Search Engine Configuration ---
    VIDEO_CLIP_SPEECH_SEARCH_TOP_K: int = 1
    VIDEO_CLIP_CAPTION_SEARCH_TOP_K: int = 1
    VIDEO_CLIP_IMAGE_SEARCH_TOP_K: int = 1
    QUESTION_ANSWER_TOP_K: int = 3
    
    # --- Server Configuration ---
    MCP_HOST: str = "0.0.0.0"
    MCP_PORT: int = 9090


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get the application settings.

    Returns:
        Settings: The application settings.
    """
    return Settings()
