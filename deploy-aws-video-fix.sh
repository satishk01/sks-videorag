#!/bin/bash

echo "🚀 Deploying AWS Video Processing Fix..."

# Stop containers
echo "Stopping containers..."
docker-compose down

# Pull latest changes (if using git)
echo "Pulling latest changes..."
git pull origin main || echo "Git pull failed or not a git repo - continuing..."

# Ensure environment files are set up
echo "Setting up environment files..."
if [ ! -f "kubrick-api/.env" ]; then
    cp kubrick-api/.env.aws-only kubrick-api/.env
    echo "Created kubrick-api/.env from aws-only template"
fi

if [ ! -f "kubrick-mcp/.env" ]; then
    cp kubrick-mcp/.env.aws-only kubrick-mcp/.env
    echo "Created kubrick-mcp/.env from aws-only template"
fi

# Check if AWS credentials are set
echo "Checking AWS credentials..."
if grep -q "your_aws_access_key_here" kubrick-api/.env; then
    echo "⚠️  WARNING: AWS credentials not set in kubrick-api/.env"
    echo "Please update AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
fi

if grep -q "your_aws_access_key_here" kubrick-mcp/.env; then
    echo "⚠️  WARNING: AWS credentials not set in kubrick-mcp/.env"
    echo "Please update AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
fi

# Build containers with no cache
echo "Building containers (this may take a few minutes)..."
docker-compose build --no-cache

# Start containers
echo "Starting containers..."
docker-compose up -d

# Wait a moment for containers to start
sleep 10

# Test the providers inside the container
echo "Testing AWS providers..."
docker-compose exec kubrick-mcp python /app/test-providers-docker.py

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Check logs: docker-compose logs -f"
echo "2. Process a video to test AWS integration"
echo "3. Monitor AWS Console for Transcribe jobs and Bedrock usage"
echo ""
echo "Expected logs should show:"
echo "  - 'Using AWS Transcribe for audio transcription'"
echo "  - 'Using AWS Bedrock for image captioning'"
echo "  - 'Using AWS Bedrock for embeddings'"