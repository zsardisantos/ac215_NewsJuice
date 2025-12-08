# CI/CD set up and workflow

Approach. Instead of manual execution of deployement container automate

| Manual | CI/CD |
|-------|-------|
| `./docker-shell.sh` | GitHub builds same container |
| Mount `../../../secrets/` | Write secret to `/tmp/` |
| Interactive shell | Run `pulumi up --yes` directly |
| Manual `pulumi up` | Automatic after tests pass |



You still need `docker-shell.sh` for local development. The CI/CD workflow replicates what it does, but they serve different purposes:

| File | Purpose | When used |
|------|---------|-----------|
| `docker-shell.sh` | Local development & manual deploys | On your laptop |
| `.github/workflows/ci-cd.yaml` | Automated deploys | On GitHub (after push) |

They do the same thing differently:

| What | `docker-shell.sh` | CI/CD workflow |
|------|-------------------|----------------|
| Build container | `docker build -t $IMAGE_NAME` | `docker build -t newsjuice-deployment` |
| Mount secrets | `-v "$SECRETS_DIR":/secrets` | Write `${{ secrets.GCP_SA_KEY }}` to `/tmp/` |
| Mount code | `-v "$BASE_DIR/../loader_deployed":/loader_deployed` | `-v ${{ github.workspace }}/services/loader_deployed:/loader_deployed` |
| Run | Interactive shell → manual `pulumi up` | Direct `pulumi up --yes` |

**Keep both because:**

1. **Local development** - You still want to run `./docker-shell.sh` to:
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

So keep `docker-shell.sh` - it's your local toolbox.


## File structure for CI/CD deployment

Files to create
1. .github/workflows/ci-cd.yaml  
2. services/loader_testing/pytest.ini  
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
## 