"""AWS Bedrock provider implementations."""

import base64
import json
from typing import Dict, List, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from loguru import logger

from .base import (
    EmbeddingsProvider,
    EmbeddingsResponse,
    ProviderError,
    ProviderUnavailableError,
    VisionProvider,
    VisionResponse,
)


class BedrockError(ProviderError):
    """Bedrock-specific errors."""
    pass


class BedrockVisionProvider(VisionProvider):
    """AWS Bedrock provider for vision/image captioning operations."""
    
    def __init__(self, region: str = "us-east-1", model_id: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"):
        self.region = region
        self.model_id = model_id
        self.client = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the Bedrock client."""
        try:
            self.client = boto3.client("bedrock-runtime", region_name=self.region)
            # Test the connection with a simple call
            self.client.list_foundation_models = boto3.client("bedrock", region_name=self.region).list_foundation_models
            self._initialized = True
            logger.info(f"Bedrock vision provider initialized with model {self.model_id}")
        except (ClientError, NoCredentialsError) as e:
            logger.error(f"Failed to initialize Bedrock vision provider: {e}")
            raise BedrockError("bedrock", f"Failed to initialize: {str(e)}", e)
    
    def is_available(self) -> bool:
        """Check if the provider is available."""
        return self.client is not None and self._initialized
    
    async def generate_caption(self, image: bytes, prompt: str) -> VisionResponse:
        """Generate caption for an image using Claude."""
        if not self.is_available():
            raise ProviderUnavailableError("bedrock", "Provider not initialized")
        
        try:
            # Encode image to base64
            image_base64 = base64.b64encode(image).decode('utf-8')
            
            # Prepare the message for Claude
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
            
            # Call Bedrock Converse API
            response = self.client.converse(
                modelId=self.model_id,
                messages=messages,
                inferenceConfig={
                    "maxTokens": 1000,
                    "temperature": 0.7
                }
            )
            
            # Extract the response text
            caption = response["output"]["message"]["content"][0]["text"]
            
            return VisionResponse(
                caption=caption,
                provider="bedrock"
            )
            
        except ClientError as e:
            logger.error(f"Bedrock vision API error: {e}")
            raise BedrockError("bedrock", f"Vision API error: {str(e)}", e)
        except Exception as e:
            logger.error(f"Unexpected error in Bedrock vision provider: {e}")
            raise BedrockError("bedrock", f"Unexpected error: {str(e)}", e)


class BedrockEmbeddingsProvider(EmbeddingsProvider):
    """AWS Bedrock provider for text embeddings operations."""
    
    def __init__(self, region: str = "us-east-1", model_id: str = "amazon.titan-embed-text-v1"):
        self.region = region
        self.model_id = model_id
        self.client = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the Bedrock client."""
        try:
            self.client = boto3.client("bedrock-runtime", region_name=self.region)
            self._initialized = True
            logger.info(f"Bedrock embeddings provider initialized with model {self.model_id}")
        except (ClientError, NoCredentialsError) as e:
            logger.error(f"Failed to initialize Bedrock embeddings provider: {e}")
            raise BedrockError("bedrock", f"Failed to initialize: {str(e)}", e)
    
    def is_available(self) -> bool:
        """Check if the provider is available."""
        return self.client is not None and self._initialized
    
    async def generate_embeddings(self, text: str, model: str) -> EmbeddingsResponse:
        """Generate embeddings for text using Titan."""
        if not self.is_available():
            raise ProviderUnavailableError("bedrock", "Provider not initialized")
        
        try:
            # Prepare the request body for Titan embeddings
            body = json.dumps({
                "inputText": text
            })
            
            # Call Bedrock InvokeModel API
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=body,
                contentType="application/json",
                accept="application/json"
            )
            
            # Parse the response
            response_body = json.loads(response["body"].read())
            embeddings = response_body["embedding"]
            
            return EmbeddingsResponse(
                embeddings=embeddings,
                model=self.model_id,
                provider="bedrock"
            )
            
        except ClientError as e:
            logger.error(f"Bedrock embeddings API error: {e}")
            raise BedrockError("bedrock", f"Embeddings API error: {str(e)}", e)
        except Exception as e:
            logger.error(f"Unexpected error in Bedrock embeddings provider: {e}")
            raise BedrockError("bedrock", f"Unexpected error: {str(e)}", e)