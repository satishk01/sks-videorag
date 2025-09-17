# AWS-Only Deployment Instructions

## Quick Fix for EC2 Deployment

Since you're building on EC2, here are the exact steps to fix the Groq/OpenAI issues:

### Step 1: Upload the Fix Script

Upload the `fix-aws-only-deployment.sh` script to your EC2 instance and run:

```bash
chmod +x fix-aws-only-deployment.sh
./fix-aws-only-deployment.sh
```

### Step 2: Manual Configuration (Alternative)

If you prefer to do it manually, make these changes on your EC2 instance:

#### 2.1 Copy Environment Files
```bash
cp kubrick-api/.env.aws-only kubrick-api/.env
cp kubrick-mcp/.env.aws-only kubrick-mcp/.env
```

#### 2.2 Update API Configuration
Edit `kubrick-api/src/kubrick_api/config.py`:
- Change `env_file="agent-api/.env"` to `env_file=".env"`
- Change `AGENT_PROVIDER: str = "groq"` to `AGENT_PROVIDER: str = "bedrock"`

#### 2.3 Update MCP Configuration  
Edit `kubrick-mcp/src/kubrick_mcp/config.py`:
- Change `env_file="kubrick-mcp/.env"` to `env_file=".env"`
- Change `VISION_PROVIDER: str = "openai"` to `VISION_PROVIDER: str = "bedrock"`
- Change `EMBEDDINGS_PROVIDER: str = "openai"` to `EMBEDDINGS_PROVIDER: str = "bedrock"`
- Change `OPIK_API_KEY: str` to `OPIK_API_KEY: Optional[str] = None`

#### 2.4 Update API Startup Logic
Edit `kubrick-api/src/kubrick_api/api.py`:

1. Update imports:
```python
from kubrick_api.agent import GroqAgent, BedrockAgent
```

2. Replace the lifespan function:
```python
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
```

#### 2.5 Update Agent Exports
Edit `kubrick-api/src/kubrick_api/agent/__init__.py`:
```python
from .groq.groq_agent import GroqAgent
from .bedrock.bedrock_agent import BedrockAgent
from .memory import Memory, MemoryRecord

__all__ = ["GroqAgent", "BedrockAgent", "Memory", "MemoryRecord"]
```

### Step 3: Configure AWS Credentials

Edit both `.env` files and update:
```bash
AWS_ACCESS_KEY_ID=your_actual_access_key
AWS_SECRET_ACCESS_KEY=your_actual_secret_key
AWS_REGION=us-east-1
```

### Step 4: Build and Deploy

```bash
# Stop existing containers
docker-compose down

# Build with no cache to ensure changes are applied
docker-compose build --no-cache

# Start the services
docker-compose up
```

### Expected Output

You should see logs like:
```
AGENT_PROVIDER setting: bedrock
Initializing BedrockAgent
Chat provider initialized: bedrock
Vision provider initialized: bedrock
Embeddings provider initialized: bedrock
Using AWS Transcribe for transcription (no OpenAI key)
```

### Troubleshooting

If you still see Groq errors:
1. Ensure the `.env` files are in the correct locations
2. Verify the configuration changes were applied
3. Make sure you built with `--no-cache`
4. Check that your AWS credentials are valid

## Key Changes Made

✅ **Fixed Configuration Paths**: Corrected env_file paths in both services
✅ **Set Bedrock as Default**: Changed default provider to Bedrock
✅ **Updated API Logic**: Added conditional agent selection
✅ **Made Keys Optional**: OpenAI/Groq keys are now optional
✅ **AWS-Only Environment**: Created complete AWS-only configuration

The system will now use **only AWS services** without any OpenAI or Groq dependencies!