"""AWS Bedrock provider implementations."""

import json
from typing import Dict, List, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from loguru import logger

from .base import ChatProvider, ChatResponse, ProviderError, ProviderUnavailableError


class BedrockError(ProviderError):
    """Bedrock-specific errors."""
    pass


class BedrockChatProvider(ChatProvider):
    """AWS Bedrock provider for conversational AI operations."""
    
    def __init__(self, region: str = "us-east-1", model_id: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"):
        self.region = region
        self.model_id = model_id
        self.client = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the Bedrock client."""
        try:
            self.client = boto3.client("bedrock-runtime", region_name=self.region)
            self._initialized = True
            logger.info(f"Bedrock chat provider initialized with model {self.model_id}")
        except (ClientError, NoCredentialsError) as e:
            logger.error(f"Failed to initialize Bedrock chat provider: {e}")
            raise BedrockError("bedrock", f"Failed to initialize: {str(e)}", e)
    
    def is_available(self) -> bool:
        """Check if the provider is available."""
        return self.client is not None and self._initialized
    
    async def chat_completion(self, messages: List[Dict], model: str, **kwargs) -> ChatResponse:
        """Generate chat completion using Claude."""
        if not self.is_available():
            raise ProviderUnavailableError("bedrock", "Provider not initialized")
        
        try:
            # Convert messages to Claude format
            claude_messages = self._convert_messages_to_claude_format(messages)
            
            # Extract inference configuration
            max_tokens = kwargs.get("max_completion_tokens", 4096)
            temperature = kwargs.get("temperature", 0.7)
            top_p = kwargs.get("top_p", 0.9)
            
            # Call Bedrock Converse API
            response = self.client.converse(
                modelId=self.model_id,
                messages=claude_messages,
                inferenceConfig={
                    "maxTokens": max_tokens,
                    "temperature": temperature,
                    "topP": top_p
                }
            )
            
            # Extract the response
            message_content = response["output"]["message"]["content"][0]["text"]
            usage_info = response.get("usage", {})
            
            return ChatResponse(
                message=message_content,
                usage=usage_info,
                provider="bedrock"
            )
            
        except ClientError as e:
            logger.error(f"Bedrock chat API error: {e}")
            raise BedrockError("bedrock", f"Chat API error: {str(e)}", e)
        except Exception as e:
            logger.error(f"Unexpected error in Bedrock chat provider: {e}")
            raise BedrockError("bedrock", f"Unexpected error: {str(e)}", e)
    
    def _convert_messages_to_claude_format(self, messages: List[Dict]) -> List[Dict]:
        """Convert messages to Claude format."""
        claude_messages = []
        
        for message in messages:
            role = message.get("role")
            content = message.get("content")
            
            # Skip system messages as they should be handled separately
            if role == "system":
                continue
            
            # Handle different content types
            if isinstance(content, str):
                claude_content = [{"type": "text", "text": content}]
            elif isinstance(content, list):
                claude_content = []
                for item in content:
                    if item.get("type") == "text":
                        claude_content.append({"type": "text", "text": item["text"]})
                    elif item.get("type") == "image_url":
                        # Handle image content
                        image_url = item["image_url"]["url"]
                        if image_url.startswith("data:image"):
                            # Extract base64 data
                            media_type, data = image_url.split(",", 1)
                            media_type = media_type.split(";")[0].split(":")[1]
                            claude_content.append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": data
                                }
                            })
            else:
                claude_content = [{"type": "text", "text": str(content)}]
            
            claude_messages.append({
                "role": role,
                "content": claude_content
            })
        
        return claude_messages