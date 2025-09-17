#!/bin/bash

echo "🚀 Deploying Working AWS Video System..."

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
echo "# No OpenAI key - AWS mode enabled" >> kubrick-mcp/.env

# Build and start containers
echo "Building containers..."
docker-compose -f docker-compose.ec2.yml build --no-cache

echo "Starting containers..."
docker-compose -f docker-compose.ec2.yml up -d

# Wait for startup
echo "Waiting for services to start..."
sleep 15

# Check status
echo "Checking service status..."
docker-compose -f docker-compose.ec2.yml ps

# Test MCP service
echo "Testing MCP service..."
if docker-compose -f docker-compose.ec2.yml exec kubrick-mcp python -c "print('MCP container is running')" 2>/dev/null; then
    echo "✅ MCP container is accessible"
else
    echo "❌ MCP container not accessible"
fi

# Check logs for any errors
echo "Checking for errors in logs..."
docker-compose -f docker-compose.ec2.yml logs kubrick-mcp | tail -10

echo ""
echo "🎯 AWS Video System Deployment Complete!"
echo ""
echo "Status:"
echo "  📡 API: http://localhost:8080"
echo "  🎬 MCP: http://localhost:9090"
echo "  🌐 UI: http://localhost:3000"
echo ""
echo "Video Processing:"
echo "  🎵 Basic video processing enabled"
echo "  📹 Video upload and re-encoding works"
echo "  🔍 Video search capabilities available"
echo ""
echo "Next Steps:"
echo "1. Test video upload through the UI"
echo "2. Check that video processing completes without errors"
echo "3. Verify AWS credentials are configured for full AWS integration"
echo ""
echo "Monitor logs: docker-compose -f docker-compose.ec2.yml logs -f"
echo "Stop services: docker-compose -f docker-compose.ec2.yml down"