# CI/CD set up and workflow

Approach of CI/CD for deployment/production. 
Instead of manual execution of deployement container (pulumi, kubernetes) automate this with GitHub Actions.

| Manual | CI/CD |
|-------|-------|
| `./docker-shell.sh` | GitHub builds same container |
| Mount `../../../secrets/` | Write secret to `/tmp/` |
| Interactive shell | Run `pulumi up --yes` directly |
| Manual `pulumi up` | Automatic after tests pass |



Still need `docker-shell.sh` for local development.   
The CI/CD workflow replicates what it does, but they serve different purposes:  

| File | Purpose | When used |
|------|---------|-----------|
| `docker-shell.sh` | Local development & manual deploys | On laptop |
| `.github/workflows/ci-cd.yaml` | Automated deploys | On GitHub (after push) |

They do the same thing differently:

| What | `docker-shell.sh` | CI/CD workflow |
|------|-------------------|----------------|
| Build container | `docker build -t $IMAGE_NAME` | `docker build -t newsjuice-deployment` |
| Mount secrets | `-v "$SECRETS_DIR":/secrets` | Write `${{ secrets.GCP_SA_KEY }}` to `/tmp/` |
| Mount code | `-v "$BASE_DIR/../loader_deployed":/loader_deployed` | `-v ${{ github.workspace }}/services/loader_deployed:/loader_deployed` |
| Run | Interactive shell → manual `pulumi up` | Direct `pulumi up --yes` |

**Keep both because:**

1. **Local development** - still want to run `./docker-shell.sh` to:
   - Test Pulumi changes before pushing
   - Debug deployment issues
   - Run `pulumi preview` manually
   - Access the cluster with `kubectl`

2. **CI/CD** - Automates deployment after tests pass, but you can't interactively debug there

**Typical workflow:**
```
1. Make changes locally
2. ./docker-shell.sh → pulumi preview  (check what will change)
3. git push                            (triggers CI/CD)
4. CI runs tests → pulumi up --yes     (automatic deploy)
```

So keep `docker-shell.sh` - it's a local toolbox.


## File structure for CI/CD deployment

Files to create (FOR EACH SERVICE TO TEST - here only for LOADER as example)  

1. .github/workflows/ci-cd.yaml  
2. services/loader_testing/pytest.ini   (NOT NEEDED WITH PYPROJECT.TOML)
3. services/loader_testing/pyproject.toml  
4. services/loader_testing/tests/__init__.py (EMPTY, just a package marker)  
5. services/loader_testing/tests/conftest.py  
6. services/loader_testing/tests/setup/init_test_db.sql
7. services/loader_testing/tests/unit/__init__.py  (EMPTY, just a package marker)  
8. services/loader_testing/tests/unit/test_chunking.py  
9. services/loader_testing/tests/integration/__init__.py  (EMPTY, just a package marker)    
10. services/loader_testing/tests/integration/test_database.py  
11. services/loader_testing/tests/system/__init__.py   (EMPTY, just a package marker)    
12. services/loader_testing/tests/system/test_loader_api.py   
13. services/loader_testing/docker-compose.test.yml  
14. services/loader_testing/Dockerfile.test  


```

ac215_NewsJuice/
├── .github/
│   └── workflows/
│       └── ci-cd.yaml                    # Main CI/CD workflow
├── services/
│   ├── loader_deployed/
│   │   ├── loader.py
│   │   ├── loader_modular.py
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── loader_testing/
│   │   ├── pytest.ini
│   │   ├── requirements-test.txt
│   │   ├── docker-compose.test.yml
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── conftest.py               # Shared fixtures
│   │       ├── setup/
│   │       │   └── init_test_db.sql
│   │       ├── unit/
│   │       │   ├── __init__.py
│   │       │   └── test_chunking.py
│   │       ├── integration/
│   │       │   ├── __init__.py
│   │       │   └── test_database.py
│   │       └── system/
│   │           ├── __init__.py
│   │           └── test_loader_api.py
│   ├── scraper_deployed/
│   │   └── ...
│   ├── scraper_testing/
│   │   └── ... (same structure as loader_testing)
│   ├── chatter_deployed/
│   │   └── ...
│   └── deployment/
│       ├── Dockerfile
│       ├── docker-shell.sh
│       ├── docker-entrypoint.sh
│       ├── __main__.py
│       └── Pulumi.yaml

```

