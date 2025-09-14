"""Groq provider implementations."""

from typing import Dict, List, Optional

from groq import Groq
from loguru import logger

from .base import ChatProvider, ChatResponse, ProviderError, ProviderUnavailableError


class GroqError(ProviderError):
    """Groq-specific errors."""
    pass


class GroqChatProvider(ChatProvider):
    """Groq provider for conversational AI operations."""
    
    def __init__(self, api_key: str, model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"):
        self.api_key = api_key
        self.model = model
        self.client = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the Groq client."""
        try:
            self.client = Groq(api_key=self.api_key)
            self._initialized = True
            logger.info(f"Groq chat provider initialized with model {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize Groq chat provider: {e}")
            raise GroqError("groq", f"Failed to initialize: {str(e)}", e)
    
    def is_available(self) -> bool:
        """Check if the provider is available."""
        return self.client is not None and self._initialized
    
    async def chat_completion(self, messages: List[Dict], model: str, **kwargs) -> ChatResponse:
        """Generate chat completion using Groq."""
        if not self.is_available():
            raise ProviderUnavailableError("groq", "Provider not initialized")
        
        try:
            # Extract parameters
            max_tokens = kwargs.get("max_completion_tokens", 4096)
            temperature = kwargs.get("temperature", 0.7)
            tools = kwargs.get("tools")
            tool_choice = kwargs.get("tool_choice", "auto")
            
            # Prepare the request
            request_params = {
                "model": model or self.model,
                "messages": messages,
                "max_completion_tokens": max_tokens,
                "temperature": temperature,
            }
            
            if tools:
                request_params["tools"] = tools
                request_params["tool_choice"] = tool_choice
            
            # Call Groq API
            response = self.client.chat.completions.create(**request_params)
            
            # Extract the response
            message = response.choices[0].message
            usage_info = response.usage.model_dump() if response.usage else {}
            
            # Handle tool calls if present
            if hasattr(message, 'tool_calls') and message.tool_calls:
                # Return the message with tool calls for further processing
                return ChatResponse(
                    message=message,  # Return the full message object for tool handling
                    usage=usage_info,
                    provider="groq"
                )
            else:
                return ChatResponse(
                    message=message.content,
                    usage=usage_info,
                    provider="groq"
                )
            
        except Exception as e:
            logger.error(f"Groq chat API error: {e}")
            raise GroqError("groq", f"Chat API error: {str(e)}", e)