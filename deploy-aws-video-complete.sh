#!/bin/bash

echo "🎬 Deploying Complete AWS Video Processing..."

# Stop containers
echo "Stopping containers..."
docker-compose -f docker-compose.ec2.yml down

# Set up AWS-only environment
echo "Setting up AWS-only environment..."
if [ ! -f "kubrick-api/.env" ]; then
    cp kubrick-api/.env.aws-only kubrick-api/.env
fi

if [ ! -f "kubrick-mcp/.env" ]; then
    cp kubrick-mcp/.env.aws-only kubrick-mcp/.env
fi

# Ensure no OpenAI key (force AWS mode)
echo "Configuring for AWS-only mode..."
sed -i '/OPENAI_API_KEY=/d' kubrick-mcp/.env 2>/dev/null || true
echo "# No OpenAI key - AWS video processing enabled" >> kubrick-mcp/.env

# Verify AWS credentials are set
echo "Checking AWS credentials..."
if grep -q "your_aws_access_key_here" kubrick-api/.env; then
    echo "⚠️  WARNING: Please update AWS credentials in kubrick-api/.env"
    echo "   Set your actual AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
fi

if grep -q "your_aws_access_key_here" kubrick-mcp/.env; then
    echo "⚠️  WARNING: Please update AWS credentials in kubrick-mcp/.env"
    echo "   Set your actual AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
fi

# Build and start containers
echo "Building containers with AWS video processing..."
docker-compose -f docker-compose.ec2.yml build --no-cache

echo "Starting containers..."
docker-compose -f docker-compose.ec2.yml up -d

# Wait for startup
echo "Waiting for services to initialize..."
sleep 20

# Check container status
echo "Checking container status..."
docker-compose -f docker-compose.ec2.yml ps

# Test if MCP service is running
echo "Testing MCP service..."
if curl -s http://localhost:9090/mcp > /dev/null; then
    echo "✅ MCP service is running"
else
    echo "❌ MCP service not responding"
fi

# Test if API service is running
echo "Testing API service..."
if curl -s http://localhost:8080 > /dev/null; then
    echo "✅ API service is running"
else
    echo "❌ API service not responding"
fi

echo ""
echo "🎯 AWS Video Processing Deployment Complete!"
echo ""
echo "Services:"
echo "  📡 API: http://localhost:8080"
echo "  🎬 MCP: http://localhost:9090"
echo "  🌐 UI: http://localhost:3000"
echo ""
echo "Video Processing Features:"
echo "  🎵 Audio Transcription: AWS Transcribe"
echo "  👁️  Image Captioning: AWS Bedrock Claude"
echo "  🔢 Embeddings: AWS Bedrock Titan"
echo "  🖼️  Frame Analysis: HuggingFace CLIP + AWS"
echo ""
echo "Next Steps:"
echo "1. Ensure AWS credentials are configured"
echo "2. Upload a video through the UI"
echo "3. Process the video to test AWS integration"
echo ""
echo "Monitor logs: docker-compose -f docker-compose.ec2.yml logs -f"
echo "Stop services: docker-compose -f docker-compose.ec2.yml down"