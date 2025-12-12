import pytest
import httpx
import os
import time


class TestLoaderAPI:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.base_url = os.environ.get("LOADER_URL", "http://localhost:8080")
        self.client = httpx.Client(base_url=self.base_url, timeout=60.0)
        self._wait_for_service()
        yield
        self.client.close()

    def _wait_for_service(self, max_attempts=30):
        for attempt in range(max_attempts):
            try:
                response = self.client.get("/")
                if response.status_code == 200:
                    return
            except httpx.RequestError:
                pass
            time.sleep(1)
        pytest.fail(f"Service not ready after {max_attempts} seconds")

    def test_health_endpoint(self):
        response = self.client.get("/")
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_process_endpoint(self):
        response = self.client.post("/process")
        
        assert response.status_code == 200
        assert response.json()["status"] == "started"

    