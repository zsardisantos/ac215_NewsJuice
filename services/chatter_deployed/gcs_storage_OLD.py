"""Google Cloud Storage helper for uploading audio files.

FUNCTIONS CONTAINED:

upload_audio_to_gcs(audio_bytes: bytes, user_id: str, filename_prefix: str = "daily-brief") -> Optional[str]:
    Upload audio bytes to Google Cloud Storage and return public URL.
"""

import os
from google.cloud import storage
from google.oauth2 import service_account
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
        bucket_name = os.environ.get("AUDIO_BUCKET", "ac215-audio-bucket")
        gcs_prefix = os.environ.get("GCS_PREFIX", "podcasts/")
        cache_control = os.environ.get("CACHE_CONTROL", "public, max-age=3600")
        
        print(f"[gcs] Uploading to bucket: {bucket_name}, prefix: {gcs_prefix}")
        
        # Initialize GCS client with explicit credentials
        # Use the main service account (sa-key.json) instead of ADC
        # Note: main.py overrides GOOGLE_APPLICATION_CREDENTIALS to gemini-service-account,
        # so we need to use the original sa-key.json path directly
        sa_key_path = "/app/sa-key.json"  # Original service account path from docker-compose
        if os.path.exists(sa_key_path):
            # Use explicit service account credentials
            credentials = service_account.Credentials.from_service_account_file(sa_key_path)
            client = storage.Client(credentials=credentials, project=os.environ.get("GOOGLE_CLOUD_PROJECT", "newsjuice-123456"))
            print(f"[gcs] Using service account from: {sa_key_path}")
        else:
            # Fallback to ADC (might not work if main.py overrode it)
            client = storage.Client()
            print("[gcs] Using Application Default Credentials (fallback)")
        
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
        
        # Generate a signed URL (valid for 1 day) since uniform bucket-level access is enabled
        # Signed URLs work even when ACLs are disabled
        from datetime import timedelta
        expiration = timedelta(days=1)  # URL valid for 1 day
        
        # Get credentials for signing
        if sa_key_path and os.path.exists(sa_key_path):
            credentials = service_account.Credentials.from_service_account_file(sa_key_path)
        else:
            # Fallback: try to get credentials from client
            credentials = client._credentials
        
        signed_url = blob.generate_signed_url(
            expiration=expiration,
            method='GET',
            credentials=credentials
        )
        
        print(f"[gcs] Uploaded audio successfully: {signed_url}")
        return signed_url
        
    except Exception as e:
        print(f"[gcs-error] Failed to upload audio: {e}")
        import traceback
        traceback.print_exc()
        return None

