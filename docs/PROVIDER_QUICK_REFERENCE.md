# AI Provider Quick Reference

This guide provides a quick reference for configuring different AI providers in Kubrick.

## Provider Capabilities

| Feature | OpenAI | AWS Bedrock | AWS Transcribe | Groq |
|---------|--------|-------------|----------------|------|
| **Vision/Image Captioning** | ✅ GPT-4o | ✅ Claude 3.5 Sonnet v2 | ❌ | ❌ |
| **Audio Transcription** | ✅ Whisper | ❌ | ✅ **Auto-fallback** | ❌ |
| **Text Embeddings** | ✅ text-embedding-3-small | ✅ Titan Embeddings | ❌ | ❌ |
| **Chat/Conversation** | ❌ | ✅ Claude 3.5 Sonnet v2 | ❌ | ✅ Llama 4 |
| **Tool Calling** | ❌ | ✅ (Limited) | ❌ | ✅ Full Support |

> **NEW**: AWS Transcribe automatically used when OpenAI key is not provided - fully AWS-native transcription!

## Quick Configuration

### OpenAI + Groq (Default)

```bash
# kubrick-mcp/.env
VISION_PROVIDER=openai
TRANSCRIPTION_PROVIDER=openai
EMBEDDINGS_PROVIDER=openai
OPENAI_API_KEY=your_key_here

# kubrick-api/.env
AGENT_PROVIDER=groq
GROQ_API_KEY=your_key_here
```

### AWS-Only (Bedrock + Transcribe)

```bash
# kubrick-mcp/.env
VISION_PROVIDER=bedrock
# OPENAI_API_KEY=  # Leave empty - AWS Transcribe will be used automatically
EMBEDDINGS_PROVIDER=bedrock
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_secret_here

# kubrick-api/.env
AGENT_PROVIDER=bedrock
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_secret_here
```

### Hybrid Configuration

```bash
# kubrick-mcp/.env
VISION_PROVIDER=bedrock        # Use Claude for better vision
OPENAI_API_KEY=your_key_here   # Provide for Whisper transcription
EMBEDDINGS_PROVIDER=openai     # Use OpenAI for compatibility

# kubrick-api/.env
AGENT_PROVIDER=groq           # Use Groq for fast responses
```

## Model IDs

### AWS Bedrock Models

```bash
# Claude Models
BEDROCK_CLAUDE_MODEL=us.anthropic.claude-3-5-sonnet-20241022-v2:0

# Embedding Models
BEDROCK_EMBEDDINGS_MODEL=amazon.titan-embed-text-v1
```

### OpenAI Models

```bash
# Vision Models
IMAGE_CAPTION_MODEL=gpt-4o-mini

# Transcription Models
AUDIO_TRANSCRIPT_MODEL=gpt-4o-mini-transcribe

# Embedding Models
TRANSCRIPT_SIMILARITY_EMBD_MODEL=text-embedding-3-small
CAPTION_SIMILARITY_EMBD_MODEL=text-embedding-3-small
```

### Groq Models

```bash
# Chat Models
GROQ_ROUTING_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
GROQ_TOOL_USE_MODEL=meta-llama/llama-4-maverick-17b-128e-instruct
GROQ_GENERAL_MODEL=meta-llama/llama-4-maverick-17b-128e-instruct
```

## Performance Comparison

| Provider | Latency | Cost | Quality | Availability |
|----------|---------|------|---------|--------------|
| **OpenAI** | Medium | Medium | High | High |
| **AWS Bedrock** | Medium-High | Variable | Very High | High |
| **Groq** | Very Low | Low | High | Medium |

## Use Case Recommendations

### High-Quality Video Analysis
```bash
VISION_PROVIDER=bedrock        # Claude 3.5 Sonnet v2
EMBEDDINGS_PROVIDER=bedrock    # Titan embeddings
AGENT_PROVIDER=bedrock         # Claude for reasoning
```

### Fast Interactive Chat
```bash
VISION_PROVIDER=openai         # Good quality, fast
EMBEDDINGS_PROVIDER=openai     # Proven compatibility
AGENT_PROVIDER=groq           # Fastest responses
```

### Cost-Optimized
```bash
VISION_PROVIDER=openai         # Reasonable cost
EMBEDDINGS_PROVIDER=openai     # Bulk pricing
AGENT_PROVIDER=groq           # Free tier
```

### Enterprise/Production (AWS-Native)
```bash
VISION_PROVIDER=bedrock        # AWS infrastructure
EMBEDDINGS_PROVIDER=bedrock    # Consistent ecosystem
AGENT_PROVIDER=bedrock         # Enterprise support
# OPENAI_API_KEY=              # Leave empty for AWS Transcribe
```

## Troubleshooting

### Common Issues

| Error | Likely Cause | Solution |
|-------|--------------|----------|
| `NoCredentialsError` | Missing AWS credentials | Check AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY |
| `AccessDeniedException` | No model access | Request access in Bedrock console |
| `RateLimitError` | Too many requests | Implement backoff or upgrade plan |
| `ModelNotFoundError` | Wrong model ID | Check model availability in region |

### Quick Fixes

```bash
# Test AWS credentials
aws bedrock list-foundation-models --region us-east-1

# Test OpenAI key
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models

# Test Groq key
curl -H "Authorization: Bearer $GROQ_API_KEY" https://api.groq.com/openai/v1/models

# Check Docker logs
docker logs kubrick-mcp
docker logs kubrick-api
```

## Migration Checklist

### From OpenAI to Bedrock

- [ ] Request Bedrock model access
- [ ] Configure AWS credentials
- [ ] Update environment variables
- [ ] Test video processing
- [ ] Monitor costs
- [ ] Update monitoring/alerts

### From Groq to Bedrock

- [ ] Configure AWS credentials
- [ ] Update AGENT_PROVIDER setting
- [ ] Test chat functionality
- [ ] Verify tool calling works
- [ ] Update any Groq-specific code

## Support

- **AWS Bedrock**: [AWS Support](https://aws.amazon.com/support/)
- **OpenAI**: [OpenAI Help Center](https://help.openai.com/)
- **Groq**: [Groq Documentation](https://console.groq.com/docs)
- **Kubrick Issues**: [GitHub Issues](https://github.com/multi-modal-ai/multimodal-agents-course/issues)