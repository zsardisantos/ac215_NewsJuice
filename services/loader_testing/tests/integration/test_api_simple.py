"""
Integration Tests for Article Loader API
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# ============= SET ENV VARS BEFORE IMPORTING =============
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "test-project")
os.environ.setdefault("GOOGLE_CLOUD_REGION", "us-central1")

# Add api-service directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src", "api-service"))

# ============= NOW IMPORT THE APP =============
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


class TestBasicFunctionality:

    def test_health_check(self):
        """TEST 1: Health Check Endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"
        print("✓ Health check passed!")

    @patch("api.main.chunk_embed_load")  # ← Changed from "main.chunk_embed_load"
    def test_background_processing(self, mock_chunk_embed_load):
        """TEST 2: Background Processing Endpoint"""
        response = client.post("/process")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        print("✓ Background processing started!")

    @patch("api.main.chunk_embed_load")  # ← Changed from "main.chunk_embed_load"
    def test_sync_processing_success(self, mock_chunk_embed_load):
        """TEST 3: Synchronous Processing - Success"""
        mock_chunk_embed_load.return_value = {
            "status": "success",
            "message": "Processed 3 articles",
            "processed": 3,
            "total_found": 3
        }

        response = client.post("/process-sync")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["processed"] == 3
        mock_chunk_embed_load.assert_called_once_with(method="recursive-split")
        print("✓ Sync processing success!")

    @patch("api.main.chunk_embed_load")  # ← Changed from "main.chunk_embed_load"
    def test_sync_processing_error(self, mock_chunk_embed_load):
        """TEST 4: Error Handling"""
        mock_chunk_embed_load.side_effect = Exception("Database connection failed")

        response = client.post("/process-sync")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "Database connection failed" in data["message"]
        print("✓ Error handling works!")
