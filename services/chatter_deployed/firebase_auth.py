import firebase_admin
from firebase_admin import auth
from typing import Dict

"""Firebase Admin SDK initialization and token verification."""

"""
FUNCTIONS CONTAINED:

initialize_firebase_admin()   ---- called by main.py
verify_token(token: str) -> Dict --- called by main.py

"""


def initialize_firebase_admin():
    """Initialize Firebase Admin SDK."""
    # Check if already initialized
    if len(firebase_admin._apps) > 0:
        print("[firebase-admin] Already initialized")
        return

    # service account JSON file for the local development
    # [CM] strange that his works? the path in .env.local seems a dummy
    # [Z] we do not need this code below, it works because when the backend
    # is deployed on Cloud Run, we do not use the
    # service account (which is a dummy path),
    # so the Firebase falls back on the Application Default Credentials (ADC)
    # AKA the firebase service account file inside our GCP IAM
    # service accounts folder
    # that is what the firebase_admin.initialize_app() does.

    # service_account_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")
    # if service_account_path and os.path.exists(service_account_path):
    #     cred = credentials.Certificate(service_account_path)
    #     firebase_admin.initialize_app(cred)
    #     print("[firebase-admin] Initialized with service account file")
    #     return

    # this is firebase authorization for the cloud deployment
    try:
        firebase_admin.initialize_app()
        print("[firebase-admin] Initialized with default credentials")
    except Exception as e:
        print(f"[firebase-admin-error] Failed to initialize: {e}")
        raise


def verify_token(token: str) -> Dict:
    """
    Verify the Firebase ID token and return the decoded token.

    Args:
        token: Firebase ID token string

    Returns:
        Decoded token dictionary containing user data (uid, email, etc.)

    Raises:
        Exception: If token is invalid or expired
    """
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        print(f"[firebase-admin-error] Token verification failed: {e}")
        raise
