# AWS Bedrock Setup Guide

This guide provides step-by-step instructions for setting up AWS Bedrock integration with the Kubrick AI system.

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI installed and configured (optional but recommended)
- Docker and Docker Compose installed
- Python 3.12+ (for local development)

## AWS Account Setup

### 1. Request Model Access

Before using AWS Bedrock models, you need to request access to the specific models:

1. **Log in to AWS Console** and navigate to the **Amazon Bedrock** service
2. **Go to Model Access** in the left sidebar
3. **Request access** to the following models:
   - **Anthropic Claude 3.5 Sonnet v2** (`us.anthropic.claude-3-5-sonnet-20241022-v2:0`)
   - **Amazon Titan Text Embeddings** (`amazon.titan-embed-text-v1`)

4. **Wait for approval** - This can take a few minutes to several hours depending on the model

### 2. Create IAM User and Permissions

Create an IAM user with the necessary permissions for Bedrock and Transcribe access:

#### Option A: Using AWS Console

1. **Navigate to IAM** in the AWS Console
2. **Create a new user** with programmatic access
3. **Attach the following managed policies**:
   - `AmazonBedrockFullAccess` (for full access)
   - `AmazonTranscribeFullAccess` (for transcription)
   - Or create a custom policy with minimal permissions (see below)

#### Option B: Custom IAM Policy (Recommended)

Create a custom policy with minimal required permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:ListFoundationModels",
                "bedrock:GetFoundationModel"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v1"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:ListFoundationModels"
            ],
            "Resource": "*"
        },
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

### 3. Get AWS Credentials

After creating the IAM user:

1. **Generate Access Keys** for the user
2. **Save the credentials** securely:
   - Access Key ID
   - Secret Access Key
3. **Note the AWS Region** where you want to use Bedrock (e.g., `us-east-1`)

## Configuration

### Environment Variables

Configure the following environment variables in your `.env` files:

#### For MCP Server (`kubrick-mcp/.env`)

```bash
# OpenAI Configuration (OPTIONAL - if not provided, AWS Transcribe will be used)
OPENAI_API_KEY=your_openai_key_here

# AWS Bedrock Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
# AWS_SESSION_TOKEN=  # Only needed for temporary credentials

# Provider Selection (openai | bedrock)
VISION_PROVIDER=bedrock
# TRANSCRIPTION_PROVIDER is auto-selected: OpenAI if key available, otherwise AWS Transcribe
EMBEDDINGS_PROVIDER=bedrock

# Bedrock Model Configuration
BEDROCK_CLAUDE_MODEL=us.anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_EMBEDDINGS_MODEL=amazon.titan-embed-text-v1

# Existing Opik configuration
OPIK_API_KEY=your_opik_key_here
OPIK_WORKSPACE=default
OPIK_PROJECT=kubrick-mcp
```

#### For API Server (`kubrick-api/.env`)

```bash
# Existing Groq configuration
GROQ_API_KEY=your_groq_key_here

# AWS Bedrock Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
# AWS_SESSION_TOKEN=  # Only needed for temporary credentials

# Provider Selection (groq | bedrock)
AGENT_PROVIDER=bedrock

# Bedrock Model Configuration
BEDROCK_CLAUDE_MODEL=us.anthropic.claude-3-5-sonnet-20241022-v2:0

# Existing Opik configuration
OPIK_API_KEY=your_opik_key_here
OPIK_PROJECT=kubrick-api
```

## AWS-Only Configuration (No OpenAI)

For a completely AWS-native setup without any OpenAI dependencies:

```bash
# kubrick-mcp/.env - AWS Only
# OPENAI_API_KEY=  # Leave empty or remove entirely

AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here

VISION_PROVIDER=bedrock
# Transcription will automatically use AWS Transcribe when no OpenAI key
EMBEDDINGS_PROVIDER=bedrock

BEDROCK_CLAUDE_MODEL=us.anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_EMBEDDINGS_MODEL=amazon.titan-embed-text-v1

# kubrick-api/.env - AWS Only
# No OpenAI or Groq keys needed
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here

AGENT_PROVIDER=bedrock
BEDROCK_CLAUDE_MODEL=us.anthropic.claude-3-5-sonnet-20241022-v2:0
```

### Alternative: AWS Credentials File

Instead of environment variables, you can use AWS credentials file:

1. **Create AWS credentials file** at `~/.aws/credentials`:

```ini
[default]
aws_access_key_id = your_access_key_here
aws_secret_access_key = your_secret_key_here
region = us-east-1
```

2. **For Docker deployment**, uncomment the volume mount in `docker-compose.yml`:

```yaml
volumes:
  - ~/.aws:/root/.aws:ro
```

## Testing the Setup

### 1. Test AWS Credentials

Test your AWS credentials using the AWS CLI:

```bash
aws bedrock list-foundation-models --region us-east-1
```

You should see a list of available models including Claude and Titan models.

### 2. Test Model Access

Test access to specific models:

```bash
aws bedrock get-foundation-model \
  --model-identifier us.anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --region us-east-1
```

### 3. Test Kubrick Integration

1. **Start the services**:
```bash
make start-kubrick
```

2. **Check the logs** for successful initialization:
```bash
docker logs kubrick-mcp
docker logs kubrick-api
```

Look for messages like:
- "Bedrock vision provider initialized"
- "Bedrock chat provider initialized"

## Troubleshooting

### Common Issues

#### 1. Model Access Denied

**Error**: `AccessDeniedException: You don't have access to the model`

**Solution**:
- Ensure you've requested access to the model in the Bedrock console
- Wait for approval (can take several hours)
- Check that your IAM user has the correct permissions

#### 2. Invalid Credentials

**Error**: `NoCredentialsError` or `InvalidAccessKeyId`

**Solution**:
- Verify your AWS credentials are correct
- Check that the IAM user has the necessary permissions
- Ensure credentials are properly set in environment variables

#### 3. Region Issues

**Error**: `EndpointConnectionError` or model not available

**Solution**:
- Ensure you're using a region where Bedrock is available
- Check that the specific models are available in your chosen region
- Common regions: `us-east-1`, `us-west-2`, `eu-west-1`

#### 4. Rate Limiting

**Error**: `ThrottlingException`

**Solution**:
- Implement retry logic (already included in the provider)
- Consider using multiple regions for load distribution
- Contact AWS support for higher rate limits if needed

### Debug Mode

Enable debug logging by setting the log level:

```bash
export LOG_LEVEL=DEBUG
```

This will provide detailed information about API calls and responses.

## Security Best Practices

1. **Use IAM Roles** instead of access keys when possible (e.g., on EC2)
2. **Rotate credentials** regularly
3. **Use least privilege** principle for IAM permissions
4. **Never commit credentials** to version control
5. **Use AWS Secrets Manager** for production deployments
6. **Enable CloudTrail** for API call auditing

## Cost Optimization

1. **Monitor usage** through AWS Cost Explorer
2. **Set up billing alerts** for unexpected charges
3. **Use appropriate model sizes** for your use case
4. **Implement caching** for repeated requests
5. **Consider using provisioned throughput** for high-volume applications

## Next Steps

After successful setup:

1. **Test video processing** with Bedrock vision models
2. **Compare performance** between OpenAI and Bedrock providers
3. **Monitor costs** and usage patterns
4. **Optimize configurations** based on your specific use case

For additional help, refer to the [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/) or contact AWS support.