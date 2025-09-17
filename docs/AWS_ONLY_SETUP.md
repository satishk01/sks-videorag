# AWS-Only Setup Guide

This guide helps you configure Kubrick to use only AWS services without any OpenAI dependencies.

## Services Used

- **AWS Bedrock**: Claude 3.5 Sonnet v2 for chat, vision, and embeddings
- **AWS Transcribe**: For audio transcription (automatic fallback when no OpenAI key)

## Quick Setup

### 1. Copy AWS-Only Environment Files

```bash
# For API service
cp kubrick-api/.env.aws-only kubrick-api/.env

# For MCP service  
cp kubrick-mcp/.env.aws-only kubrick-mcp/.env
```

### 2. Configure AWS Credentials

Edit both `.env` files and update:

```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_actual_access_key
AWS_SECRET_ACCESS_KEY=your_actual_secret_key
```

### 3. Verify Configuration

The configuration will automatically:
- Use Bedrock Claude 3.5 Sonnet v2 for all chat operations
- Use Bedrock Claude for vision analysis
- Use Bedrock Titan for embeddings
- Use AWS Transcribe for audio transcription (no OpenAI key needed)

## Key Benefits

✅ **No OpenAI Dependencies**: System works completely without OpenAI API keys
✅ **AWS Native**: All processing stays within AWS ecosystem
✅ **Automatic Fallbacks**: Smart provider selection based on available credentials
✅ **Cost Effective**: Use AWS credits and billing

## Verification

After setup, the logs should show:
```
Chat provider initialized: bedrock
Vision provider initialized: bedrock
Embeddings provider initialized: bedrock
Using AWS Transcribe for transcription (no OpenAI key)
```

## Troubleshooting

If you see any OpenAI-related errors:
1. Ensure no `OPENAI_API_KEY` is set in your environment
2. Verify AWS credentials are correctly configured
3. Check that Bedrock models are available in your AWS region

## AWS Permissions Required

Your AWS credentials need access to:
- `bedrock:InvokeModel` for Claude and Titan models
- `transcribe:StartTranscriptionJob` for audio processing
- `s3:PutObject`, `s3:GetObject` for Transcribe temporary storage