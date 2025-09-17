"""AWS-native VideoProcessor that bypasses Pixeltable's OpenAI functions."""

import asyncio
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import pixeltable as pxt
from loguru import logger
from pixeltable.functions.huggingface import clip
from pixeltable.functions.video import extract_audio
from pixeltable.iterators import AudioSplitter
from pixeltable.iterators.video import FrameIterator

import kubrick_mcp.video.ingestion.registry as registry
from kubrick_mcp.config import get_settings
from kubrick_mcp.providers.factory import AIProviderFactory
from kubrick_mcp.video.ingestion.functions import extract_text_from_chunk, resize_image
from kubrick_mcp.video.ingestion.tools import re_encode_video

if TYPE_CHECKING:
    from kubrick_mcp.video.ingestion.models import CachedTable

logger = logger.bind(name="AWSVideoProcessor")
settings = get_settings()


class AWSVideoProcessor:
    """VideoProcessor that uses AWS services instead of OpenAI."""
    
    def __init__(self):
        self._pxt_cache: Optional[str] = None
        self._video_table = None
        self._frames_view = None
        self._audio_chunks = None
        self._video_mapping_idx: Optional[str] = None
        self._provider_factory = AIProviderFactory()
        self._transcription_provider = None
        self._vision_provider = None
        self._embeddings_provider = None

        logger.info(
            "AWSVideoProcessor initialized",
            f"\n Split FPS: {settings.SPLIT_FRAMES_COUNT}",
            f"\n Audio Chunk: {settings.AUDIO_CHUNK_LENGTH} seconds",
            f"\n Using AWS providers only",
        )

    async def _get_providers(self):
        """Initialize AWS providers."""
        if self._transcription_provider is None:
            self._transcription_provider = await self._provider_factory.get_transcription_provider_with_fallback()
            self._vision_provider = await self._provider_factory.get_vision_provider_with_fallback()
            self._embeddings_provider = await self._provider_factory.get_embeddings_provider_with_fallback()
            
            logger.info(f"Transcription provider: {type(self._transcription_provider).__name__}")
            logger.info(f"Vision provider: {type(self._vision_provider).__name__}")
            logger.info(f"Embeddings provider: {type(self._embeddings_provider).__name__}")

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

            # Initialize providers before setting up table
            asyncio.run(self._get_providers())
            
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
        """Set up audio processing pipeline."""
        self._add_audio_extraction()
        self._create_audio_chunks_view()
        # Skip transcription for now - we'll handle it differently
        self._add_audio_text_extraction()

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

    def _add_audio_text_extraction(self):
        """Add text extraction from transcription."""
        # For now, create empty columns that we'll populate later
        self.audio_chunks.add_computed_column(
            transcription=pxt.String,
            if_exists="ignore",
        )
        self.audio_chunks.add_computed_column(
            chunk_text=pxt.String,
            if_exists="ignore",
        )

    def _setup_frame_processing(self):
        """Set up frame processing pipeline."""
        self._create_frames_view()
        self._add_frame_embedding_index()
        # Skip captioning for now - we'll handle it differently

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

    def add_video(self, video_path: str) -> bool:
        """Add a video to the pixel table."""
        if not self.video_table:
            raise ValueError("Video table is not initialized. Call setup_table() first.")
        
        logger.info(f"Adding video {video_path} to table {self.video_table_name}")

        new_video_path = re_encode_video(video_path=video_path)
        if new_video_path:
            self.video_table.insert([{"video": video_path}])
            
            # Now process with AWS providers
            logger.info("Processing video with AWS providers...")
            asyncio.run(self._process_with_aws_providers())
            
        return True

    async def _process_with_aws_providers(self):
        """Process audio and video using AWS providers."""
        try:
            await self._process_audio_transcription()
            await self._process_frame_captioning()
            logger.info("AWS processing completed successfully")
        except Exception as e:
            logger.error(f"AWS processing failed: {e}")
            raise

    async def _process_audio_transcription(self):
        """Process audio transcription using AWS Transcribe."""
        logger.info("Processing audio transcription with AWS...")
        
        # Get audio chunks that need transcription
        audio_rows = list(self.audio_chunks.select())
        
        for row in audio_rows:
            try:
                # Get audio data
                audio_data = row['audio_chunk']
                
                # Transcribe using AWS
                transcription = await self._transcription_provider.transcribe_audio(audio_data)
                
                # Extract text
                chunk_text = transcription if transcription else ""
                
                # Update the row
                self.audio_chunks.update(
                    where=self.audio_chunks.id == row['id'],
                    values={
                        'transcription': transcription,
                        'chunk_text': chunk_text
                    }
                )
                
                logger.info(f"Transcribed audio chunk {row['id']}: {chunk_text[:50]}...")
                
            except Exception as e:
                logger.error(f"Failed to transcribe audio chunk {row['id']}: {e}")

    async def _process_frame_captioning(self):
        """Process frame captioning using AWS Bedrock."""
        logger.info("Processing frame captioning with AWS...")
        
        # Add caption column if it doesn't exist
        try:
            self.frames_view.add_computed_column(
                im_caption=pxt.String,
                if_exists="ignore",
            )
        except:
            pass
        
        # Get frames that need captioning
        frame_rows = list(self.frames_view.select())
        
        for row in frame_rows:
            try:
                # Get image data
                image_data = row['resized_frame']
                
                # Generate caption using AWS
                caption = await self._vision_provider.analyze_image(
                    image_data, 
                    settings.CAPTION_MODEL_PROMPT
                )
                
                # Update the row
                self.frames_view.update(
                    where=self.frames_view.id == row['id'],
                    values={'im_caption': caption}
                )
                
                logger.info(f"Captioned frame {row['id']}: {caption[:50]}...")
                
            except Exception as e:
                logger.error(f"Failed to caption frame {row['id']}: {e}")


# Create a function to replace the original VideoProcessor
def create_video_processor():
    """Create the appropriate video processor based on configuration."""
    openai_available = bool(getattr(settings, 'OPENAI_API_KEY', None))
    
    if openai_available:
        # Use original VideoProcessor if OpenAI is available
        from kubrick_mcp.video.ingestion.video_processor import VideoProcessor
        logger.info("Using original VideoProcessor with OpenAI")
        return VideoProcessor()
    else:
        # Use AWS VideoProcessor if no OpenAI
        logger.info("Using AWSVideoProcessor with AWS services")
        return AWSVideoProcessor()