Files to Create
1. **.github/workflows/ci-cd.yaml**

```bash
name: NewsJuice CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  GCP_PROJECT: newsjuice-123456
  GCP_REGION: us-central1
  GCP_ZONE: us-central1-a

jobs:
  # ============================================================
  # DETECT WHICH SERVICES CHANGED
  # ============================================================
  changes:
    runs-on: ubuntu-latest
    outputs:
      loader: ${{ steps.filter.outputs.loader }}
      scraper: ${{ steps.filter.outputs.scraper }}
      chatter: ${{ steps.filter.outputs.chatter }}
      frontend: ${{ steps.filter.outputs.frontend }}
      any_change: ${{ steps.filter.outputs.any_change }}
    steps:
      - uses: actions/checkout@v4
      
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            loader:
              - 'services/loader_deployed/**'
              - 'services/loader_testing/**'
            scraper:
              - 'services/scraper_deployed/**'
              - 'services/scraper_testing/**'
            chatter:
              - 'services/chatter_deployed/**'
            frontend:
              - 'services/frontend/**'
            any_change:
              - 'services/**'
              - 'deployment/**'

  # ============================================================
  # UNIT TESTS - Fast, no external dependencies
  # ============================================================
  unit-tests:
    runs-on: ubuntu-latest
    needs: changes
    if: needs.changes.outputs.any_change == 'true'
    
    strategy:
      fail-fast: false
      matrix:
        include:
          - service: loader
            src_dir: services/loader_deployed
            test_dir: services/loader_testing
          - service: scraper
            src_dir: services/scraper_deployed
            test_dir: services/scraper_testing

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install pytest pytest-cov
          if [ -f ${{ matrix.test_dir }}/requirements-test.txt ]; then
            pip install -r ${{ matrix.test_dir }}/requirements-test.txt
          fi
          if [ -f ${{ matrix.src_dir }}/requirements.txt ]; then
            pip install -r ${{ matrix.src_dir }}/requirements.txt
          fi

      - name: Run unit tests
        run: |
          cd ${{ matrix.test_dir }}
          pytest tests/unit/ -v --tb=short
        env:
          PYTHONPATH: ${{ github.workspace }}/${{ matrix.src_dir }}

  # ============================================================
  # INTEGRATION TESTS - With real database
  # ============================================================
  integration-tests:
    runs-on: ubuntu-latest
    needs: [changes, unit-tests]
    if: needs.changes.outputs.any_change == 'true'
    
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: testpassword
          POSTGRES_DB: newsdb_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    strategy:
      fail-fast: false
      matrix:
        include:
          - service: loader
            src_dir: services/loader_deployed
            test_dir: services/loader_testing
          - service: scraper
            src_dir: services/scraper_deployed
            test_dir: services/scraper_testing

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install PostgreSQL client
        run: sudo apt-get install -y postgresql-client

      - name: Install dependencies
        run: |
          pip install pytest
          if [ -f ${{ matrix.test_dir }}/requirements-test.txt ]; then
            pip install -r ${{ matrix.test_dir }}/requirements-test.txt
          fi
          if [ -f ${{ matrix.src_dir }}/requirements.txt ]; then
            pip install -r ${{ matrix.src_dir }}/requirements.txt
          fi

      - name: Initialize test database
        run: |
          PGPASSWORD=testpassword psql -h localhost -U postgres -d newsdb_test \
            -f ${{ matrix.test_dir }}/tests/setup/init_test_db.sql
        continue-on-error: true

      - name: Run integration tests
        run: |
          cd ${{ matrix.test_dir }}
          pytest tests/integration/ -v --tb=short
        env:
          PYTHONPATH: ${{ github.workspace }}/${{ matrix.src_dir }}
          DATABASE_URL: postgresql://postgres:testpassword@localhost:5432/newsdb_test
          ARTICLES_TABLE_NAME: articles_test
          VECTOR_TABLE_NAME: chunks_vector_test

  # ============================================================
  # SYSTEM TESTS - Full service with Docker Compose
  # ============================================================
  system-tests:
    runs-on: ubuntu-latest
    needs: [changes, integration-tests]
    if: needs.changes.outputs.any_change == 'true' && github.event_name == 'push'
    
    strategy:
      fail-fast: false
      matrix:
        include:
          - service: loader
            test_dir: services/loader_testing

    steps:
      - uses: actions/checkout@v4

      - name: Start services with Docker Compose
        run: |
          cd ${{ matrix.test_dir }}
          docker compose -f docker-compose.test.yml up -d --build
          sleep 30

      - name: Check services are running
        run: |
          cd ${{ matrix.test_dir }}
          docker compose -f docker-compose.test.yml ps

      - name: Run system tests
        run: |
          cd ${{ matrix.test_dir }}
          docker compose -f docker-compose.test.yml run --rm test-runner \
            pytest tests/system/ -v --tb=short

      - name: Show logs on failure
        if: failure()
        run: |
          cd ${{ matrix.test_dir }}
          docker compose -f docker-compose.test.yml logs

      - name: Cleanup
        if: always()
        run: |
          cd ${{ matrix.test_dir }}
          docker compose -f docker-compose.test.yml down -v

  # ============================================================
  # LINT - Code quality checks
  # ============================================================
  lint:
    runs-on: ubuntu-latest
    needs: changes
    if: needs.changes.outputs.any_change == 'true'
    
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install linters
        run: pip install ruff black

      - name: Run Ruff
        run: ruff check services/ --ignore E501 || true

      - name: Check Black formatting
        run: black --check services/ || true

  # ============================================================
  # DEPLOY - Only on push to main, after all tests pass
  # ============================================================
  deploy:
    runs-on: ubuntu-latest
    needs: [changes, unit-tests, integration-tests, system-tests, lint]
    if: |
      always() &&
      github.event_name == 'push' &&
      github.ref == 'refs/heads/main' &&
      needs.unit-tests.result == 'success' &&
      needs.integration-tests.result == 'success' &&
      (needs.system-tests.result == 'success' || needs.system-tests.result == 'skipped')

    steps:
      - uses: actions/checkout@v4

      - name: Write GCP credentials
        run: echo '${{ secrets.GCP_SA_KEY }}' > /tmp/deployment.json

      - name: Build deployment container
        run: |
          cd services/deployment
          docker build -t newsjuice-deployment --platform=linux/amd64 -f Dockerfile .

      - name: Pulumi Preview
        if: github.event_name == 'pull_request'
        run: |
          docker run --rm \
            -v /var/run/docker.sock:/var/run/docker.sock \
            -v ${{ github.workspace }}/services/deployment:/app \
            -v /tmp/deployment.json:/secrets/deployment.json:ro \
            -v ${{ github.workspace }}/services/loader_deployed:/loader_deployed \
            -v ${{ github.workspace }}/services/scraper_deployed:/scraper_deployed \
            -v ${{ github.workspace }}/services/chatter_deployed:/chatter_deployed \
            -v ${{ github.workspace }}/services/frontend/podcast-app:/frontend \
            -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/deployment.json \
            -e GCP_PROJECT=${{ env.GCP_PROJECT }} \
            -e GCP_REGION=${{ env.GCP_REGION }} \
            -e GCP_ZONE=${{ env.GCP_ZONE }} \
            -e PULUMI_BUCKET=gs://${{ env.GCP_PROJECT }}-pulumi-state-bucket \
            newsjuice-deployment \
            bash -c "pulumi stack select prod && pulumi preview"

      - name: Pulumi Up
        if: github.event_name == 'push'
        run: |
          docker run --rm \
            -v /var/run/docker.sock:/var/run/docker.sock \
            -v ${{ github.workspace }}/services/deployment:/app \
            -v /tmp/deployment.json:/secrets/deployment.json:ro \
            -v ${{ github.workspace }}/services/loader_deployed:/loader_deployed \
            -v ${{ github.workspace }}/services/scraper_deployed:/scraper_deployed \
            -v ${{ github.workspace }}/services/chatter_deployed:/chatter_deployed \
            -v ${{ github.workspace }}/services/frontend/podcast-app:/frontend \
            -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/deployment.json \
            -e GCP_PROJECT=${{ env.GCP_PROJECT }} \
            -e GCP_REGION=${{ env.GCP_REGION }} \
            -e GCP_ZONE=${{ env.GCP_ZONE }} \
            -e PULUMI_BUCKET=gs://${{ env.GCP_PROJECT }}-pulumi-state-bucket \
            newsjuice-deployment \
            bash -c "pulumi stack select prod && pulumi up --yes"

      - name: Deployment Summary
        run: |
          echo "## ✅ Deployment Complete" >> $GITHUB_STEP_SUMMARY
          echo "- **Project:** ${{ env.GCP_PROJECT }}" >> $GITHUB_STEP_SUMMARY
          echo "- **Region:** ${{ env.GCP_REGION }}" >> $GITHUB_STEP_SUMMARY
          echo "- **Commit:** ${{ github.sha }}" >> $GITHUB_STEP_SUMMARY

```
## 3. services/loader_testing/pyproject.toml  

