# Data Versioning for NewsJuice

## Overview

This module versions the `articles` and `chunks_vector` tables from the NewsJuice PostgreSQL database (`newsdb`) using a hybrid DVC + PostgreSQL export approach.

### How It Works

1. **Export** — Create SQL dump of target tables
2. **Track** — DVC creates a small pointer file (`.dvc`)
3. **Commit** — Git tracks the pointer, not the actual data
4. **Push** — DVC uploads the SQL file to Google Cloud Storage
5. **Link** — Each data version is tied to a Git commit

### Why This Approach?

- **Reproducibility** — Complete, restorable database snapshots
- **Scalability** — Large files stored efficiently in GCS, not Git
- **Traceability** — Data versions linked directly to code commits
- **Simplicity** — Easy to restore any previous state

---

## Setup Instructions

### 1. Navigate to the data versioner service
```bash
cd services/data_versioner
```

### 2. Create and activate virtual environment
```bash
uv venv
source .venv/bin/activate
```

### 3. Create package structure
```bash
mkdir -p data_versioner scripts/data_versioning data/exports
touch data_versioner/__init__.py
```

### 4. Create `pyproject.toml`
```toml
[project]
name = "data-versioner"
version = "0.1.0"
description = "Data versioning with DVC"
requires-python = ">=3.11"
dependencies = []

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/data_versioner"]
```

### 5. Install dependencies
```bash
uv add dvc dvc-gs
uv sync
```

### 6. Initialize DVC
```bash
dvc init --subdir
```

### 7. Create GCS bucket and configure remote
```bash
# Create bucket (if not exists)
gsutil mb gs://newsjuice-data-versions

# Configure DVC remote
dvc remote add -d myremote gs://newsjuice-data-versions/dvc-storage

# Verify
dvc remote list
# Output: myremote    gs://newsjuice-data-versions/dvc-storage
```

### 8. Commit DVC setup
```bash
git add .dvc/config .dvc/.gitignore
git commit -m "Initialize DVC with GCS remote"
git push
```

### Final Directory Structure
```
services/data_versioner/
├── .dvc/                          # DVC configuration
├── data/
│   └── exports/                   # Database exports (DVC-tracked)
├── data.dvc                       # DVC pointer file (Git-tracked)
├── data_versioner/
│   └── __init__.py
├── scripts/
│   └── data_versioning/
│       └── version_data.py        # Main versioning script
└── pyproject.toml
```

---

## Usage

### Creating a New Data Version

The versioning script handles everything automatically: export, DVC tracking, Git commit, and push to both GCS and GitHub.

**Step 1: Start Cloud SQL Proxy** (in a separate terminal)
```bash
cloud-sql-proxy \
  --credentials-file="../../../secrets/sa-key.json" \
  --address 127.0.0.1 \
  --port 5432 \
  <PROJECT_ID>:us-central1:newsdb-instance
```

Replace `<PROJECT_ID>` with your actual GCP project ID.

**Step 2: Set environment variables and run**
```bash
cd services/data_versioner
source .venv/bin/activate

export PGHOST=127.0.0.1
export PGPORT=5432
export PGUSER=postgres
export PGPASSWORD='<your-db-password>'
export DB_PASS='<your-db-password>'
export GOOGLE_APPLICATION_CREDENTIALS="../../../secrets/sa-key.json"

python scripts/data_versioning/version_data.py
```

**Step 3: Verify**
```bash
# Check Git log
git log --oneline -n 3
# Should show: "Data version 20251124_HHMMSS"

# Check DVC pointer file
ls -lh data/exports/
# Should show: db_export_TIMESTAMP.sql.dvc (~100 bytes)

# Check GCS storage
gsutil ls -lh gs://newsjuice-data-versions/dvc-storage/files/md5/
# Should show: Large SQL files
```

---

### Visualizing detailed version history

**Details**
```bash
git log --stat --date=format:"%Y-%m-%d %H:%M" -- data.dvc
```
**Summary**
```bash
git log --format="%C(yellow)%h%C(reset) %C(green)%ad%C(reset) %s" --date=format:"%Y-%m-%d %H:%M" -- data.dvc
```
---

### Restoring a Previous Version

**Step 1: List available versions**
```bash
git log --oneline -- data.dvc
```

**Step 2: Checkout the desired version**
```bash
git checkout <commit-hash> -- data.dvc
```

**Step 3: Pull data from GCS**
```bash
dvc pull
```

The SQL file will appear in `data/exports/`.

**Step 4: Import to database**
```bash
psql -h 127.0.0.1 -p 5432 -U postgres -d newsdb -f data/exports/db_export_<timestamp>.sql
```

---

### Checking DVC Status
```bash
# Check if local data matches remote
dvc status

# List DVC-tracked files
dvc list . --dvc-only
```

---

## Troubleshooting

### "pg_dump: connection refused"

Ensure Cloud SQL Proxy is running in another terminal.

### "dvc push" fails with authentication error

Verify your service account credentials:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="../../../secrets/sa-key.json"
```

### Git complains about large files

Make sure DVC is tracking the data directory, not Git:
```bash
git rm -r --cached data
dvc add data
git add data.dvc data/.gitignore
git commit -m "Track data with DVC, not Git"
```