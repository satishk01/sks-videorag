"""Bedrock agent implementation using AWS Bedrock Claude models."""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import instructor
import opik
from loguru import logger
from opik import Attachment, opik_context

from kubrick_api import tools
from kubrick_api.agent.base_agent import BaseAgent
from kubrick_api.agent.bedrock.bedrock_tool import transform_tool_definition
from kubrick_api.agent.memory import Memory, MemoryRecord
from kubrick_api.config import get_settings
from kubrick_api.models import (
    AssistantMessageResponse,
    GeneralResponseModel,
    RoutingResponseModel,
    VideoClipResponseModel,
)
from kubrick_api.providers.factory import AgentProviderFactory

logger.bind(name="BedrockAgent")

settings = get_settings()


class BedrockAgent(BaseAgent):
    """Bedrock-powered agent using Claude models."""
    
    def __init__(
        self,
        name: str,
        mcp_server: str,
        memory: Optional[Memory] = None,
        disable_tools: list = None,
    ):
        super().__init__(
            name,
            mcp_server,
            memory,
            disable_tools,
        )
        self.provider_factory = AgentProviderFactory()
        self.chat_provider = None
        self.thread_id = str(uuid.uuid4())

    async def setup(self):
        """Initialize async components of the agent."""
        await super().setup()
        self.chat_provider = await self.provider_factory.get_chat_provider_with_fallback()

    async def _get_tools(self) -> List[Dict[str, Any]]:
        """Get tools transformed for Bedrock format."""
        tools = await self.discover_tools()
        return [transform_tool_definition(tool) for tool in tools]

    @opik.track(name="build-chat-history")
    def _build_chat_history(
        self,
        system_prompt: str,
        user_message: str,
        image_base64: Optional[str] = None,
        n: int = settings.AGENT_MEMORY_SIZE,
    ) -> List[Dict[str, Any]]:
        """Build chat history for Bedrock."""
        history = []
        
        # Add memory
        memory_records = self.memory.get_latest(n)
        for record in memory_records:
            history.append({"role": record.role, "content": record.content})

        # Add current user message
        user_content = []
        if image_base64:
            user_content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_base64
                }
            })
        user_content.append({"type": "text", "text": user_message})
        
        history.append({"role": "user", "content": user_content})
        return history

    @opik.track(name="router", type="llm")
    def _should_use_tool(self, message: str) -> bool:
        """Determine if tools should be used."""
        # For Bedrock, we'll use a simple heuristic for now
        # In a full implementation, this would use a routing model
        tool_keywords = ["video", "clip", "search", "find", "show", "extract", "process"]
        return any(keyword in message.lower() for keyword in tool_keywords)

    def validate_video_clip_response(self, video_clip_response: VideoClipResponseModel, video_clip_path: str) -> VideoClipResponseModel:
        """Validate the video clip response."""
        video_clip_response.clip_path = video_clip_path
        return video_clip_response

    async def _execute_tool_call(self, tool_call: Dict, video_path: str, image_base64: str | None = None) -> str:
        """Execute a single tool call and return its response."""
        function_name = tool_call["name"]
        function_args = tool_call.get("input", {})

        function_args["video_path"] = video_path

        if function_name == "get_video_clip_from_image":
            function_args["user_image"] = image_base64

        logger.info(f"Executing tool: {function_name}")

        try:
            return await self.call_tool(function_name, function_args)
        except Exception as e:
            logger.error(f"Error executing tool {function_name}: {str(e)}")
            return f"Error executing tool {function_name}: {str(e)}"

    @opik.track(name="tool-use", type="tool")
    async def _run_with_tool(self, message: str, video_path: str, image_base64: str | None = None) -> str:
        """Execute chat completion with tool usage."""
        tool_use_system_prompt = self.tool_use_system_prompt.format(
            is_image_provided=bool(image_base64),
        )
        
        # For Bedrock, we need to handle tools differently
        # This is a simplified implementation
        chat_history = self._build_chat_history(tool_use_system_prompt, message)
        
        # Add system prompt as the first message
        messages = [{"role": "system", "content": tool_use_system_prompt}] + chat_history
        
        try:
            response = await self.chat_provider.chat_completion(
                messages=messages,
                model=settings.BEDROCK_CLAUDE_MODEL,
                max_completion_tokens=4096
            )
            
            # For now, return a general response
            # In a full implementation, this would handle tool calling
            return GeneralResponseModel(message=response.message)
            
        except Exception as e:
            logger.error(f"Error in Bedrock tool use: {e}")
            return GeneralResponseModel(message=f"Error: {str(e)}")

    @opik.track(name="generate-response", type="llm")
    async def _respond_general(self, message: str) -> GeneralResponseModel:
        """Generate a general response."""
        chat_history = self._build_chat_history(self.general_system_prompt, message)
        messages = [{"role": "system", "content": self.general_system_prompt}] + chat_history
        
        try:
            response = await self.chat_provider.chat_completion(
                messages=messages,
                model=settings.BEDROCK_CLAUDE_MODEL
            )
            
            return GeneralResponseModel(message=response.message)
            
        except Exception as e:
            logger.error(f"Error in Bedrock general response: {e}")
            return GeneralResponseModel(message=f"Error: {str(e)}")

    def _add_to_memory(self, role: str, content: str) -> None:
        """Add a message to the agent's memory."""
        self.memory.insert(
            MemoryRecord(
                message_id=str(uuid.uuid4()),
                role=role,
                content=content,
                timestamp=datetime.now(),
            )
        )

    @opik.track(name="memory-insertion", type="general")
    def _add_memory_pair(self, user_message: str, assistant_message: str) -> None:
        """Add user-assistant message pair to memory."""
        self._add_to_memory("user", user_message)
        self._add_to_memory("assistant", assistant_message)

    @opik.track(name="chat", type="general")
    async def chat(
        self,
        message: str,
        video_path: Optional[str] = None,
        image_base64: Optional[str] = None,
    ) -> AssistantMessageResponse:
        """Main entry point for processing a user message."""
        opik_context.update_current_trace(thread_id=self.thread_id)

        tool_required = video_path and self._should_use_tool(message)
        logger.info(f"Tool required: {tool_required}")

        if tool_required:
            logger.info("Running tool response")
            response = await self._run_with_tool(message, video_path, image_base64)
        else:
            logger.info("Running general response")
            response = await self._respond_general(message)

        self._add_memory_pair(message, response.message)

        return AssistantMessageResponse(**response.dict())