```bash

[project]
name = "loader-testing"
version = "0.1.0"
description = "Tests for NewsJuice Loader"
requires-python = ">=3.12"

dependencies = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "httpx>=0.24.0",
    "psycopg[binary]>=3.1.0",
    "pgvector>=0.2.0",
    "pandas>=2.0.0",
    "langchain>=0.1.0",
    "langchain-text-splitters>=0.1.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
filterwarnings = ["ignore::DeprecationWarning"]

[tool.uv]
dev-dependencies = [
    "ruff>=0.1.0",
    "black>=23.0.0",
]
```

## 5. services/loader_testing/tests/conftest.py

```bash
"""
Shared pytest fixtures for all test levels
"""
import pytest
import os


@pytest.fixture(scope="session")
def db_url():
    """Database URL for tests"""
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:testpassword@localhost:5432/newsdb_test"
    )


@pytest.fixture(scope="session")
def articles_table():
    """Articles table name"""
    return os.environ.get("ARTICLES_TABLE_NAME", "articles_test")


@pytest.fixture(scope="session")
def vector_table():
    """Vector table name"""
    return os.environ.get("VECTOR_TABLE_NAME", "chunks_vector_test")


@pytest.fixture
def sample_article():
    """Sample article for testing"""
    return {
        "article_id": "test-article-123",
        "title": "Test Article Title",
        "author": "Test Author",
        "summary": "This is a test summary.",
        "content": "This is the article content. " * 100,  # ~2700 chars
        "source_link": "https://example.com/article",
        "source_type": "test",
        "vflag": 0,
    }


@pytest.fixture
def sample_long_article():
    """Longer article to test chunking"""
    paragraphs = [
        "This is paragraph one with some content about technology.",
        "This is paragraph two discussing different topics entirely.",
        "Paragraph three covers yet another subject matter.",
        "The fourth paragraph brings new information to light.",
        "Finally, paragraph five concludes the article.",
    ]
    return {
        "article_id": "test-long-article-456",
        "title": "Long Test Article",
        "author": "Test Author",
        "summary": "A longer test article.",
        "content": "\n\n".join([p * 20 for p in paragraphs]),  # ~5000 chars
        "source_link": "https://example.com/long-article",
        "source_type": "test",
        "vflag": 0,
    }
```

