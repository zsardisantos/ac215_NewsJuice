import pytest
import httpx
import os
import time


@pytest.mark.system
class TestChatterSystem:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.base_url = os.environ.get("CHATTER_URL", "http://localhost:8080")
        self.client = httpx.Client(base_url=self.base_url, timeout=60.0)
        self._wait_for_service()
        yield
        self.client.close()

    def _wait_for_service(self, max_attempts=30):
        for attempt in range(max_attempts):
            try:
                response = self.client.get("/health")
                if response.status_code == 200:
                    return
            except httpx.RequestError:
                pass
            time.sleep(1)
        pytest.fail(f"Service not ready after {max_attempts} seconds")

    def test_health_endpoint(self):
        """Test the health check endpoint"""
        response = self.client.get("/health")

        assert response.status_code == 200
        assert response.json()["ok"] is True
