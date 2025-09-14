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


class VisionResponse(BaseModel):
    """Response model for vision operations."""
    caption: str
    confidence: Optional[float] = None
    provider: str


class TranscriptionResponse(BaseModel):
    """Response model for transcription operations."""
    text: str
    language: Optional[str] = None
    provider: str


class EmbeddingsResponse(BaseModel):
    """Response model for embeddings operations."""
    embeddings: List[float]
    model: str
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


class VisionProvider(AIProvider):
    """Interface for vision/image captioning operations."""
    
    @abstractmethod
    async def generate_caption(self, image: bytes, prompt: str) -> VisionResponse:
        """Generate caption for an image."""
        pass


class TranscriptionProvider(AIProvider):
    """Interface for audio transcription operations."""
    
    @abstractmethod
    async def transcribe_audio(self, audio: bytes, model: str) -> TranscriptionResponse:
        """Transcribe audio to text."""
        pass


class EmbeddingsProvider(AIProvider):
    """Interface for text embeddings operations."""
    
    @abstractmethod
    async def generate_embeddings(self, text: str, model: str) -> EmbeddingsResponse:
        """Generate embeddings for text."""
        pass