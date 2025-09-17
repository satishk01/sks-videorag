"""Monkey patch for VideoProcessor to use AWS services."""

import asyncio
import tempfile
import base64
import io
from loguru import logger
from PIL import Image

from kubrick_mcp.config import get_settings
from kubrick_mcp.providers.factory import AIProviderFactory

logger = logger.bind(name="AWSPatch")
settings = get_settings()

# Global provider factory
_provider_factory = AIProviderFactory()
_providers_initialized = False
_transcription_provider = None
_vision_provider = None
_embeddings_provider = None


async def _init_providers():
    """Initialize AWS providers."""
    global _providers_initialized, _transcription_provider, _vision_provider, _embeddings_provider
    
    if not _providers_initialized:
        logger.info("Initializing AWS providers...")
        _transcription_provider = await _provider_factory.get_transcription_provider_with_fallback()
        _vision_provider = await _provider_factory.get_vision_provider_with_fallback()
        _embeddings_provider = await _provider_factory.get_embeddings_provider_with_fallback()
        
        logger.info(f"Transcription provider: {type(_transcription_provider).__name__}")
        logger.info(f"Vision provider: {type(_vision_provider).__name__}")
        logger.info(f"Embeddings provider: {type(_embeddings_provider).__name__}")
        
        _providers_initialized = True


def _run_async(coro):
    """Run async function in sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Create new loop in thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def aws_transcribe_function(audio_data, model=None):
    """AWS transcription function."""
    try:
        logger.info("Starting AWS transcription...")
        
        async def transcribe():
            await _init_providers()
            
            # Save audio to temp file
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                if hasattr(audio_data, 'read'):
                    audio_bytes = audio_data.read()
                else:
                    audio_bytes = audio_data
                
                temp_file.write(audio_bytes)
                temp_file.flush()
                
                # Read back as bytes for transcription
                with open(temp_file.name, 'rb') as f:
                    audio_for_transcription = f.read()
                
                result = await _transcription_provider.transcribe_audio(audio_for_transcription)
                logger.info(f"Transcription result: {result[:100] if result else 'Empty'}...")
                return result or ""
        
        return _run_async(transcribe())
        
    except Exception as e:
        logger.error(f"AWS transcription error: {e}")
        return ""


def aws_vision_function(image_data, prompt, model=None):
    """AWS vision function."""
    try:
        logger.info("Starting AWS vision analysis...")
        
        async def analyze():
            await _init_providers()
            
            # Convert image to base64
            if hasattr(image_data, 'convert'):
                # PIL Image
                buffer = io.BytesIO()
                image_data.convert('RGB').save(buffer, format='JPEG')
                image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            elif isinstance(image_data, bytes):
                image_base64 = base64.b64encode(image_data).decode('utf-8')
            else:
                # Try to handle as file-like object
                if hasattr(image_data, 'read'):
                    image_bytes = image_data.read()
                else:
                    image_bytes = image_data
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            result = await _vision_provider.analyze_image(image_base64, prompt)
            logger.info(f"Vision result: {result[:100] if result else 'Empty'}...")
            return result or ""
        
        return _run_async(analyze())
        
    except Exception as e:
        logger.error(f"AWS vision error: {e}")
        return ""


def aws_embeddings_function(text, model=None):
    """AWS embeddings function."""
    try:
        logger.info("Starting AWS embeddings generation...")
        
        async def embed():
            await _init_providers()
            result = await _embeddings_provider.generate_embeddings([text])
            embeddings = result[0] if result else []
            logger.info(f"Generated embedding with {len(embeddings)} dimensions")
            return embeddings
        
        return _run_async(embed())
        
    except Exception as e:
        logger.error(f"AWS embeddings error: {e}")
        return []


def patch_video_processor():
    """Patch VideoProcessor to use AWS functions when OpenAI is not available."""
    openai_available = bool(getattr(settings, 'OPENAI_API_KEY', None))
    
    if openai_available:
        logger.info("OpenAI API key available - using OpenAI functions")
        return
    
    logger.info("No OpenAI API key - patching VideoProcessor to use AWS functions")
    
    # Import and patch the VideoProcessor
    from kubrick_mcp.video.ingestion import video_processor
    
    # Store original methods
    original_add_audio_transcription = video_processor.VideoProcessor._add_audio_transcription
    original_add_frame_captioning = video_processor.VideoProcessor._add_frame_captioning
    original_add_audio_embedding_index = video_processor.VideoProcessor._add_audio_embedding_index
    original_add_caption_embedding_index = video_processor.VideoProcessor._add_caption_embedding_index
    
    def patched_add_audio_transcription(self):
        """Patched transcription method."""
        logger.info("Using AWS Transcribe for audio transcription")
        
        # Create a simple UDF for transcription
        import pixeltable as pxt
        
        @pxt.udf
        def transcribe_with_aws(audio):
            return aws_transcribe_function(audio)
        
        self.audio_chunks.add_computed_column(
            transcription=transcribe_with_aws(self.audio_chunks.audio_chunk),
            if_exists="ignore",
        )
    
    def patched_add_frame_captioning(self):
        """Patched captioning method."""
        logger.info("Using AWS Bedrock for image captioning")
        
        import pixeltable as pxt
        
        @pxt.udf
        def caption_with_aws(image):
            return aws_vision_function(image, settings.CAPTION_MODEL_PROMPT)
        
        self.frames_view.add_computed_column(
            im_caption=caption_with_aws(self.frames_view.resized_frame)
        )
    
    def patched_add_audio_embedding_index(self):
        """Patched audio embedding method."""
        if settings.EMBEDDINGS_PROVIDER.lower() == "bedrock":
            logger.info("Using AWS Bedrock for audio embeddings")
            
            import pixeltable as pxt
            
            @pxt.udf(return_type=pxt.ArrayType(pxt.FloatType()))
            def embed_with_aws(text):
                return aws_embeddings_function(text)
            
            # Add embedding column first
            self.audio_chunks.add_computed_column(
                chunk_embedding=embed_with_aws(self.audio_chunks.chunk_text),
                if_exists="ignore",
            )
            # Then add index
            self.audio_chunks.add_embedding_index(
                column=self.audio_chunks.chunk_embedding,
                if_exists="ignore",
                idx_name="chunks_index",
            )
        else:
            # Use original method
            original_add_audio_embedding_index(self)
    
    def patched_add_caption_embedding_index(self):
        """Patched caption embedding method."""
        if settings.EMBEDDINGS_PROVIDER.lower() == "bedrock":
            logger.info("Using AWS Bedrock for caption embeddings")
            
            import pixeltable as pxt
            
            @pxt.udf(return_type=pxt.ArrayType(pxt.FloatType()))
            def embed_with_aws(text):
                return aws_embeddings_function(text)
            
            # Add embedding column first
            self.frames_view.add_computed_column(
                caption_embedding=embed_with_aws(self.frames_view.im_caption),
                if_exists="ignore",
            )
            # Then add index
            self.frames_view.add_embedding_index(
                column=self.frames_view.caption_embedding,
                if_exists="replace_force",
            )
        else:
            # Use original method
            original_add_caption_embedding_index(self)
    
    # Apply patches
    video_processor.VideoProcessor._add_audio_transcription = patched_add_audio_transcription
    video_processor.VideoProcessor._add_frame_captioning = patched_add_frame_captioning
    video_processor.VideoProcessor._add_audio_embedding_index = patched_add_audio_embedding_index
    video_processor.VideoProcessor._add_caption_embedding_index = patched_add_caption_embedding_index
    
    logger.info("VideoProcessor patched successfully for AWS usage")