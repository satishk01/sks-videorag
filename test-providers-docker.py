#!/usr/bin/env python3
"""Simple test to run inside Docker container to verify AWS providers."""

import asyncio
import sys
import os

async def test_providers():
    """Test AWS providers inside Docker container."""
    print("🧪 Testing AWS Providers (Docker)...")
    
    try:
        from kubrick_mcp.providers.factory import AIProviderFactory
        from kubrick_mcp.config import get_settings
        
        settings = get_settings()
        factory = AIProviderFactory(settings)
        
        print(f"Configuration:")
        print(f"  VISION_PROVIDER: {settings.VISION_PROVIDER}")
        print(f"  EMBEDDINGS_PROVIDER: {settings.EMBEDDINGS_PROVIDER}")
        print(f"  AWS_REGION: {settings.AWS_REGION}")
        print(f"  OPENAI_API_KEY: {'Set' if getattr(settings, 'OPENAI_API_KEY', None) else 'Not set'}")
        print()
        
        # Test transcription provider
        try:
            print("🎵 Testing Transcription Provider...")
            transcription_provider = await factory.get_transcription_provider_with_fallback()
            print(f"  ✅ Transcription provider: {type(transcription_provider).__name__}")
            print(f"  ✅ Available: {transcription_provider.is_available()}")
        except Exception as e:
            print(f"  ❌ Transcription provider error: {e}")
        
        # Test vision provider
        try:
            print("👁️  Testing Vision Provider...")
            vision_provider = await factory.get_vision_provider_with_fallback()
            print(f"  ✅ Vision provider: {type(vision_provider).__name__}")
            print(f"  ✅ Available: {vision_provider.is_available()}")
        except Exception as e:
            print(f"  ❌ Vision provider error: {e}")
        
        # Test embeddings provider
        try:
            print("🔢 Testing Embeddings Provider...")
            embeddings_provider = await factory.get_embeddings_provider_with_fallback()
            print(f"  ✅ Embeddings provider: {type(embeddings_provider).__name__}")
            print(f"  ✅ Available: {embeddings_provider.is_available()}")
        except Exception as e:
            print(f"  ❌ Embeddings provider error: {e}")
        
        print("\n🎯 Provider Test Complete!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("This test should be run inside the Docker container.")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(test_providers())