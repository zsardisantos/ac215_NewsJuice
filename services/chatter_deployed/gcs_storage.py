"""Google Cloud Storage helper for uploading audio files."""
import os
from google.cloud import storage
from typing import Optional
import uuid
from datetime import datetime


def upload_audio_to_gcs(audio_bytes: bytes, user_id: str, filename_prefix: str = "daily-brief") -> Optional[str]:
    """
    Upload audio bytes to Google Cloud Storage and return public URL.
    
    Args:
        audio_bytes: WAV audio file as bytes
        user_id: User ID for organizing files
        filename_prefix: Prefix for the filename (e.g., "daily-brief")
    
    Returns:
        Public URL to the uploaded file, or None if upload fails
    """
    try:
        bucket_name = os.environ.get("AUDIO_BUCKET", "newsjuice-123456-audio-bucket")
        gcs_prefix = os.environ.get("GCS_PREFIX", "podcasts/")
        cache_control = os.environ.get("CACHE_CONTROL", "public, max-age=3600")
        
        print(f"[gcs] Uploading to bucket: {bucket_name}, prefix: {gcs_prefix}")
        
        # Use default credentials (Workload Identity in GKE, ADC elsewhere)
        client = storage.Client()
        print("[gcs] Using default credentials")
        
        bucket = client.bucket(bucket_name)
        
        # Generate unique filename: podcasts/daily-brief/{user_id}/{timestamp}_{uuid}.wav
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        blob_path = f"{gcs_prefix}{filename_prefix}/{user_id}/{timestamp}_{unique_id}.wav"
        
        print(f"[gcs] Uploading to path: {blob_path}")
        
        # Create blob and upload
        blob = bucket.blob(blob_path)
        blob.upload_from_string(audio_bytes, content_type="audio/wav")
        
        # Set cache control
        blob.cache_control = cache_control
        blob.patch()
        
        # Return public URL (bucket IAM allows allUsers:objectViewer)
        public_url = f"https://storage.googleapis.com/{bucket_name}/{blob_path}"
        
        print(f"[gcs] Uploaded audio successfully: {public_url}")
        return public_url
        
    except Exception as e:
        print(f"[gcs-error] Failed to upload audio: {e}")
        import traceback
        traceback.print_exc()
        return None
        