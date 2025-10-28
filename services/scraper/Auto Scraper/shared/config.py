import os
from pathlib import Path

_DEFAULT_SERVICE_ACCOUNT = Path(__file__).resolve().parents[5] / "secrets" / "gcp.json"


def _resolve_service_account_path() -> Path:
    """Determine the service account path from env vars or defaults."""
    configured_path = (
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        or os.environ.get("GEMINI_SERVICE_ACCOUNT_PATH")
        or os.environ.get("GCP_SERVICE_ACCOUNT_PATH")
    )

    if configured_path:
        path = Path(configured_path).expanduser()
    else:
        path = _DEFAULT_SERVICE_ACCOUNT

    if not path.is_absolute():
        path = (Path(__file__).resolve().parent / path).resolve()
    else:
        path = path.resolve()

    return path


def get_api_key(silent: bool = False) -> Path:
    """Load the GCP service account and configure environment variables."""
    service_account_path = _resolve_service_account_path()

    if not service_account_path.exists():
        print(f"❌ Service account file not found: {service_account_path}")
        print("\nPlease either:")
        print("1. Set GOOGLE_APPLICATION_CREDENTIALS to the service account path")
        print("2. Place the service account JSON at ../../../secrets/gcp.json")
        exit(1)

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(service_account_path)
    os.environ["GEMINI_SERVICE_ACCOUNT_PATH"] = str(service_account_path)

    if not silent:
        print(f"✓ Loaded service account credentials from: {service_account_path}")

    return service_account_path
