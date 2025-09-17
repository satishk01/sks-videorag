from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="agent-api/.env", extra="ignore", env_file_encoding="utf-8")

    # --- GROQ Configuration ---
    GROQ_API_KEY: Optional[str] = None
    GROQ_ROUTING_MODEL: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    GROQ_TOOL_USE_MODEL: str = "meta-llama/llama-4-maverick-17b-128e-instruct"
    GROQ_IMAGE_MODEL: str = "meta-llama/llama-4-maverick-17b-128e-instruct"
    GROQ_GENERAL_MODEL: str = "meta-llama/llama-4-maverick-17b-128e-instruct"

    # --- AWS Bedrock Configuration ---
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_SESSION_TOKEN: Optional[str] = None

    # --- Provider Selection ---
    AGENT_PROVIDER: str = "groq"  # groq | bedrock

    # --- Bedrock Model Configuration ---
    BEDROCK_CLAUDE_MODEL: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"

    # --- Comet ML & Opik Configuration ---
    OPIK_API_KEY: str | None = Field(default=None, description="API key for Comet ML and Opik services.")
    OPIK_WORKSPACE: str = "default"
    OPIK_PROJECT: str = Field(
        default="kubrick-api",
        description="Project name for Comet ML and Opik tracking.",
    )

    # --- Memory Configuration ---
    AGENT_MEMORY_SIZE: int = 20

    # --- MCP Configuration ---
    MCP_SERVER: str = "http://kubrick-mcp:9090/mcp"
    
    # --- Server Configuration ---
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8080

    # --- Disable Nest Asyncio ---
    DISABLE_NEST_ASYNCIO: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get the application settings.

    Returns:
        Settings: The application settings.
    """
    return Settings()
