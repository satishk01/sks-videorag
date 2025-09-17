#!/bin/bash

echo "🔧 Fixing boto3 dependency issue..."

# Stop containers
echo "Stopping containers..."
docker-compose -f docker-compose.ec2.yml down

# Navigate to MCP directory and regenerate lock file
echo "Regenerating uv.lock file with boto3..."
cd kubrick-mcp

# Remove existing lock file
rm -f uv.lock

# Add boto3 explicitly and regenerate lock
echo "Adding boto3 dependency..."
uv add boto3>=1.35.0

# Go back to root
cd ..

# Rebuild containers with no cache
echo "Rebuilding containers (this may take a few minutes)..."
docker-compose -f docker-compose.ec2.yml build --no-cache

# Start containers
echo "Starting containers..."
docker-compose -f docker-compose.ec2.yml up -d

# Wait for containers to start
echo "Waiting for containers to start..."
sleep 15

# Check if boto3 is now available
echo "Testing boto3 availability..."
docker-compose -f docker-compose.ec2.yml exec kubrick-mcp python -c "import boto3; print('✅ boto3 imported successfully')"

echo ""
echo "✅ boto3 dependency fix complete!"
echo "Monitor logs with: docker-compose -f docker-compose.ec2.yml logs -f"