## 6. services/loader_testing/tests/setup/init_test_db.sql

```bash
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create test articles table
CREATE TABLE IF NOT EXISTS articles_test (
    id SERIAL PRIMARY KEY,
    article_id VARCHAR(255) UNIQUE NOT NULL,
    author VARCHAR(255),
    title TEXT,
    summary TEXT,
    content TEXT,
    source_link TEXT,
    source_type VARCHAR(50),
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP,
    vflag INTEGER DEFAULT 0
);

-- Create test chunks_vector table
CREATE TABLE IF NOT EXISTS chunks_vector_test (
    id SERIAL PRIMARY KEY,
    article_id VARCHAR(255) NOT NULL,
    author VARCHAR(255),
    title TEXT,
    summary TEXT,
    content TEXT,
    source_link TEXT,
    source_type VARCHAR(50),
    fetched_at TIMESTAMP,
    published_at TIMESTAMP,
    chunk TEXT,
    chunk_index INTEGER,
    embedding vector(768),
    FOREIGN KEY (article_id) REFERENCES articles_test(article_id) ON DELETE CASCADE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_articles_test_vflag ON articles_test(vflag);
CREATE INDEX IF NOT EXISTS idx_chunks_test_article_id ON chunks_vector_test(article_id);
```

## 10. services/loader_testing/tests/integration/test_database.py

