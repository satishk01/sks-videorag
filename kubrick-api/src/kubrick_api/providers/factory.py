"""Provider factory for agent operations."""

from enum import Enum
from typing import Optional

from loguru import logger

from kubrick_api.config import get_settings

from .base import ChatProvider, ProviderUnavailableError
from .bedrock import BedrockChatProvider
from .groq import GroqChatProvider


class ProviderType(Enum):
    """Supported provider types."""
    GROQ = "groq"
    BEDROCK = "bedrock"


class AgentProviderFactory:
    """Factory for creating agent providers."""
    
    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self._chat_provider = None
    
    async def get_chat_provider(self) -> ChatProvider:
        """Get the configured chat provider."""
        if self._chat_provider is None:
            provider_type = ProviderType(self.settings.AGENT_PROVIDER.lower())
            
            if provider_type == ProviderType.BEDROCK:
                self._chat_provider = BedrockChatProvider(
                    region=self.settings.AWS_REGION,
                    model_id=self.settings.BEDROCK_CLAUDE_MODEL
                )
            else:
                self._chat_provider = GroqChatProvider(
                    api_key=self.settings.GROQ_API_KEY,
                    model=self.settings.GROQ_TOOL_USE_MODEL
                )
            
            await self._chat_provider.initialize()
            logger.info(f"Chat provider initialized: {provider_type.value}")
        
        return self._chat_provider
    
    async def get_chat_provider_with_fallback(self) -> ChatProvider:
        """Get chat provider with fallback to Groq."""
        try:
            provider = await self.get_chat_provider()
            if provider.is_available():
                return provider
        except Exception as e:
            logger.warning(f"Primary chat provider failed: {e}")
        
        # Fallback to Groq
        try:
            fallback_provider = GroqChatProvider(
                api_key=self.settings.GROQ_API_KEY,
                model=self.settings.GROQ_TOOL_USE_MODEL
            )
            await fallback_provider.initialize()
            if fallback_provider.is_available():
                logger.info("Using fallback Groq chat provider")
                return fallback_provider
        except Exception as e:
            logger.error(f"Fallback chat provider also failed: {e}")
        
        raise ProviderUnavailableError("all", "All chat providers unavailable")