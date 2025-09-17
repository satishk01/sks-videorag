#!/bin/bash

echo "🚀 Deploying AWS Video Processing Patch..."

# Stop containers
echo "Stopping containers..."
docker-compose down

# Copy test files to container directories
echo "Copying test files..."
cp test-aws-patch.py kubrick-mcp/
cp debug-video-processing.py kubrick-mcp/

# Ensure environment files are set up for AWS-only
echo "Setting up AWS-only environment..."
if [ ! -f "kubrick-api/.env" ]; then
    cp kubrick-api/.env.aws-only kubrick-api/.env
fi

if [ ! -f "kubrick-mcp/.env" ]; then
    cp kubrick-mcp/.env.aws-only kubrick-mcp/.env
fi

# Verify no OpenAI key is set
echo "Ensuring no OpenAI key is set..."
sed -i '/OPENAI_API_KEY=/d' kubrick-mcp/.env
echo "# OPENAI_API_KEY not set - using AWS services only" >> kubrick-mcp/.env

# Build containers with no cache
echo "Building containers (this may take a few minutes)..."
docker-compose build --no-cache

# Start containers
echo "Starting containers..."
docker-compose up -d

# Wait for containers to start
echo "Waiting for containers to start..."
sleep 15

# Test the patch
echo "Testing AWS patch..."
docker-compose exec kubrick-mcp python /app/test-aws-patch.py

echo ""
echo "✅ AWS Patch Deployment Complete!"
echo ""
echo "The video processing should now use:"
echo "  🎵 AWS Transcribe for audio transcription"
echo "  👁️  AWS Bedrock Claude for image captioning"
echo "  🔢 AWS Bedrock Titan for embeddings"
echo ""
echo "Process a video to test the fix!"
echo "Monitor logs with: docker-compose logs -f kubrick-mcp"