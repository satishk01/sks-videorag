# AWS Bedrock Deployment and Configuration Guide

This guide covers deployment scenarios, configuration options, and migration strategies for AWS Bedrock integration with Kubrick AI.

## Table of Contents

- [Deployment Scenarios](#deployment-scenarios)
- [Configuration Options](#configuration-options)
- [Migration Guide](#migration-guide)
- [Performance Tuning](#performance-tuning)
- [Monitoring and Observability](#monitoring-and-observability)
- [Production Considerations](#production-considerations)

## Deployment Scenarios

### 1. Local Development

For local development with Docker Compose:

```bash
# 1. Clone the repository
git clone https://github.com/multi-modal-ai/multimodal-agents-course.git
cd multimodal-agents-course

# 2. Configure environment files
cp kubrick-mcp/.env.example kubrick-mcp/.env
cp kubrick-api/.env.example kubrick-api/.env

# 3. Edit .env files with your AWS credentials
# See AWS_BEDROCK_SETUP.md for detailed configuration

# 4. Start the services
make start-kubrick
```

### 2. Production Deployment

#### Option A: Docker Compose with External Database

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  kubrick-mcp:
    image: kubrick-mcp:latest
    environment:
      - AWS_REGION=${AWS_REGION}
      - VISION_PROVIDER=bedrock
      - EMBEDDINGS_PROVIDER=bedrock
    secrets:
      - aws_access_key_id
      - aws_secret_access_key
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '2'
          memory: 2G

  kubrick-api:
    image: kubrick-api:latest
    environment:
      - AWS_REGION=${AWS_REGION}
      - AGENT_PROVIDER=bedrock
    secrets:
      - aws_access_key_id
      - aws_secret_access_key
    deploy:
      replicas: 3

secrets:
  aws_access_key_id:
    external: true
  aws_secret_access_key:
    external: true
```

#### Option B: Kubernetes Deployment

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kubrick-mcp
spec:
  replicas: 2
  selector:
    matchLabels:
      app: kubrick-mcp
  template:
    metadata:
      labels:
        app: kubrick-mcp
    spec:
      serviceAccountName: kubrick-bedrock-sa
      containers:
      - name: kubrick-mcp
        image: kubrick-mcp:latest
        env:
        - name: AWS_REGION
          value: "us-east-1"
        - name: VISION_PROVIDER
          value: "bedrock"
        - name: EMBEDDINGS_PROVIDER
          value: "bedrock"
        envFrom:
        - secretRef:
            name: aws-credentials
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1"
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: kubrick-bedrock-sa
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT:role/KubrickBedrockRole
```

### 3. AWS ECS Deployment

```json
{
  "family": "kubrick-mcp",
  "taskRoleArn": "arn:aws:iam::ACCOUNT:role/KubrickBedrockTaskRole",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "kubrick-mcp",
      "image": "your-account.dkr.ecr.region.amazonaws.com/kubrick-mcp:latest",
      "environment": [
        {"name": "AWS_REGION", "value": "us-east-1"},
        {"name": "VISION_PROVIDER", "value": "bedrock"},
        {"name": "EMBEDDINGS_PROVIDER", "value": "bedrock"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/kubrick-mcp",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

## Configuration Options

### Provider Selection Matrix

| Component | OpenAI | Bedrock | AWS Transcribe | Groq | Notes |
|-----------|--------|---------|----------------|------|-------|
| Vision/Captioning | ✅ | ✅ | ❌ | ❌ | Bedrock uses Claude 3.5 Sonnet |
| Transcription | ✅ | ❌ | ✅ **Auto-fallback** | ❌ | AWS Transcribe used when no OpenAI key |
| Embeddings | ✅ | ✅ | ❌ | ❌ | Bedrock uses Titan embeddings |
| Chat/Agent | ❌ | ✅ | ❌ | ✅ | Bedrock uses Claude, Groq uses Llama |

### Environment Variable Reference

#### MCP Server Configuration

```bash
# Provider Selection
VISION_PROVIDER=bedrock          # openai | bedrock
# TRANSCRIPTION: Auto-selected based on OpenAI key availability
EMBEDDINGS_PROVIDER=bedrock      # openai | bedrock

# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...        # Optional if using IAM roles
AWS_SECRET_ACCESS_KEY=...        # Optional if using IAM roles
AWS_SESSION_TOKEN=...            # Only for temporary credentials

# Bedrock Models
BEDROCK_CLAUDE_MODEL=us.anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_EMBEDDINGS_MODEL=amazon.titan-embed-text-v1

# Performance Tuning
BEDROCK_MAX_RETRIES=3
BEDROCK_TIMEOUT=30
BEDROCK_MAX_CONCURRENT_REQUESTS=10
```

#### API Server Configuration

```bash
# Provider Selection
AGENT_PROVIDER=bedrock           # groq | bedrock

# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...

# Bedrock Models
BEDROCK_CLAUDE_MODEL=us.anthropic.claude-3-5-sonnet-20241022-v2:0

# Agent Configuration
BEDROCK_MAX_TOKENS=4096
BEDROCK_TEMPERATURE=0.7
BEDROCK_TOP_P=0.9
```

### Configuration Validation

Create a configuration validation script:

```python
# scripts/validate_config.py
import os
import boto3
from kubrick_mcp.config import get_settings
from kubrick_api.config import get_settings as get_api_settings

def validate_mcp_config():
    settings = get_settings()
    
    # Check AWS credentials
    if settings.VISION_PROVIDER == "bedrock" or settings.EMBEDDINGS_PROVIDER == "bedrock":
        try:
            client = boto3.client("bedrock", region_name=settings.AWS_REGION)
            models = client.list_foundation_models()
            print("✅ AWS Bedrock connection successful")
        except Exception as e:
            print(f"❌ AWS Bedrock connection failed: {e}")
    
    # Check model access
    if settings.VISION_PROVIDER == "bedrock":
        try:
            client = boto3.client("bedrock-runtime", region_name=settings.AWS_REGION)
            # Test model access (this might incur small charges)
            print("✅ Bedrock vision model accessible")
        except Exception as e:
            print(f"❌ Bedrock vision model access failed: {e}")

if __name__ == "__main__":
    validate_mcp_config()
```

## Migration Guide

### From OpenAI-Only to Multi-Provider

#### Step 1: Backup Current Configuration

```bash
# Backup existing .env files
cp kubrick-mcp/.env kubrick-mcp/.env.backup
cp kubrick-api/.env kubrick-api/.env.backup
```

#### Step 2: Gradual Migration

Start with a hybrid approach:

```bash
# kubrick-mcp/.env - Hybrid configuration
VISION_PROVIDER=bedrock          # Migrate vision first
TRANSCRIPTION_PROVIDER=openai    # Keep transcription on OpenAI
EMBEDDINGS_PROVIDER=openai       # Keep embeddings on OpenAI initially

# kubrick-api/.env - Keep agent on Groq initially
AGENT_PROVIDER=groq
```

#### Step 3: Test and Validate

```bash
# Test video processing with new configuration
docker-compose up kubrick-mcp
docker logs kubrick-mcp

# Test specific functionality
curl -X POST http://localhost:9090/test-vision
```

#### Step 4: Complete Migration

Once validated, migrate remaining components:

```bash
# kubrick-mcp/.env - Full Bedrock
VISION_PROVIDER=bedrock
TRANSCRIPTION_PROVIDER=openai    # Still OpenAI (no Bedrock support)
EMBEDDINGS_PROVIDER=bedrock

# kubrick-api/.env - Bedrock agent
AGENT_PROVIDER=bedrock
```

### Rollback Strategy

If issues occur, quickly rollback:

```bash
# Restore backup configurations
cp kubrick-mcp/.env.backup kubrick-mcp/.env
cp kubrick-api/.env.backup kubrick-api/.env

# Restart services
docker-compose restart
```

## Performance Tuning

### Bedrock-Specific Optimizations

#### 1. Connection Pooling

```python
# Custom Bedrock client with connection pooling
import boto3
from botocore.config import Config

config = Config(
    retries={'max_attempts': 3},
    max_pool_connections=50,
    region_name='us-east-1'
)

client = boto3.client('bedrock-runtime', config=config)
```

#### 2. Caching Strategy

```python
# Implement response caching
from functools import lru_cache
import hashlib

@lru_cache(maxsize=1000)
def cached_bedrock_call(prompt_hash, model_id):
    # Cache responses for identical prompts
    pass
```

#### 3. Batch Processing

```python
# Process multiple requests in batches
async def batch_process_images(images, batch_size=5):
    for i in range(0, len(images), batch_size):
        batch = images[i:i+batch_size]
        tasks = [process_image(img) for img in batch]
        await asyncio.gather(*tasks)
```

### Resource Allocation

#### Docker Resource Limits

```yaml
# docker-compose.yml
services:
  kubrick-mcp:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 4G
        reservations:
          cpus: '2'
          memory: 2G
```

#### Kubernetes Resource Requests

```yaml
resources:
  requests:
    memory: "2Gi"
    cpu: "1"
  limits:
    memory: "4Gi"
    cpu: "2"
```

## Monitoring and Observability

### CloudWatch Integration

```python
# Add CloudWatch metrics
import boto3

cloudwatch = boto3.client('cloudwatch')

def publish_metric(metric_name, value, unit='Count'):
    cloudwatch.put_metric_data(
        Namespace='Kubrick/Bedrock',
        MetricData=[
            {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Dimensions': [
                    {
                        'Name': 'Service',
                        'Value': 'kubrick-mcp'
                    }
                ]
            }
        ]
    )
```

### Custom Metrics

Track important metrics:

- Request latency
- Error rates
- Token usage
- Cost per request
- Model availability

### Logging Configuration

```python
# Enhanced logging for Bedrock operations
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bedrock.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('bedrock_provider')
```

## Production Considerations

### Security

1. **Use IAM Roles** instead of access keys
2. **Enable VPC endpoints** for Bedrock
3. **Implement request signing** for additional security
4. **Use AWS Secrets Manager** for credential management

### High Availability

1. **Multi-region deployment** for disaster recovery
2. **Load balancing** across multiple instances
3. **Health checks** and automatic failover
4. **Circuit breaker pattern** for external dependencies

### Cost Management

1. **Monitor usage** with AWS Cost Explorer
2. **Set up billing alerts**
3. **Implement request quotas**
4. **Use spot instances** for non-critical workloads

### Compliance

1. **Data residency** requirements
2. **Audit logging** with CloudTrail
3. **Encryption** at rest and in transit
4. **Access controls** and least privilege

## Troubleshooting Production Issues

### Common Production Problems

#### 1. High Latency

```bash
# Check network connectivity
curl -w "@curl-format.txt" -o /dev/null -s "https://bedrock-runtime.us-east-1.amazonaws.com"

# Monitor CloudWatch metrics
aws logs filter-log-events --log-group-name /aws/lambda/kubrick --filter-pattern "ERROR"
```

#### 2. Rate Limiting

```python
# Implement exponential backoff
import time
import random

def exponential_backoff(attempt):
    delay = (2 ** attempt) + random.uniform(0, 1)
    time.sleep(min(delay, 60))  # Cap at 60 seconds
```

#### 3. Memory Issues

```bash
# Monitor memory usage
docker stats kubrick-mcp
kubectl top pods -l app=kubrick-mcp
```

### Emergency Procedures

#### Quick Rollback

```bash
# Emergency rollback script
#!/bin/bash
echo "Rolling back to OpenAI providers..."
kubectl set env deployment/kubrick-mcp VISION_PROVIDER=openai
kubectl set env deployment/kubrick-api AGENT_PROVIDER=groq
kubectl rollout restart deployment/kubrick-mcp
kubectl rollout restart deployment/kubrick-api
```

#### Health Check Endpoints

```python
# Add health check endpoints
@app.get("/health/bedrock")
async def bedrock_health():
    try:
        provider = await get_bedrock_provider()
        if provider.is_available():
            return {"status": "healthy", "provider": "bedrock"}
        else:
            return {"status": "unhealthy", "provider": "bedrock"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

This deployment guide provides comprehensive coverage of production deployment scenarios, configuration options, and operational considerations for AWS Bedrock integration.