"""Provider factory for AI operations."""

from enum import Enum
from typing import Optional

from loguru import logger

from kubrick_mcp.config import get_settings

from .base import EmbeddingsProvider, ProviderUnavailableError, TranscriptionProvider, VisionProvider
from .bedrock import BedrockEmbeddingsProvider, BedrockVisionProvider
from .openai import OpenAIEmbeddingsProvider, OpenAITranscriptionProvider, OpenAIVisionProvider
from .aws_transcribe import AWSTranscribeProvider


class ProviderType(Enum):
    """Supported provider types."""
    OPENAI = "openai"
    BEDROCK = "bedrock"


class AIProviderFactory:
    """Factory for creating AI providers."""
    
    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self._vision_provider = None
        self._embeddings_provider = None
        self._transcription_provider = None
    
    async def get_vision_provider(self) -> VisionProvider:
        """Get the configured vision provider."""
        if self._vision_provider is None:
            provider_type = ProviderType(self.settings.VISION_PROVIDER.lower())
            
            if provider_type == ProviderType.BEDROCK:
                self._vision_provider = BedrockVisionProvider(
                    region=self.settings.AWS_REGION,
                    model_id=self.settings.BEDROCK_CLAUDE_MODEL
                )
            else:
                self._vision_provider = OpenAIVisionProvider(
                    model=self.settings.IMAGE_CAPTION_MODEL
                )
            
            await self._vision_provider.initialize()
            logger.info(f"Vision provider initialized: {provider_type.value}")
        
        return self._vision_provider
    
    async def get_embeddings_provider(self) -> EmbeddingsProvider:
        """Get the configured embeddings provider."""
        if self._embeddings_provider is None:
            provider_type = ProviderType(self.settings.EMBEDDINGS_PROVIDER.lower())
            
            if provider_type == ProviderType.BEDROCK:
                self._embeddings_provider = BedrockEmbeddingsProvider(
                    region=self.settings.AWS_REGION,
                    model_id=self.settings.BEDROCK_EMBEDDINGS_MODEL
                )
            else:
                self._embeddings_provider = OpenAIEmbeddingsProvider(
                    model=self.settings.TRANSCRIPT_SIMILARITY_EMBD_MODEL
                )
            
            await self._embeddings_provider.initialize()
            logger.info(f"Embeddings provider initialized: {provider_type.value}")
        
        return self._embeddings_provider
    
    async def get_transcription_provider(self) -> TranscriptionProvider:
        """Get the configured transcription provider with intelligent fallback."""
        if self._transcription_provider is None:
            # Check if OpenAI key is available
            openai_available = bool(getattr(self.settings, 'OPENAI_API_KEY', None))
            
            if openai_available:
                # Use OpenAI Whisper if key is available
                self._transcription_provider = OpenAITranscriptionProvider(
                    model=self.settings.AUDIO_TRANSCRIPT_MODEL
                )
                logger.info("Using OpenAI for transcription (API key available)")
            else:
                # Fall back to AWS Transcribe if no OpenAI key
                self._transcription_provider = AWSTranscribeProvider(
                    region=self.settings.AWS_REGION
                )
                logger.info("Using AWS Transcribe for transcription (no OpenAI key)")
            
            await self._transcription_provider.initialize()
        
        return self._transcription_provider
    
    async def get_vision_provider_with_fallback(self) -> VisionProvider:
        """Get vision provider with fallback to OpenAI."""
        try:
            provider = await self.get_vision_provider()
            if provider.is_available():
                return provider
        except Exception as e:
            logger.warning(f"Primary vision provider failed: {e}")
        
        # Fallback to OpenAI
        try:
            fallback_provider = OpenAIVisionProvider(model=self.settings.IMAGE_CAPTION_MODEL)
            await fallback_provider.initialize()
            if fallback_provider.is_available():
                logger.info("Using fallback OpenAI vision provider")
                return fallback_provider
        except Exception as e:
            logger.error(f"Fallback vision provider also failed: {e}")
        
        raise ProviderUnavailableError("all", "All vision providers unavailable")
    
    async def get_embeddings_provider_with_fallback(self) -> EmbeddingsProvider:
        """Get embeddings provider with fallback to OpenAI."""
        try:
            provider = await self.get_embeddings_provider()
            if provider.is_available():
                return provider
        except Exception as e:
            logger.warning(f"Primary embeddings provider failed: {e}")
        
        # Fallback to OpenAI
        try:
            fallback_provider = OpenAIEmbeddingsProvider(model=self.settings.TRANSCRIPT_SIMILARITY_EMBD_MODEL)
            await fallback_provider.initialize()
            if fallback_provider.is_available():
                logger.info("Using fallback OpenAI embeddings provider")
                return fallback_provider
        except Exception as e:
            logger.error(f"Fallback embeddings provider also failed: {e}")
        
        raise ProviderUnavailableError("all", "All embeddings providers unavailable")
    
    async def get_transcription_provider_with_fallback(self) -> TranscriptionProvider:
        """Get transcription provider with fallback logic."""
        try:
            provider = await self.get_transcription_provider()
            if provider.is_available():
                return provider
        except Exception as e:
            logger.warning(f"Primary transcription provider failed: {e}")
        
        # Try alternative provider
        try:
            openai_available = bool(getattr(self.settings, 'OPENAI_API_KEY', None))
            
            if openai_available:
                # Try AWS Transcribe as fallback
                fallback_provider = AWSTranscribeProvider(region=self.settings.AWS_REGION)
                await fallback_provider.initialize()
                if fallback_provider.is_available():
                    logger.info("Using fallback AWS Transcribe provider")
                    return fallback_provider
            else:
                # Try OpenAI as fallback (if key becomes available)
                fallback_provider = OpenAITranscriptionProvider(model=self.settings.AUDIO_TRANSCRIPT_MODEL)
                await fallback_provider.initialize()
                if fallback_provider.is_available():
                    logger.info("Using fallback OpenAI transcription provider")
                    return fallback_provider
        except Exception as e:
            logger.error(f"Fallback transcription provider also failed: {e}")
        
        raise ProviderUnavailableError("all", "All transcription providers unavailable")