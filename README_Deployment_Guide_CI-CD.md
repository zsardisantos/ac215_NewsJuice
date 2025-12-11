# 🔄 CI/CD Setup and Workflow

This document is complementary to **README_Deployment_Guide_GKS-pulumi.md** and describes automated deployment via GitHub Actions.

---

## ✅ Prerequisites

### Service Account Roles

The deployment service account must have the following roles:
```bash
gcloud projects get-iam-policy newsjuice-123456 \
  --flatten="bindings[].members" \
  --filter="bindings.members:deployment@newsjuice-123456.iam.gserviceaccount.com" \
  --format="table(bindings.role)"
```

| Role |
|------|
| `roles/artifactregistry.admin` |
| `roles/compute.admin` |
| `roles/compute.osLogin` |
| `roles/container.admin` |
| `roles/editor` |
| `roles/iam.serviceAccountAdmin` |
| `roles/iam.serviceAccountUser` |
| `roles/resourcemanager.projectIamAdmin` |
| `roles/run.admin` |
| `roles/storage.admin` |

### GitHub Secret Configuration

1. Go to: https://github.com/zsardisantos/ac215_NewsJuice/settings/secrets/actions
2. Click **"New repository secret"**
3. Configure:
   - **Name:** `GCP_SA_KEY`
   - **Value:** Copy entire contents of `../secrets/deployment.json`
4. Click **"Add secret"**

> **Note:** No additional secrets needed. Pulumi uses GCS backend (not Pulumi Cloud). The `GCP_SA_KEY` secret already has `storage.admin` role, so it can read/write the Pulumi state bucket.

### Verify Pulumi State Access
```bash
root@32cc13d7288e:/app# echo $PULUMI_BUCKET
gs://newsjuice-123456-pulumi-state-bucket
```

---

## 🎯 CI/CD Approach

Instead of manual execution of the deployment container (Pulumi, Kubernetes), we automate this with GitHub Actions.

### Manual vs CI/CD Comparison

| Manual | CI/CD |
|--------|-------|
| `./docker-shell.sh` | GitHub builds same container |
| Mount `../../../secrets/` | Write secret to `/tmp/` |
| Interactive shell | Run `pulumi up --yes` directly |
| Manual `pulumi up` | Automatic after tests pass |

### When to Use Each

| File | Purpose | When Used |
|------|---------|-----------|
| `docker-shell.sh` | Local development & manual deploys | On laptop |
| `.github/workflows/ci_*.yaml` | Automated deploys | On GitHub (after push) |

### Implementation Differences

| What | `docker-shell.sh` | CI/CD Workflow |
|------|-------------------|----------------|
| Build container | `docker build -t $IMAGE_NAME` | `docker build -t newsjuice-deployment` |
| Mount secrets | `-v "$SECRETS_DIR":/secrets` | Write `${{ secrets.GCP_SA_KEY }}` to `/tmp/` |
| Mount code | `-v "$BASE_DIR/../loader_deployed":/loader_deployed` | `-v ${{ github.workspace }}/services/loader_deployed:/loader_deployed` |
| Run | Interactive shell → manual `pulumi up` | Direct `pulumi up --yes` |

### Why Keep Both?

**Local Development (`docker-shell.sh`):**
- Test Pulumi changes before pushing
- Debug deployment issues
- Run `pulumi preview` manually
- Access the cluster with `kubectl`

**CI/CD (`ci-*.yaml`):**
- Automates deployment after tests pass
- No interactive debugging available

### Typical Workflow
```
1. Make changes locally
2. ./docker-shell.sh → pulumi preview  (check what will change)
3. git push                            (triggers CI/CD)
4. CI runs tests → pulumi up --yes     (automatic deploy)
```

---

## 📁 File Structure for CI/CD

### Files to Create (per service)

> Example shown for LOADER service

| File | Purpose |
|------|---------|
| `pyproject.toml` | Dependencies + pytest config |
| `docker-compose.test.yml` | System tests stack |
| `Dockerfile.test` | Test runner container |
| `tests/__init__.py` | Package marker |
| `tests/conftest.py` | Shared fixtures |
| `tests/setup/init_test_db.sql` | DB schema |
| `tests/unit/__init__.py` | Package marker |
| `tests/unit/test_*.py` | Unit tests |
| `tests/integration/__init__.py` | Package marker |
| `tests/integration/test_*.py` | DB tests |
| `tests/system/__init__.py` | Package marker |
| `tests/system/test_*.py` | API tests |

### Directory Structure
```
ac215_NewsJuice/
├── .github/
│   └── workflows/
│       └── ci-cd.yaml                    # Main CI/CD workflow
│
├── services/
│   ├── loader_deployed/
│   │   ├── loader.py
│   │   ├── loader_modular.py
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
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
│   │
│   ├── scraper_deployed/
│   │   └── ...
│   │
│   ├── scraper_testing/
│   │   └── ... (same structure as loader_testing)
│   │
│   ├── chatter_deployed/
│   │   └── ...
│   │
│   └── deployment/
│       ├── Dockerfile
│       ├── docker-shell.sh
│       ├── docker-entrypoint.sh
│       ├── __main__.py
│       └── Pulumi.yaml
```

---

## 🚀 How to Use


### Run Tests Locally

#### Unit Tests (no dependencies)
```bash
cd services/loader
pytest tests/unit/ -v
```

#### Integration Tests (needs PostgreSQL)
```bash
# Start PostgreSQL
docker run -d --name test-postgres \
  -e POSTGRES_PASSWORD=testpassword \
  -e POSTGRES_DB=newsdb_test \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# Initialize database
psql -h localhost -U postgres -d newsdb_test -f tests/setup/init_test_db.sql

# Run tests
DATABASE_URL=postgresql://postgres:testpassword@localhost:5432/newsdb_test \
  pytest tests/integration/ -v
```

#### System Tests (full stack)
```bash
docker compose -f docker-compose.test.yml up -d
docker compose -f docker-compose.test.yml run system_tests
docker compose -f docker-compose.test.yml down -v
```

---

## 📊 CI/CD Flow

### On Push to Branch / Open PR
```
┌─────────────────────────────────────────────────────────────────┐
│  Push to branch / Open PR                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐   ┌─────────────┐   ┌──────┐                      │
│  │  Unit    │ → │ Integration │ → │ Lint │                      │
│  │  Tests   │   │   Tests     │   │      │                      │
│  └──────────┘   └─────────────┘   └──────┘                      │
│       │               │               │                         │
│       └───────────────┴───────────────┘                         │
│                       │                                         │
│                       ▼                                         │
│              ✅ All Pass = Ready to merge                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### On Push to Main
```
┌─────────────────────────────────────────────────────────────────┐
│  Push to main                                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐   ┌─────────────┐   ┌────────┐   ┌─────────────┐  │
│  │  Unit    │ → │ Integration │ → │ System │ → │   Deploy    │  │
│  │  Tests   │   │   Tests     │   │ Tests  │   │ (Pulumi Up) │  │
│  └──────────┘   └─────────────┘   └────────┘   └─────────────┘  │
│                                                      │          │
│                                                      ▼          │
│                                              GKE Updated ✅     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```