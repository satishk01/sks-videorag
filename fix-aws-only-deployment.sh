#!/bin/bash

echo "🔧 Fixing Kubrick for AWS-only deployment..."

# Stop any running containers
echo "Stopping containers..."
docker-compose down

# Copy AWS-only environment files
echo "Setting up AWS-only environment files..."
cp kubrick-api/.env.aws-only kubrick-api/.env
cp kubrick-mcp/.env.aws-only kubrick-mcp/.env

# Fix API configuration file
echo "Fixing API configuration..."
sed -i 's/env_file="agent-api\/.env"/env_file=".env"/' kubrick-api/src/kubrick_api/config.py
sed -i 's/AGENT_PROVIDER: str = "groq"/AGENT_PROVIDER: str = "bedrock"/' kubrick-api/src/kubrick_api/config.py

# Fix MCP configuration file  
echo "Fixing MCP configuration..."
sed -i 's/env_file="kubrick-mcp\/.env"/env_file=".env"/' kubrick-mcp/src/kubrick_mcp/config.py
sed -i 's/VISION_PROVIDER: str = "openai"/VISION_PROVIDER: str = "bedrock"/' kubrick-mcp/src/kubrick_mcp/config.py
sed -i 's/TRANSCRIPTION_PROVIDER: str = "openai"/TRANSCRIPTION_PROVIDER: str = "bedrock"/' kubrick-mcp/src/kubrick_mcp/config.py
sed -i 's/EMBEDDINGS_PROVIDER: str = "openai"/EMBEDDINGS_PROVIDER: str = "bedrock"/' kubrick-mcp/src/kubrick_mcp/config.py
sed -i 's/OPIK_API_KEY: str$/OPIK_API_KEY: Optional[str] = None/' kubrick-mcp/src/kubrick_mcp/config.py

# Update API startup logic
echo "Updating API startup logic..."
cat > /tmp/api_lifespan.py << 'EOF'
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Debug: Print configuration
    logger.info(f"AGENT_PROVIDER setting: {settings.AGENT_PROVIDER}")
    
    # Select agent based on configuration
    if settings.AGENT_PROVIDER.lower() == "bedrock":
        logger.info("Initializing BedrockAgent")
        app.state.agent = BedrockAgent(
            name="kubrick",
            mcp_server=settings.MCP_SERVER,
            disable_tools=["process_video"],
        )
    else:
        logger.info("Initializing GroqAgent")
        app.state.agent = GroqAgent(
            name="kubrick",
            mcp_server=settings.MCP_SERVER,
            disable_tools=["process_video"],
        )
    
    app.state.bg_task_states = dict()
    yield
    app.state.agent.reset_memory()
EOF

# Replace the lifespan function in api.py
python3 << 'EOF'
import re

# Read the API file
with open('kubrick-api/src/kubrick_api/api.py', 'r') as f:
    content = f.read()

# Update imports
content = re.sub(
    r'from kubrick_api\.agent import GroqAgent',
    'from kubrick_api.agent import GroqAgent, BedrockAgent',
    content
)

# Update lifespan function
lifespan_pattern = r'@asynccontextmanager\s*\nasync def lifespan\(app: FastAPI\):.*?app\.state\.agent\.reset_memory\(\)'
new_lifespan = '''@asynccontextmanager
async def lifespan(app: FastAPI):
    # Debug: Print configuration
    logger.info(f"AGENT_PROVIDER setting: {settings.AGENT_PROVIDER}")
    
    # Select agent based on configuration
    if settings.AGENT_PROVIDER.lower() == "bedrock":
        logger.info("Initializing BedrockAgent")
        app.state.agent = BedrockAgent(
            name="kubrick",
            mcp_server=settings.MCP_SERVER,
            disable_tools=["process_video"],
        )
    else:
        logger.info("Initializing GroqAgent")
        app.state.agent = GroqAgent(
            name="kubrick",
            mcp_server=settings.MCP_SERVER,
            disable_tools=["process_video"],
        )
    
    app.state.bg_task_states = dict()
    yield
    app.state.agent.reset_memory()'''

content = re.sub(lifespan_pattern, new_lifespan, content, flags=re.DOTALL)

# Write back
with open('kubrick-api/src/kubrick_api/api.py', 'w') as f:
    f.write(content)
EOF

# Update agent __init__.py to export BedrockAgent
echo "Updating agent exports..."
cat > kubrick-api/src/kubrick_api/agent/__init__.py << 'EOF'
from .groq.groq_agent import GroqAgent
from .bedrock.bedrock_agent import BedrockAgent
from .memory import Memory, MemoryRecord

__all__ = ["GroqAgent", "BedrockAgent", "Memory", "MemoryRecord"]
EOF

echo "✅ AWS-only configuration applied!"
echo ""
echo "Next steps:"
echo "1. Update your AWS credentials in both .env files:"
echo "   - kubrick-api/.env"
echo "   - kubrick-mcp/.env"
echo ""
echo "2. Build and start the containers:"
echo "   docker-compose build --no-cache"
echo "   docker-compose up"
echo ""
echo "The system will now use only AWS Bedrock and AWS Transcribe!"