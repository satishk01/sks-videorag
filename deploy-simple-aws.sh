#!/bin/bash

echo "🚀 Simple AWS-Only Deployment..."

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

# Remove OpenAI key to force AWS mode
sed -i '/OPENAI_API_KEY=/d' kubrick-mcp/.env 2>/dev/null || true
echo "# No OpenAI key - AWS mode enabled" >> kubrick-mcp/.env

# Build and start
echo "Building and starting containers..."
docker-compose -f docker-compose.ec2.yml build --no-cache
docker-compose -f docker-compose.ec2.yml up -d

# Wait for startup
sleep 15

# Check status
echo "Checking container status..."
docker-compose -f docker-compose.ec2.yml ps

echo ""
echo "✅ Simple AWS deployment complete!"
echo ""
echo "Note: Video processing is currently disabled in AWS-only mode"
echo "The API and chat functionality will work with AWS Bedrock"
echo ""
echo "Monitor logs: docker-compose -f docker-compose.ec2.yml logs -f"