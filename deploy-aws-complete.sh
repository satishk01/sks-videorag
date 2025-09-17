#!/bin/bash

echo "🚀 Complete AWS-Only Deployment for Kubrick..."

# Stop any running containers
echo "Stopping existing containers..."
docker-compose -f docker-compose.ec2.yml down 2>/dev/null || true
docker-compose down 2>/dev/null || true

# Set up AWS-only environment files
echo "Setting up AWS-only environment files..."
if [ ! -f "kubrick-api/.env" ]; then
    cp kubrick-api/.env.aws-only kubrick-api/.env
    echo "Created kubrick-api/.env from aws-only template"
fi

if [ ! -f "kubrick-mcp/.env" ]; then
    cp kubrick-mcp/.env.aws-only kubrick-mcp/.env
    echo "Created kubrick-mcp/.env from aws-only template"
fi

# Ensure no OpenAI key is set (force AWS-only mode)
echo "Ensuring AWS-only configuration..."
sed -i '/OPENAI_API_KEY=/d' kubrick-mcp/.env 2>/dev/null || true
echo "# OPENAI_API_KEY not set - using AWS services only" >> kubrick-mcp/.env

# Check AWS credentials
echo "Checking AWS credentials..."
if grep -q "your_aws_access_key_here" kubrick-api/.env; then
    echo "⚠️  WARNING: Please update AWS credentials in kubrick-api/.env"
    echo "   AWS_ACCESS_KEY_ID=your_actual_access_key"
    echo "   AWS_SECRET_ACCESS_KEY=your_actual_secret_key"
fi

if grep -q "your_aws_access_key_here" kubrick-mcp/.env; then
    echo "⚠️  WARNING: Please update AWS credentials in kubrick-mcp/.env"
    echo "   AWS_ACCESS_KEY_ID=your_actual_access_key"
    echo "   AWS_SECRET_ACCESS_KEY=your_actual_secret_key"
fi

# Build containers using AWS-specific configuration
echo "Building containers with AWS dependencies (this may take 5-10 minutes)..."
docker-compose -f docker-compose.aws.yml build --no-cache

# Start containers
echo "Starting AWS-enabled containers..."
docker-compose -f docker-compose.aws.yml up -d

# Wait for containers to start
echo "Waiting for containers to initialize..."
sleep 20

# Test boto3 availability
echo "Testing AWS dependencies..."
if docker-compose -f docker-compose.aws.yml exec kubrick-mcp python -c "import boto3; print('✅ boto3 available')" 2>/dev/null; then
    echo "✅ AWS dependencies installed successfully"
else
    echo "❌ AWS dependencies test failed"
fi

# Test provider initialization
echo "Testing AWS providers..."
docker-compose -f docker-compose.aws.yml exec kubrick-mcp python -c "
try:
    from kubrick_mcp.providers.bedrock import BedrockVisionProvider
    print('✅ AWS Bedrock provider available')
except Exception as e:
    print(f'❌ AWS Bedrock provider error: {e}')
" 2>/dev/null || echo "❌ Provider test failed"

echo ""
echo "🎯 AWS-Only Deployment Complete!"
echo ""
echo "Services running:"
echo "  📡 API: http://localhost:8080"
echo "  🎬 MCP: http://localhost:9090"
echo "  🌐 UI: http://localhost:3000"
echo ""
echo "Expected behavior:"
echo "  🎵 Audio transcription: AWS Transcribe"
echo "  👁️  Image captioning: AWS Bedrock Claude"
echo "  🔢 Embeddings: AWS Bedrock Titan"
echo ""
echo "Monitor logs: docker-compose -f docker-compose.aws.yml logs -f"
echo "Stop services: docker-compose -f docker-compose.aws.yml down"