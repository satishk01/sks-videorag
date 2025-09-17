#!/usr/bin/env python3
"""Test AWS video processing functionality."""

import sys
import os
import requests
import json
import time

def test_video_processing():
    """Test the complete video processing pipeline."""
    print("🧪 Testing AWS Video Processing...")
    
    # Test API connectivity
    try:
        response = requests.get("http://localhost:8080")
        if response.status_code == 200:
            print("✅ API service is accessible")
        else:
            print("❌ API service not responding properly")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        return False
    
    # Test MCP connectivity
    try:
        response = requests.get("http://localhost:9090/mcp")
        if response.status_code in [200, 405]:  # 405 is OK for MCP endpoint
            print("✅ MCP service is accessible")
        else:
            print("❌ MCP service not responding properly")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to MCP: {e}")
        return False
    
    # Test video upload (if you have a test video)
    test_video_path = "shared_media/test_video.mp4"
    if os.path.exists(test_video_path):
        print(f"📹 Found test video: {test_video_path}")
        
        try:
            # Upload video
            with open(test_video_path, 'rb') as f:
                files = {'file': f}
                response = requests.post("http://localhost:8080/upload-video", files=files)
            
            if response.status_code == 200:
                print("✅ Video upload successful")
                
                # Process video
                video_data = response.json()
                video_path = video_data.get('video_path')
                
                if video_path:
                    process_data = {"video_path": video_path}
                    response = requests.post("http://localhost:8080/process-video", json=process_data)
                    
                    if response.status_code == 200:
                        task_data = response.json()
                        task_id = task_data.get('task_id')
                        print(f"✅ Video processing started (Task ID: {task_id})")
                        
                        # Check task status
                        for i in range(30):  # Wait up to 5 minutes
                            time.sleep(10)
                            status_response = requests.get(f"http://localhost:8080/task-status/{task_id}")
                            if status_response.status_code == 200:
                                status_data = status_response.json()
                                status = status_data.get('status')
                                print(f"📊 Task status: {status}")
                                
                                if status == 'completed':
                                    print("✅ Video processing completed successfully!")
                                    return True
                                elif status == 'failed':
                                    print("❌ Video processing failed")
                                    return False
                        
                        print("⏰ Video processing timeout")
                        return False
                    else:
                        print("❌ Failed to start video processing")
                        return False
            else:
                print("❌ Video upload failed")
                return False
                
        except Exception as e:
            print(f"❌ Video processing test error: {e}")
            return False
    else:
        print("📹 No test video found - skipping video processing test")
        print("   Place a test video at 'shared_media/test_video.mp4' to test processing")
    
    print("✅ Basic connectivity tests passed")
    return True

if __name__ == "__main__":
    success = test_video_processing()
    if success:
        print("\n🎯 AWS Video Processing Test: PASSED")
        sys.exit(0)
    else:
        print("\n❌ AWS Video Processing Test: FAILED")
        sys.exit(1)