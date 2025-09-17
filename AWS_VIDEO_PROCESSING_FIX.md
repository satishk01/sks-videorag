# AWS Video Processing Fix

## Problem Identified

The video processing system was hardcoded to use OpenAI APIs through Pixeltable, which is why you were seeing transcription errors and no AWS Transcribe jobs. The system wasn't using our AWS provider factory at all.

## Solution Implemented

✅ **Created AWS-compatible Pixeltable functions** (`aws_functions.py`)
✅ **Modified VideoProcessor** to use AWS providers when configured
✅ **Added intelligent provider selection** based on configuration
✅ **Maintained backward compatibility** with OpenAI when keys are available

## Key Changes Made

### 1. New AWS Functions (`kubrick-mcp/src/kubrick_mcp/video/ingestion/aws_functions.py`)
- `aws_transcribe()` - Uses AWS Transcribe via our provider factory
- `aws_vision()` - Uses AWS Bedrock Claude for image captioning  
- `aws_embeddings()` - Uses AWS Bedrock Titan for embeddings

### 2. Updated VideoProcessor (`kubrick-mcp/src/kubrick_mcp/video/ingestion/video_processor.py`)
- Added provider factory integration
- Intelligent selection between AWS and OpenAI based on configuration
- Proper logging to show which providers are being used

## Expected Behavior After Fix

When you process a video with AWS-only configuration:

```
VideoProcessor initialized
Using AWS Transcribe for audio transcription
Using AWS Bedrock for image captioning  
Using AWS Bedrock for audio embeddings
Using AWS Bedrock for caption embeddings
```

You should see:
- ✅ AWS Transcribe jobs in your AWS Console
- ✅ AWS Bedrock API calls for vision and embeddings
- ✅ No more "179 errors" in video processing
- ✅ Successful transcription and captioning

## Deployment Steps

### 1. Update Code on EC2
```bash
git pull origin main  # Get the latest changes
```

### 2. Verify Configuration
Ensure your `.env` files have:
```bash
# kubrick-mcp/.env
VISION_PROVIDER=bedrock
EMBEDDINGS_PROVIDER=bedrock
# OPENAI_API_KEY should be empty or not set

AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

### 3. Test Providers (Optional)
```bash
python test-aws-providers.py
```

### 4. Rebuild and Deploy
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up
```

## Verification

### Check Logs
Look for these log messages:
```
Using AWS Transcribe for audio transcription
Using AWS Bedrock for image captioning
Using AWS Bedrock for audio embeddings
Using AWS Bedrock for caption embeddings
```

### Check AWS Console
- **AWS Transcribe**: You should see transcription jobs
- **AWS Bedrock**: You should see API usage for Claude and Titan models

### Test Video Processing
Process a video and verify:
- No more "179 errors"
- Successful transcription results
- Proper image captions
- Working embeddings

## Troubleshooting

### If you still see OpenAI errors:
1. Verify `OPENAI_API_KEY` is not set in environment
2. Check that `VISION_PROVIDER=bedrock` and `EMBEDDINGS_PROVIDER=bedrock`
3. Ensure AWS credentials are valid

### If AWS Transcribe jobs don't appear:
1. Check AWS credentials have Transcribe permissions
2. Verify the correct AWS region is set
3. Check CloudTrail for API calls

### If you see "179 errors":
1. Check AWS Bedrock model access in your region
2. Verify Bedrock permissions for Claude and Titan models
3. Check the logs for specific error messages

## AWS Permissions Required

Your AWS credentials need:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "transcribe:StartTranscriptionJob",
                "transcribe:GetTranscriptionJob",
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject"
            ],
            "Resource": "*"
        }
    ]
}
```

## Success Indicators

✅ **Video processing completes without errors**
✅ **AWS Transcribe jobs visible in console**
✅ **AWS Bedrock usage in billing/CloudTrail**
✅ **Proper transcription and caption results**
✅ **No OpenAI API calls**

The system will now use **only AWS services** for video processing as requested!