```bash
"""
Integration tests for database operations
Requires running PostgreSQL with pgvector
"""
import pytest
import psycopg
from psycopg import sql
import os


class TestDatabaseConnection:
    """Tests for database connectivity"""

    def test_can_connect(self, db_url):
        """Should connect to database"""
        conn = psycopg.connect(db_url)
        assert conn is not None
        conn.close()

    def test_pgvector_extension_exists(self, db_url):
        """Should have pgvector extension installed"""
        conn = psycopg.connect(db_url)
        cur = conn.cursor()
        
        cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        result = cur.fetchone()
        
        assert result is not None
        cur.close()
        conn.close()


class TestArticlesTable:
    """Tests for articles table operations"""

    @pytest.fixture(autouse=True)
    def setup(self, db_url, articles_table):
        """Setup and teardown for each test"""
        self.conn = psycopg.connect(db_url, autocommit=True)
        self.cur = self.conn.cursor()
        self.table = articles_table
        yield
        # Cleanup: delete test data
        self.cur.execute(
            sql.SQL("DELETE FROM {} WHERE article_id LIKE 'test-%'").format(
                sql.Identifier(self.table)
            )
        )
        self.cur.close()
        self.conn.close()

    def test_insert_article(self, sample_article):
        """Should insert article"""
        self.cur.execute(
            sql.SQL("""
                INSERT INTO {} (article_id, title, author, content, source_link, source_type, vflag)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """).format(sql.Identifier(self.table)),
            (
                sample_article["article_id"],
                sample_article["title"],
                sample_article["author"],
                sample_article["content"],
                sample_article["source_link"],
                sample_article["source_type"],
                sample_article["vflag"],
            )
        )

        # Verify insert
        self.cur.execute(
            sql.SQL("SELECT * FROM {} WHERE article_id = %s").format(
                sql.Identifier(self.table)
            ),
            (sample_article["article_id"],)
        )
        result = self.cur.fetchone()

        assert result is not None

    def test_fetch_unprocessed_articles(self, sample_article):
        """Should fetch articles with vflag=0"""
        # Insert test article
        self.cur.execute(
            sql.SQL("""
                INSERT INTO {} (article_id, title, content, vflag)
                VALUES (%s, %s, %s, 0)
            """).format(sql.Identifier(self.table)),
            (sample_article["article_id"], sample_article["title"], sample_article["content"])
        )

        # Fetch unprocessed
        self.cur.execute(
            sql.SQL("SELECT * FROM {} WHERE vflag = 0").format(
                sql.Identifier(self.table)
            )
        )
        results = self.cur.fetchall()

        assert len(results) >= 1

    def test_update_vflag(self, sample_article):
        """Should update vflag to 1"""
        # Insert
        self.cur.execute(
            sql.SQL("""
                INSERT INTO {} (article_id, title, content, vflag)
                VALUES (%s, %s, %s, 0)
            """).format(sql.Identifier(self.table)),
            (sample_article["article_id"], sample_article["title"], sample_article["content"])
        )

        # Update vflag
        self.cur.execute(
            sql.SQL("UPDATE {} SET vflag = 1 WHERE article_id = %s").format(
                sql.Identifier(self.table)
            ),
            (sample_article["article_id"],)
        )

        # Verify
        self.cur.execute(
            sql.SQL("SELECT vflag FROM {} WHERE article_id = %s").format(
                sql.Identifier(self.table)
            ),
            (sample_article["article_id"],)
        )
        result = self.cur.fetchone()

        assert result[0] == 1


class TestChunksVectorTable:
    """Tests for chunks_vector table operations"""

    @pytest.fixture(autouse=True)
    def setup(self, db_url, articles_table, vector_table):
        """Setup and teardown"""
        self.conn = psycopg.connect(db_url, autocommit=True)
        self.cur = self.conn.cursor()
        self.articles_table = articles_table
        self.vector_table = vector_table
        
        # Insert parent article first (for FK constraint)
        self.cur.execute(
            sql.SQL("""
                INSERT INTO {} (article_id, title, content, vflag)
                VALUES ('test-parent-123', 'Parent Article', 'Content', 0)
                ON CONFLICT (article_id) DO NOTHING
            """).format(sql.Identifier(self.articles_table))
        )
        
        yield
        
        # Cleanup
        self.cur.execute(
            sql.SQL("DELETE FROM {} WHERE article_id LIKE 'test-%'").format(
                sql.Identifier(self.vector_table)
            )
        )
        self.cur.execute(
            sql.SQL("DELETE FROM {} WHERE article_id LIKE 'test-%'").format(
                sql.Identifier(self.articles_table)
            )
        )
        self.cur.close()
        self.conn.close()

    def test_insert_chunk(self):
        """Should insert chunk with embedding"""
        # Create a dummy 768-dim embedding
        embedding = [0.1] * 768

        self.cur.execute(
            sql.SQL("""
                INSERT INTO {} (article_id, chunk, chunk_index, embedding)
                VALUES (%s, %s, %s, %s)
            """).format(sql.Identifier(self.vector_table)),
            ("test-parent-123", "This is a test chunk", 0, embedding)
        )

        # Verify
        self.cur.execute(
            sql.SQL("SELECT chunk FROM {} WHERE article_id = %s").format(
                sql.Identifier(self.vector_table)
            ),
            ("test-parent-123",)
        )
        result = self.cur.fetchone()

        assert result is not None
        assert result[0] == "This is a test chunk"
```

