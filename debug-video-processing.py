#!/usr/bin/env python3
"""Debug script to check video processing configuration."""

import sys
import os

# Add path for imports
sys.path.insert(0, '/app/src')

def check_video_processor():
    """Check VideoProcessor configuration and imports."""
    print("🔍 Debugging Video Processing...")
    
    try:
        from kubrick_mcp.config import get_settings
        settings = get_settings()
        
        print(f"Configuration:")
        print(f"  VISION_PROVIDER: {settings.VISION_PROVIDER}")
        print(f"  EMBEDDINGS_PROVIDER: {settings.EMBEDDINGS_PROVIDER}")
        print(f"  OPENAI_API_KEY: {'Set' if getattr(settings, 'OPENAI_API_KEY', None) else 'Not set'}")
        print(f"  AWS_REGION: {settings.AWS_REGION}")
        print(f"  AWS_ACCESS_KEY_ID: {'Set' if getattr(settings, 'AWS_ACCESS_KEY_ID', None) else 'Not set'}")
        print()
        
        # Check if AWS functions can be imported
        try:
            from kubrick_mcp.video.ingestion.aws_functions import aws_transcribe, aws_vision, aws_embeddings
            print("✅ AWS functions imported successfully")
        except Exception as e:
            print(f"❌ AWS functions import error: {e}")
        
        # Check provider factory
        try:
            from kubrick_mcp.providers.factory import AIProviderFactory
            factory = AIProviderFactory(settings)
            print("✅ Provider factory created successfully")
        except Exception as e:
            print(f"❌ Provider factory error: {e}")
        
        # Check VideoProcessor
        try:
            from kubrick_mcp.video.ingestion.video_processor import VideoProcessor
            processor = VideoProcessor()
            print("✅ VideoProcessor created successfully")
            print(f"  Has provider factory: {hasattr(processor, '_provider_factory')}")
        except Exception as e:
            print(f"❌ VideoProcessor error: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"❌ General error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_video_processor()