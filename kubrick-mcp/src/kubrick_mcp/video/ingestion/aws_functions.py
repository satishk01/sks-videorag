"""AWS-compatible functions for Pixeltable video processing."""

import asyncio
import base64
import io
import tempfile
from typing import Any, Dict, List

import pixeltable as pxt
from PIL import Image
from loguru import logger

from kubrick_mcp.providers.factory import AIProviderFactory

logger = logger.bind(name="AWSPixeltableFunctions")

# Global provider factory instance
_provider_factory = AIProviderFactory()


def _run_async(coro):
    """Helper to run async functions in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        # If we're already in an event loop, we need to use a different approach
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        return loop.run_until_complete(coro)


async def _get_transcription_provider():
    """Get transcription provider."""
    return await _provider_factory.get_transcription_provider_with_fallback()


async def _get_vision_provider():
    """Get vision provider."""
    return await _provider_factory.get_vision_provider_with_fallback()


async def _get_embeddings_provider():
    """Get embeddings provider."""
    return await _provider_factory.get_embeddings_provider_with_fallback()


# Pixeltable-compatible function wrappers
@pxt.udf
def aws_transcribe(audio, model: str = None) -> str:
    """Pixeltable UDF for AWS transcription."""
    try:
        logger.info("Starting AWS transcription")
        
        # Save audio to temporary file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            if hasattr(audio, 'read'):
                # File-like object
                temp_file.write(audio.read())
            else:
                # Bytes
                temp_file.write(audio)
            temp_file.flush()
            
            async def transcribe():
                provider = await _get_transcription_provider()
                with open(temp_file.name, 'rb') as f:
                    audio_data = f.read()
                return await provider.transcribe_audio(audio_data)
            
            result = _run_async(transcribe())
            logger.info(f"Transcription result: {result[:100] if result else 'Empty'}...")
            return result or ""
            
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return ""


@pxt.udf  
def aws_vision(image, prompt: str, model: str = None) -> str:
    """Pixeltable UDF for AWS vision."""
    try:
        logger.info("Starting AWS vision analysis")
        
        # Convert Pixeltable image to base64
        if hasattr(image, 'convert'):
            # PIL Image
            buffer = io.BytesIO()
            image.convert('RGB').save(buffer, format='JPEG')
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        elif hasattr(image, 'read'):
            # File-like object
            image_data = image.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')
        else:
            # Assume it's already bytes
            image_base64 = base64.b64encode(image).decode('utf-8')
        
        async def analyze():
            provider = await _get_vision_provider()
            return await provider.analyze_image(image_base64, prompt)
        
        result = _run_async(analyze())
        logger.info(f"Vision result: {result[:100] if result else 'Empty'}...")
        return result or ""
        
    except Exception as e:
        logger.error(f"Vision error: {e}")
        return ""


@pxt.udf
def aws_embeddings(text: str, model: str = None) -> List[float]:
    """Pixeltable UDF for AWS embeddings."""
    try:
        logger.info("Starting AWS embeddings generation")
        
        async def embed():
            provider = await _get_embeddings_provider()
            result = await provider.generate_embeddings([text])
            return result[0] if result else []
        
        result = _run_async(embed())
        logger.info(f"Generated embedding with {len(result)} dimensions")
        return result
        
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        return []