## 12. services/loader_testing/tests/system/test_loader_api.py

```bash
"""
System tests for loader API
Requires full service running via Docker Compose
"""
import pytest
import httpx
import os
import time


class TestLoaderAPI:
    """End-to-end tests for loader service"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test client"""
        self.base_url = os.environ.get("LOADER_URL", "http://localhost:8080")
        self.client = httpx.Client(base_url=self.base_url, timeout=60.0)
        
        # Wait for service to be ready
        self._wait_for_service()
        
        yield
        
        self.client.close()

    def _wait_for_service(self, max_attempts=30):
        """Wait for service to be healthy"""
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
        """GET / should return healthy status"""
        response = self.client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_process_endpoint_returns_started(self):
        """POST /process should return started status"""
        response = self.client.post("/process")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"

    def test_process_sync_endpoint(self):
        """POST /process-sync should process and return result"""
        response = self.client.post("/process-sync", timeout=120.0)
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["success", "error"]
```

## 13. services/loader_testing/docker-compose.test.yml

```bash
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: testpassword
      POSTGRES_DB: newsdb_test
    ports:
      - "5432:5432"
    volumes:
      - ./tests/setup/init_test_db.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 10

  loader:
    build:
      context: ../loader_deployed
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    environment:
      DATABASE_URL: postgresql://postgres:testpassword@postgres:5432/newsdb_test
      ARTICLES_TABLE_NAME: articles_test
      VECTOR_TABLE_NAME: chunks_vector_test
      GOOGLE_CLOUD_PROJECT: newsjuice-123456
      GOOGLE_CLOUD_REGION: us-central1
    depends_on:
      postgres:
        condition: service_healthy

  test-runner:
    build:
      context: .
      dockerfile: Dockerfile.test
    environment:
      LOADER_URL: http://loader:8080
      DATABASE_URL: postgresql://postgres:testpassword@postgres:5432/newsdb_test
      ARTICLES_TABLE_NAME: articles_test
      VECTOR_TABLE_NAME: chunks_vector_test
    depends_on:
      - loader
      - postgres
    volumes:
      - ./tests:/app/tests
```

