"""Base provider interfaces for AI operations."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ProviderError(Exception):
    """Base exception for provider errors."""
    
    def __init__(self, provider: str, message: str, original_error: Exception = None):
        self.provider = provider
        self.message = message
        self.original_error = original_error
        super().__init__(f"{provider}: {message}")


class ProviderUnavailableError(ProviderError):
    """Provider is not available or misconfigured."""
    pass


class ChatResponse(BaseModel):
    """Response model for chat operations."""
    message: str
    usage: Optional[Dict] = None
    provider: str


class AIProvider(ABC):
    """Base interface for AI providers."""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider with credentials and configuration."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and properly configured."""
        pass


class ChatProvider(AIProvider):
    """Interface for conversational AI operations."""
    
    @abstractmethod
    async def chat_completion(self, messages: List[Dict], model: str, **kwargs) -> ChatResponse:
        """Generate chat completion."""
        pass