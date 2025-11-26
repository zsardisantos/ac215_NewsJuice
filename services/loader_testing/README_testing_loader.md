# Loader testing workflow

The base version of the loader service is in "loader_deployed".
In this "loader_testing" folder, a test suit has been added.
In the final version both folders will be integrated into a version that can be used in development/testing and production.

Tests covered:
- Black + Flake8 (with container)
- Black and Flake8 (direct, without container)
- Pytest (unit, integration and system)
- GitHub Actions CI workflow


Files testet (in **src/api-service/api/**)
- main.py
- loader.py

Test files in **/tests/**


## Instructions:


Go into folder: services/loader_testing

### Black + Flake 8 (with container)

Build development image
```bash
docker build -f Dockerfile.dev -t loader-app-api:dev .
```

Run Black inside container, but write changes by Black to local files
```bash
docker run --rm \
  -v $(pwd)/src/api-service/api:/app/api \
  loader-app-api:dev \
  black api/
```
This does
* The container mounts your local API folder at /app/api
* Black runs inside the container using uv’s dependencies
* Black formats the files in the mounted volume
* The changes appear instantly on local machine

Similarly, run the image for Flake8:
```bash
docker run --rm \
  -v $(pwd)/src/api-service/api:/app/api \
  loader-app-api:dev \
  flake8 api/
  ```
Rebuild after modifications by black
```bash
docker build -f Dockerfile.dev -t loader-app-api:dev .
```
Check with black - should now be clean
```bash
docker run --rm loader-app-api:dev black --check api/
```

### Black and Flake8 (direct, without container)

Let black reformat
```bash
black src/api-service/api/
```
Check code quality with flake
```bash
flake8 src/api-service/api/
```

### Testing with pytest

#### Unit tests

Move into the folder **services/loader_testing**

Execute the unit tests in **tests/unit/\***
```bash
uv sync --extra dev
```

```bash
DATABASE_URL="postgresql://test:test@localhost:5432/testdb" \
GOOGLE_CLOUD_PROJECT="test-project" \
uv run python -m pytest tests/unit/ -v --cov=api --cov-report=html
```

Get the report:
```bash
open htmlcov/index.html
```


### Integration tests

Integration test (no container)

```bash
DATABASE_URL="postgresql://dummy" GOOGLE_CLOUD_PROJECT="test-project" \
  uv run python -m pytest tests/integration/ -v --cov-fail-under=50
```

Integration test (container)

Build the image first
```bash
docker build -t loader-app-api:dev .
```
Run integration tests only
```bash
docker run --rm \
  -e DATABASE_URL="postgresql://dummy" \
  -e GOOGLE_CLOUD_PROJECT="test-project" \
  loader-app-api:dev \
  pytest tests/integration/ -v
```

### System tests

Need to use a real DB now.

- Use a docker-compose (docker-compose.test.yml) as we need to spin up DB for testing
and also initialize tables.
- Initialization uses tests/setup/init_test_db.sql to create tables in temporary local DB
- Uses real VertexAI calls for embeddings.

Authenticate (if not already done)
```bash
gcloud auth application-default login
```
Verify credentials exist
```bash
ls -la ~/.config/gcloud/application_default_credentials.json
```
Clean up and start fresh
```bash
docker-compose -f docker-compose.test.yml down -v  # ← The -v removes volumes
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

```
✅ Tests with real Google Cloud Vertex AI embeddings
✅ Validates the complete end-to-end pipeline
✅ Shows you the actual embedding values
✅ Runs in isolated Docker environment
```


## GitHub Actions CI workflow

### Systems test
- Locally: use real VertexAI calls (environmental variable)  
- CI: use mocked VertexAI calls  

Have two docker-compose files:   
- **docker-compose.test**  
- **docker-compose.test-ci** (for mocked system test)  

Set **USE_MOCKED_AI=true**
```bash
USE_MOCKED_AI=true docker-compose -f docker-compose.test-ci.yml up --build --abort-on-container-exit
```
Don't set USE_MOCKED_AI, defaults to real
```bash
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
```
Test locally with mock AI
```bash
cd services/loader_testing
docker-compose -f docker-compose.test-ci.yml up --build --abort-on-container-exit
```

Use **.github/workflows/ci_full.yaml** file (IN PROJECT ROOT)  

Whenever there is a change in the files specified in ci.yaml (currently only loader.py and main.py in loader_testing) and a push being executed, then GitHub Actions workflow with unit and integration tests are triggered.
Go to GitHub->Actions to the the workflow in action, with logs and outcome (should be gree tick)


## APPENDIX/NOTES

Set up SA and credentials

Create service account
```bash
gcloud iam service-accounts create github-actions-ci \
  --display-name="GitHub Actions CI" \
  --project=newsjuice-123456
```
Grant necessary permissions
```bash
gcloud projects add-iam-policy-binding newsjuice-123456 \
  --member="serviceAccount:github-actions-ci@newsjuice-123456.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```
Create and download key
```bash
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=github-actions-ci@newsjuice-123456.iam.gserviceaccount.com
```
Paste the key to the Clipboard
```bash
cat github-actions-key.json | pbcopy
```

Add Secret to GitHub  

Go to your GitHub repo → Settings → Secrets and variables → Actions  
Click "New repository secret"  
Name: GCP_SA_KEY  
Value: Paste the entire contents of github-actions-key.json  


Start the API server
```bash
docker run -d --name api-server -p 8080:8080 -e DEV=1 loader-app-api:local
```
Run system tests against the live server
```bash
docker run --rm --network host loader-app-api:local pytest tests/system/ -v
```
Clean up when done
```bash
docker stop api-server && docker rm api-server
```

Test directly:
Run with pytest (standard way)  
```bash
uv run pytest tests/integration/test_api_simple.py -v
```


## Required Files Structure
```
services/loader_testing/
├── .github/
│   └── workflows/
│       └── ci_full.yml                          # ← This file above
├── src/
│   └── api-service/
│       └── api/
│           ├── __init__.py
│           ├── loader.py
│           └── main.py
├── tests/
│   ├── unit/
│   │   └── test_utils.py
|   |   |__ test_main_api.py
|   |   |__ test_database_manager-py
|   |   |__ test_article_processing_and_orchestrator.py 
│   ├── integration/
│   │   └── test_api_simple.py
│   ├── system/
│   │   └── test_loader_system.py          # ← Modified with USE_MOCKED_AI support
│   └── setup/
│       └── init_test_db.sql
├── docker-compose.test.yml                 # ← Original (real AI, local use)
├── docker-compose.test-ci.yml              # ← New (mocked AI, CI use)
├── Dockerfile
├── pyproject.toml
├── uv.lock
├── pytest.ini
└── .flake8
```

## Execution Flow Visualization
```
┌─────────────────────────────────────────────────────────┐
│                    PUSH / PULL REQUEST                  │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │   🔍 LINT    │ (Black + Flake8)
                  └──────┬───────┘
                         │
            ┌────────────┴────────────┐
            │                         │
            ▼                         ▼
     ┌──────────────┐          ┌──────────────┐
     │ 🧪 UNIT TESTS│          │ 🔗 INTEGRATION│
     │  (Coverage)  │          │   (DB Mock)  │
     └──────┬───────┘          └──────┬───────┘
            │                         │
            └────────────┬────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ 🚀 SYSTEM    │ (Full Stack + Mocked AI)
                  │    TESTS     │ (Docker Compose)
                  └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ 📊 SUMMARY   │ (Results + PR Comment)
                  └──────────────┘