## 14. services/loader_testing/Dockerfile.test

```bash
FROM python:3.12-slim

WORKDIR /app

# Install test dependencies
COPY requirements-test.txt .
RUN pip install --no-cache-dir -r requirements-test.txt

# Copy tests
COPY tests/ ./tests/
COPY pytest.ini .

CMD ["pytest", "tests/", "-v"]
```

## How to Use
1. Set up GitHub Secret  
Go to your GitHub repo → Settings → Secrets and variables → Actions → New repository secret  

Name: GCP_SA_KEY  
Value: Contents of your deployment.json file  
  
2. Run Tests Locally  

```bash
# Unit tests (no dependencies)
cd services/loader_testing
pip install -r requirements-test.txt
pytest tests/unit/ -v

# Integration tests (needs PostgreSQL)
docker run -d --name test-postgres \
  -e POSTGRES_PASSWORD=testpassword \
  -e POSTGRES_DB=newsdb_test \
  -p 5432:5432 \
  pgvector/pgvector:pg16

psql -h localhost -U postgres -d newsdb_test -f tests/setup/init_test_db.sql
DATABASE_URL=postgresql://postgres:testpassword@localhost:5432/newsdb_test \
  pytest tests/integration/ -v

# System tests (full stack)
docker compose -f docker-compose.test.yml up -d
docker compose -f docker-compose.test.yml run test-runner
docker compose -f docker-compose.test.yml down -v


3. CI/CD Flow

┌─────────────────────────────────────────────────────────────────┐
│  Push to branch / Open PR                                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────┐   ┌─────────────┐   ┌──────┐                      │
│  │  Unit    │ → │ Integration │ → │ Lint │                      │
│  │  Tests   │   │   Tests     │   │      │                      │
│  └──────────┘   └─────────────┘   └──────┘                      │
│       │               │               │                          │
│       └───────────────┴───────────────┘                          │
│                       │                                          │
│                       ▼                                          │
│              ✅ All Pass = Ready to merge                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Push to main                                                    │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────┐   ┌─────────────┐   ┌────────┐   ┌─────────────┐  │
│  │  Unit    │ → │ Integration │ → │ System │ → │   Deploy    │  │
│  │  Tests   │   │   Tests     │   │ Tests  │   │ (Pulumi Up) │  │
│  └──────────┘   └─────────────┘   └────────┘   └─────────────┘  │
│                                                      │           │
│                                                      ▼           │
│                                              GKE Updated ✅      │
└─────────────────────────────────────────────────────────────────┘
```
