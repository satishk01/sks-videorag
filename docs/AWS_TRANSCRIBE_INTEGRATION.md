# AWS Transcribe Integration

This document explains the AWS Transcribe integration that provides automatic fallback transcription when OpenAI is not available.

## Overview

The Kubrick system now includes intelligent transcription provider selection:

- **Primary**: OpenAI Whisper (if API key is provided)
- **Fallback**: AWS Transcribe (automatically used when no OpenAI key)

This enables a fully AWS-native deployment without any OpenAI dependencies.

## How It Works

### Automatic Provider Selection

```python
# The system automatically chooses the best available transcription provider
if openai_api_key_available:
    use_openai_whisper()
else:
    use_aws_transcribe()
```

### AWS Transcribe Process

1. **Audio Upload**: Audio chunks are uploaded to a temporary S3 bucket
2. **Transcription Job**: AWS Transcribe processes the audio asynchronously
3. **Result Retrieval**: Transcript is downloaded and processed
4. **Cleanup**: Temporary files are automatically deleted

## Configuration

### AWS-Only Setup (No OpenAI)

```bash
# kubrick-mcp/.env
# OPENAI_API_KEY=  # Leave empty or remove

AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

VISION_PROVIDER=bedrock
EMBEDDINGS_PROVIDER=bedrock
```

### Hybrid Setup (OpenAI + AWS)

```bash
# kubrick-mcp/.env
OPENAI_API_KEY=your_openai_key  # Whisper will be used

AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

VISION_PROVIDER=bedrock
EMBEDDINGS_PROVIDER=bedrock
```

## AWS Permissions Required

### IAM Policy for AWS Transcribe

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "transcribe:StartTranscriptionJob",
                "transcribe:GetTranscriptionJob",
                "transcribe:DeleteTranscriptionJob",
                "transcribe:ListTranscriptionJobs"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:CreateBucket",
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject",
                "s3:PutBucketLifecycleConfiguration"
            ],
            "Resource": [
                "arn:aws:s3:::kubrick-transcribe-*",
                "arn:aws:s3:::kubrick-transcribe-*/*"
            ]
        }
    ]
}
```

## S3 Bucket Management

### Automatic Bucket Creation

- Buckets are created automatically with naming pattern: `kubrick-transcribe-{region}-{random}`
- Lifecycle policy automatically deletes temporary files after 1 day
- Buckets are region-specific for optimal performance

### Manual Bucket Configuration

You can specify a custom bucket:

```python
# In your configuration
AWS_TRANSCRIBE_BUCKET=my-custom-transcribe-bucket
```

## Performance Characteristics

### AWS Transcribe vs OpenAI Whisper

| Feature | OpenAI Whisper | AWS Transcribe |
|---------|----------------|----------------|
| **Latency** | ~2-5 seconds | ~10-30 seconds |
| **Accuracy** | Very High | High |
| **Cost** | $0.006/minute | $0.024/minute |
| **Languages** | 99+ languages | 31+ languages |
| **Real-time** | No | No |
| **Batch Processing** | Yes | Yes |

### When to Use Each

**Use OpenAI Whisper when:**
- You need fastest transcription
- You're already using OpenAI for other services
- You need support for many languages
- Cost is a primary concern

**Use AWS Transcribe when:**
- You want AWS-native infrastructure
- You're using other AWS services
- You need enterprise-grade compliance
- You want to avoid external API dependencies

## Monitoring and Troubleshooting

### CloudWatch Metrics

AWS Transcribe automatically provides metrics:
- Job success/failure rates
- Processing duration
- Queue depth

### Common Issues

#### 1. S3 Bucket Creation Fails

```bash
# Error: Access denied creating bucket
# Solution: Ensure IAM user has s3:CreateBucket permission
```

#### 2. Transcription Job Timeout

```bash
# Error: Job timed out after 300 seconds
# Solution: Increase timeout or check audio file size
```

#### 3. Audio Format Issues

```bash
# Error: Unsupported audio format
# Solution: Ensure audio is in supported format (MP3, WAV, etc.)
```

### Debug Logging

Enable debug logging to troubleshoot:

```bash
export LOG_LEVEL=DEBUG
docker-compose up kubrick-mcp
```

## Cost Optimization

### Best Practices

1. **Audio Chunking**: Process audio in optimal chunk sizes (10-30 seconds)
2. **Lifecycle Policies**: Automatic cleanup of temporary S3 objects
3. **Regional Deployment**: Use same region for S3 and Transcribe
4. **Batch Processing**: Group multiple transcription jobs when possible

### Cost Comparison

For 1 hour of audio transcription:

| Provider | Cost | Notes |
|----------|------|-------|
| OpenAI Whisper | $0.36 | Direct API cost |
| AWS Transcribe | $1.44 | Plus minimal S3 storage |

## Migration Guide

### From OpenAI-Only to AWS Transcribe

1. **Add AWS credentials** to your environment
2. **Remove or comment out** `OPENAI_API_KEY`
3. **Restart services** - AWS Transcribe will be used automatically
4. **Test transcription** with a sample video

### From AWS Transcribe to OpenAI

1. **Add `OPENAI_API_KEY`** to your environment
2. **Restart services** - OpenAI Whisper will be used automatically
3. **Optional**: Clean up unused S3 buckets

## Security Considerations

### Data Privacy

- **Temporary Storage**: Audio files are stored temporarily in S3
- **Automatic Cleanup**: Files are deleted after processing
- **Encryption**: S3 objects can be encrypted at rest
- **Access Control**: Strict IAM policies limit access

### Compliance

- **GDPR**: Ensure proper data handling for EU users
- **HIPAA**: AWS Transcribe supports HIPAA compliance
- **SOC 2**: AWS provides SOC 2 compliance documentation

## Future Enhancements

### Planned Features

- **Real-time Transcription**: Support for streaming audio
- **Custom Vocabularies**: Domain-specific transcription accuracy
- **Multi-language Detection**: Automatic language detection
- **Speaker Identification**: Multiple speaker support

### Integration Opportunities

- **Amazon Comprehend**: Sentiment analysis of transcripts
- **Amazon Translate**: Multi-language transcript translation
- **Amazon Polly**: Text-to-speech for processed transcripts

This integration provides a robust, scalable transcription solution that seamlessly integrates with the existing Kubrick architecture while maintaining the flexibility to use either OpenAI or AWS services based on your specific needs and constraints.