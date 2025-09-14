"""AWS Transcribe provider implementation."""

import json
import time
import uuid
from typing import Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from loguru import logger

from .base import ProviderError, ProviderUnavailableError, TranscriptionProvider, TranscriptionResponse


class AWSTranscribeError(ProviderError):
    """AWS Transcribe-specific errors."""
    pass


class AWSTranscribeProvider(TranscriptionProvider):
    """AWS Transcribe provider for audio transcription operations."""
    
    def __init__(self, region: str = "us-east-1", s3_bucket: Optional[str] = None):
        self.region = region
        self.s3_bucket = s3_bucket or f"kubrick-transcribe-{region}-{uuid.uuid4().hex[:8]}"
        self.transcribe_client = None
        self.s3_client = None
        self._initialized = False
        self._bucket_created = False
    
    async def initialize(self) -> None:
        """Initialize the AWS Transcribe and S3 clients."""
        try:
            self.transcribe_client = boto3.client("transcribe", region_name=self.region)
            self.s3_client = boto3.client("s3", region_name=self.region)
            
            # Create S3 bucket if it doesn't exist
            await self._ensure_s3_bucket()
            
            self._initialized = True
            logger.info(f"AWS Transcribe provider initialized in region {self.region}")
        except (ClientError, NoCredentialsError) as e:
            logger.error(f"Failed to initialize AWS Transcribe provider: {e}")
            raise AWSTranscribeError("aws-transcribe", f"Failed to initialize: {str(e)}", e)
    
    def is_available(self) -> bool:
        """Check if the provider is available."""
        return (self.transcribe_client is not None and 
                self.s3_client is not None and 
                self._initialized and 
                self._bucket_created)
    
    async def _ensure_s3_bucket(self) -> None:
        """Ensure S3 bucket exists for storing audio files."""
        try:
            # Check if bucket exists
            self.s3_client.head_bucket(Bucket=self.s3_bucket)
            self._bucket_created = True
            logger.info(f"Using existing S3 bucket: {self.s3_bucket}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Bucket doesn't exist, create it
                try:
                    if self.region == 'us-east-1':
                        # us-east-1 doesn't need LocationConstraint
                        self.s3_client.create_bucket(Bucket=self.s3_bucket)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.s3_bucket,
                            CreateBucketConfiguration={'LocationConstraint': self.region}
                        )
                    
                    # Set bucket lifecycle to delete objects after 1 day
                    self.s3_client.put_bucket_lifecycle_configuration(
                        Bucket=self.s3_bucket,
                        LifecycleConfiguration={
                            'Rules': [
                                {
                                    'ID': 'DeleteTempAudioFiles',
                                    'Status': 'Enabled',
                                    'Expiration': {'Days': 1},
                                    'Filter': {'Prefix': 'temp-audio/'}
                                }
                            ]
                        }
                    )
                    
                    self._bucket_created = True
                    logger.info(f"Created S3 bucket: {self.s3_bucket}")
                except ClientError as create_error:
                    logger.error(f"Failed to create S3 bucket: {create_error}")
                    raise AWSTranscribeError("aws-transcribe", f"Failed to create S3 bucket: {str(create_error)}", create_error)
            else:
                logger.error(f"Error checking S3 bucket: {e}")
                raise AWSTranscribeError("aws-transcribe", f"S3 bucket error: {str(e)}", e)
    
    async def transcribe_audio(self, audio: bytes, model: str) -> TranscriptionResponse:
        """Transcribe audio using AWS Transcribe."""
        if not self.is_available():
            raise ProviderUnavailableError("aws-transcribe", "Provider not initialized")
        
        job_name = f"kubrick-transcribe-{uuid.uuid4().hex}"
        s3_key = f"temp-audio/{job_name}.mp3"
        
        try:
            # Upload audio to S3
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=audio,
                ContentType='audio/mpeg'
            )
            logger.info(f"Uploaded audio to S3: s3://{self.s3_bucket}/{s3_key}")
            
            # Start transcription job
            media_uri = f"s3://{self.s3_bucket}/{s3_key}"
            
            self.transcribe_client.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={'MediaFileUri': media_uri},
                MediaFormat='mp3',
                LanguageCode='en-US',  # Default to English, could be configurable
                Settings={
                    'ShowSpeakerLabels': False,
                    'MaxSpeakerLabels': 2
                }
            )
            
            logger.info(f"Started transcription job: {job_name}")
            
            # Wait for job completion
            transcript_text = await self._wait_for_transcription_job(job_name)
            
            # Clean up S3 object (optional, lifecycle policy will handle it)
            try:
                self.s3_client.delete_object(Bucket=self.s3_bucket, Key=s3_key)
            except Exception as e:
                logger.warning(f"Failed to delete S3 object {s3_key}: {e}")
            
            return TranscriptionResponse(
                text=transcript_text,
                language="en-US",
                provider="aws-transcribe"
            )
            
        except ClientError as e:
            logger.error(f"AWS Transcribe API error: {e}")
            raise AWSTranscribeError("aws-transcribe", f"Transcription API error: {str(e)}", e)
        except Exception as e:
            logger.error(f"Unexpected error in AWS Transcribe provider: {e}")
            raise AWSTranscribeError("aws-transcribe", f"Unexpected error: {str(e)}", e)
    
    async def _wait_for_transcription_job(self, job_name: str, max_wait_time: int = 300) -> str:
        """Wait for transcription job to complete and return the transcript."""
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                response = self.transcribe_client.get_transcription_job(
                    TranscriptionJobName=job_name
                )
                
                status = response['TranscriptionJob']['TranscriptionJobStatus']
                
                if status == 'COMPLETED':
                    # Get transcript from the results
                    transcript_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
                    transcript_text = await self._download_transcript(transcript_uri)
                    
                    # Clean up the transcription job
                    try:
                        self.transcribe_client.delete_transcription_job(
                            TranscriptionJobName=job_name
                        )
                    except Exception as e:
                        logger.warning(f"Failed to delete transcription job {job_name}: {e}")
                    
                    return transcript_text
                
                elif status == 'FAILED':
                    failure_reason = response['TranscriptionJob'].get('FailureReason', 'Unknown error')
                    raise AWSTranscribeError("aws-transcribe", f"Transcription job failed: {failure_reason}")
                
                # Job is still in progress, wait before checking again
                await self._async_sleep(5)
                
            except ClientError as e:
                logger.error(f"Error checking transcription job status: {e}")
                raise AWSTranscribeError("aws-transcribe", f"Job status check error: {str(e)}", e)
        
        # Timeout reached
        raise AWSTranscribeError("aws-transcribe", f"Transcription job {job_name} timed out after {max_wait_time} seconds")
    
    async def _download_transcript(self, transcript_uri: str) -> str:
        """Download and parse the transcript from the given URI."""
        import urllib.request
        
        try:
            with urllib.request.urlopen(transcript_uri) as response:
                transcript_data = json.loads(response.read().decode('utf-8'))
            
            # Extract the transcript text
            transcript_text = transcript_data['results']['transcripts'][0]['transcript']
            return transcript_text
            
        except Exception as e:
            logger.error(f"Failed to download transcript from {transcript_uri}: {e}")
            raise AWSTranscribeError("aws-transcribe", f"Transcript download error: {str(e)}", e)
    
    async def _async_sleep(self, seconds: int) -> None:
        """Async sleep helper."""
        import asyncio
        await asyncio.sleep(seconds)