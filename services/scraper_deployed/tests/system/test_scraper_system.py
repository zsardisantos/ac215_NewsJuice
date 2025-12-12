import pytest
import httpx
import os
import time


@pytest.mark.system
class TestScraperSystem:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.base_url = os.environ.get("SCRAPER_URL", "http://localhost:8080")
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
        """Test the health check endpoint"""
        response = self.client.get("/")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_process_endpoint(self):
        """Test the async process endpoint starts correctly"""
        # Note: This just triggers the background task.
        # In a real system test we might want to wait and check DB side effects,
        # but here we just verify the API contract.
        response = self.client.post("/process")

        assert response.status_code == 200
        assert response.json()["status"] == "started"

    # Note: process-sync might take too long for a default test if it actually scrapes.
    # We can skip it or run it depending on if we have mocked the scrapers or not.
    # Since this is a "System Test" it usually runs against the real thing, but
    # the real scrapers need internet access and time.
    # For now, we will verify the endpoint exists and returns 200 (or errors gracefully if no config).
    # If the docker container has no internet or valid credentials, it might fail.
