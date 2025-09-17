#!/usr/bin/env python3
"""Test the AWS patch for video processing."""

import sys
import os

# Add path for imports
sys.path.insert(0, '/app/src')

def test_aws_patch():
    """Test AWS patch functionality."""
    print("🧪 Testing AWS Patch...")
    
    try:
        from kubrick_mcp.config import get_settings
        settings = get_settings()
        
        print(f"Configuration:")
        print(f"  OPENAI_API_KEY: {'Set' if getattr(settings, 'OPENAI_API_KEY', None) else 'Not set'}")
        print(f"  AWS_REGION: {settings.AWS_REGION}")
        print(f"  VISION_PROVIDER: {settings.VISION_PROVIDER}")
        print(f"  EMBEDDINGS_PROVIDER: {settings.EMBEDDINGS_PROVIDER}")
        print()
        
        # Test the patch
        from kubrick_mcp.video.ingestion.aws_patch import patch_video_processor
        patch_video_processor()
        print("✅ AWS patch applied successfully")
        
        # Test VideoProcessor creation
        from kubrick_mcp.video.ingestion.video_processor import VideoProcessor
        processor = VideoProcessor()
        print("✅ VideoProcessor created successfully")
        
        # Test AWS functions directly
        from kubrick_mcp.video.ingestion.aws_patch import aws_transcribe_function, aws_vision_function
        
        print("🎵 Testing transcription function...")
        # Test with dummy data
        result = aws_transcribe_function(b"dummy audio data")
        print(f"  Transcription test: {'✅ Success' if isinstance(result, str) else '❌ Failed'}")
        
        print("👁️  Testing vision function...")
        # Test with dummy data
        result = aws_vision_function(b"dummy image data", "Describe this image")
        print(f"  Vision test: {'✅ Success' if isinstance(result, str) else '❌ Failed'}")
        
        print("\n🎯 AWS Patch Test Complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_aws_patch()