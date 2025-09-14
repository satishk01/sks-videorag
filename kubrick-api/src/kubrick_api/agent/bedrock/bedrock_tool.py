"""Tool transformation utilities for Bedrock."""

from typing import Any, Dict, Optional
from pydantic import BaseModel


class BedrockParameter(BaseModel):
    """Represents a parameter in a Bedrock tool definition."""
    type: str
    description: str
    default: Optional[Any] = None


class BedrockToolSpec(BaseModel):
    """Represents a tool specification for Bedrock."""
    name: str
    description: str
    input_schema: Dict[str, Any]


def transform_tool_definition(tool) -> dict:
    """Transform an MCP tool into a Bedrock tool definition dictionary."""
    
    # Extract properties from the MCP tool schema
    properties = {}
    for field_name, field_info in tool.inputSchema["properties"].items():
        properties[field_name] = {
            "type": field_info["type"],
            "description": field_info.get("title", field_info.get("description", "")),
        }
        if "default" in field_info:
            properties[field_name]["default"] = field_info["default"]
    
    # Create the Bedrock tool specification
    bedrock_tool = {
        "toolSpec": {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": properties,
                    "required": tool.inputSchema.get("required", [])
                }
            }
        }
    }
    
    return bedrock_tool