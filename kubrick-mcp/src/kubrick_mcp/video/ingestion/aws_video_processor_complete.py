"""Complete AWS-native VideoProcessor that works without OpenAI."""

import asyncio
import uuid
import tempfile
import base64
import io
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import pixeltable as pxt
from loguru import logger
from pixeltable.functions.huggingface import clip
from pixeltable.functions.video import extract_audio
from pixeltable.iterators import AudioSplitter
from pixeltable.iterators.video import FrameIterator
from PIL import Image

import kubrick_mcp.video.ingestion.registry as registry
from kubrick_mcp.config import get_settings
from kubrick_mcp.providers.factory import AIProviderFactory
from kubrick_mcp.video.ingestion.functions import extract_text_from_chunk, resize_image
from kubrick_mcp.video.ingestion.tools import re_encode_video

if TYPE_CHECKING:
    from kubrick_mcp.video.ingestion.models import CachedTable

logger = logger.bind(name="AWSVideoProcessor")
settings = get_settings()


def _run_async(coro):
    """Helper to run async functions in sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an event loop, create a new one in a thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


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
        logger.info("Initializing AWS providers for video processing...")
        _transcription_provider = await _provider_factory.get_transcription_provider_with_fallback()
        _vision_provider = await _provider_factory.get_vision_provider_with_fallback()
        _embeddings_provider = await _provider_factory.get_embeddings_provider_with_fallback()
        
        logger.info(f"Transcription provider: {type(_transcription_provider).__name__}")
        logger.info(f"Vision provider: {type(_vision_provider).__name__}")
        logger.info(f"Embeddings provider: {type(_embeddings_provider).__name__}")
        
        _providers_initialized = True


# AWS-compatible Pixeltable UDFs
@pxt.udf
def aws_transcribe_audio(audio_chunk) -> str:
    """Transcribe audio using AWS providers."""
    try:
        logger.info("Transcribing audio with AWS...")
        
        # Initialize providers
        _run_async(_init_providers())
        
        # Save audio to temporary file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            if hasattr(audio_chunk, 'read'):
                audio_data = audio_chunk.read()
            else:
                audio_data = audio_chunk
            
            temp_file.write(audio_data)
            temp_file.flush()
            
            # Read back for transcription
            with open(temp_file.name, 'rb') as f:
                audio_bytes = f.read()
            
            # Transcribe
            async def transcribe():
                return await _transcription_provider.transcribe_audio(audio_bytes)
            
            result = _run_async(transcribe())
            logger.info(f"Transcription: {result[:100] if result else 'Empty'}...")
            return result or ""
            
    except Exception as e:
        logger.error(f"AWS transcription error: {e}")
        return ""


@pxt.udf
def aws_caption_image(image, prompt: str) -> str:
    """Caption image using AWS providers."""
    try:
        logger.info("Captioning image with AWS...")
        
        # Initialize providers
        _run_async(_init_providers())
        
        # Convert image to base64
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
            # Bytes
            image_base64 = base64.b64encode(image).decode('utf-8')
        
        # Generate caption
        async def caption():
            return await _vision_provider.analyze_image(image_base64, prompt)
        
        result = _run_async(caption())
        logger.info(f"Caption: {result[:100] if result else 'Empty'}...")
        return result or ""
        
    except Exception as e:
        logger.error(f"AWS vision error: {e}")
        return ""


@pxt.udf
def aws_generate_embeddings(text: str) -> list:
    """Generate embeddings using AWS providers."""
    try:
        logger.info("Generating embeddings with AWS...")
        
        # Initialize providers
        _run_async(_init_providers())
        
        # Generate embeddings
        async def embed():
            result = await _embeddings_provider.generate_embeddings([text])
            return result[0] if result else []
        
        embeddings = _run_async(embed())
        logger.info(f"Generated {len(embeddings)} dimensional embedding")
        return embeddings
        
    except Exception as e:
        logger.error(f"AWS embeddings error: {e}")
        return []


class AWSVideoProcessor:
    """Complete AWS-native VideoProcessor."""
    
    def __init__(self):
        self._pxt_cache: Optional[str] = None
        self._video_table = None
        self._frames_view = None
        self._audio_chunks = None
        self._video_mapping_idx: Optional[str] = None

        logger.info(
            "AWSVideoProcessor initialized",
            f"\n Split FPS: {settings.SPLIT_FRAMES_COUNT}",
            f"\n Audio Chunk: {settings.AUDIO_CHUNK_LENGTH} seconds",
            f"\n Using AWS services only",
        )

    def setup_table(self, video_name: str):
        """Set up Pixeltable for video processing."""
        self._video_mapping_idx = video_name
        exists = self._check_if_exists(video_name)
        if exists:
            logger.info(f"Video index '{self._video_mapping_idx}' already exists and is ready for use.")
            cached_table: "CachedTable" = registry.get_table(self._video_mapping_idx)
            self.pxt_cache = cached_table.video_cache
            self.video_table = cached_table.video_table
            self.frames_view = cached_table.frames_view
            self.audio_chunks = cached_table.audio_chunks_view
        else:
            self.pxt_cache = f"cache_{uuid.uuid4().hex[-4:]}"
            self.video_table_name = f"{self.pxt_cache}.table"
            self.frames_view_name = f"{self.video_table_name}_frames"
            self.audio_view_name = f"{self.video_table_name}_audio_chunks"
            self.video_table = None

            self._setup_table()

            registry.add_index_to_registry(
                video_name=self._video_mapping_idx,
                video_cache=self.pxt_cache,
                frames_view_name=self.frames_view_name,
                audio_view_name=self.audio_view_name,
            )
            logger.info(f"Creating new video index '{self.video_table_name}' in '{self.pxt_cache}'")

    def _check_if_exists(self, video_path: str) -> bool:
        """Check if the PixelTable table exists."""
        existing_tables = registry.get_registry()
        return video_path in existing_tables

    def _setup_table(self):
        """Set up the complete table structure."""
        self._setup_cache_directory()
        self._create_video_table()
        self._setup_audio_processing()
        self._setup_frame_processing()

    def _setup_cache_directory(self):
        """Create cache directory."""
        logger.info(f"Creating cache path {self.pxt_cache}.")
        Path(self.pxt_cache).mkdir(parents=True, exist_ok=True)
        pxt.create_dir(self.pxt_cache, if_exists="replace_force")

    def _create_video_table(self):
        """Create the main video table."""
        self.video_table = pxt.create_table(
            self.video_table_name,
            schema={"video": pxt.Video},
            if_exists="replace_force",
        )

    def _setup_audio_processing(self):
        """Set up audio processing pipeline with AWS."""
        self._add_audio_extraction()
        self._create_audio_chunks_view()
        self._add_aws_audio_transcription()
        self._add_audio_text_extraction()
        self._add_aws_audio_embedding_index()

    def _add_audio_extraction(self):
        """Extract audio from video."""
        self.video_table.add_computed_column(
            audio_extract=extract_audio(self.video_table.video, format="mp3"),
            if_exists="ignore",
        )

    def _create_audio_chunks_view(self):
        """Create audio chunks view."""
        self.audio_chunks = pxt.create_view(
            self.audio_view_name,
            self.video_table,
            iterator=AudioSplitter.create(
                audio=self.video_table.audio_extract,
                chunk_duration_sec=settings.AUDIO_CHUNK_LENGTH,
                overlap_sec=settings.AUDIO_OVERLAP_SECONDS,
                min_chunk_duration_sec=settings.AUDIO_MIN_CHUNK_DURATION_SECONDS,
            ),
            if_exists="replace_force",
        )

    def _add_aws_audio_transcription(self):
        """Add AWS transcription."""
        logger.info("Setting up AWS audio transcription")
        self.audio_chunks.add_computed_column(
            transcription=aws_transcribe_audio(self.audio_chunks.audio_chunk),
            if_exists="ignore",
        )

    def _add_audio_text_extraction(self):
        """Add text extraction from transcription."""
        self.audio_chunks.add_computed_column(
            chunk_text=extract_text_from_chunk(self.audio_chunks.transcription),
            if_exists="ignore",
        )

    def _add_aws_audio_embedding_index(self):
        """Add AWS embeddings for audio."""
        logger.info("Setting up AWS audio embeddings")
        
        # Add embedding column
        self.audio_chunks.add_computed_column(
            chunk_embedding=aws_generate_embeddings(self.audio_chunks.chunk_text),
            if_exists="ignore",
        )
        
        # Add index on embeddings
        self.audio_chunks.add_embedding_index(
            column=self.audio_chunks.chunk_embedding,
            if_exists="ignore",
            idx_name="chunks_index",
        )

    def _setup_frame_processing(self):
        """Set up frame processing pipeline with AWS."""
        self._create_frames_view()
        self._add_frame_embedding_index()
        self._add_aws_frame_captioning()
        self._add_aws_caption_embedding_index()

    def _create_frames_view(self):
        """Create frames view."""
        self.frames_view = pxt.create_view(
            self.frames_view_name,
            self.video_table,
            iterator=FrameIterator.create(video=self.video_table.video, num_frames=settings.SPLIT_FRAMES_COUNT),
            if_exists="ignore",
        )
        self.frames_view.add_computed_column(
            resized_frame=resize_image(
                self.frames_view.frame,
                width=settings.IMAGE_RESIZE_WIDTH,
                height=settings.IMAGE_RESIZE_HEIGHT,
            )
        )

    def _add_frame_embedding_index(self):
        """Add frame embedding index using CLIP."""
        self.frames_view.add_embedding_index(
            column=self.frames_view.resized_frame,
            image_embed=clip.using(model_id=settings.IMAGE_SIMILARITY_EMBD_MODEL),
            if_exists="replace_force",
        )

    def _add_aws_frame_captioning(self):
        """Add AWS frame captioning."""
        logger.info("Setting up AWS frame captioning")
        self.frames_view.add_computed_column(
            im_caption=aws_caption_image(
                self.frames_view.resized_frame,
                settings.CAPTION_MODEL_PROMPT
            )
        )

    def _add_aws_caption_embedding_index(self):
        """Add AWS embeddings for captions."""
        logger.info("Setting up AWS caption embeddings")
        
        # Add embedding column
        self.frames_view.add_computed_column(
            caption_embedding=aws_generate_embeddings(self.frames_view.im_caption),
            if_exists="ignore",
        )
        
        # Add index on embeddings
        self.frames_view.add_embedding_index(
            column=self.frames_view.caption_embedding,
            if_exists="replace_force",
        )

    def add_video(self, video_path: str) -> bool:
        """Add a video to the pixel table."""
        if not self.video_table:
            raise ValueError("Video table is not initialized. Call setup_table() first.")
        
        logger.info(f"Adding video {video_path} to table {self.video_table_name}")

        new_video_path = re_encode_video(video_path=video_path)
        if new_video_path:
            self.video_table.insert([{"video": video_path}])
            logger.info("Video processing with AWS services completed successfully")
        return True