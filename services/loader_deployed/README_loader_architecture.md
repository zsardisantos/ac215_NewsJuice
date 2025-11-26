# Loader Service - Technical Architecture

## Short description

The Loader service is a Cloud Run application that ingests news articles from the SCRAPER service, cuts them into semantic chunks with vector embeddings, and stores them in PostgreSQL for the NewsJuice platform.

---

## System Architecture

```
Harvard related web news sources → Loader service (Cloud Run) → PostgreSQL (Cloud SQL + pgvector)
              ↓
         Cloud Scheduler (every 24 hours)
```

### Key Components

1. **Cloud Run service**: Stateless containerized application
2. **Cloud SQL (PostgreSQL + pgvector)**: Article storage with vector search
3. **Cloud Scheduler**: Automated periodic ingestion (every 24 hours)
4. **Google Cloud Storage**: DVC data versioning backend

---

## Technology Stack

**Runtime**: Python 3.12  
**Framework**: FastAPI  
**Database**: PostgreSQL with pgvector extension  
**Package Manager**: UV  
**Container**: Docker  

---

## Data Processing Pipeline

```
1. Detect New Articles
   ↓ Query GCS SQL database **articles** table for unprocessed articles
   
2. Content Extraction
   ↓ Fetch unprocessed articles
   
3. Chunking
   ↓ Split text using strategy (Recursive)
   
5. Embedding Generation
   ↓ Generate vectors using VertexAI (model: XYZ)
   
6. Storage
   ↓ Store chunks + embeddings in PostgreSQL (pgvector) in **chunks_vector" table
```

---

### RecursiveChunking
- Hierarchical splitting (paragraphs → sentences)
- Preserves semantic boundaries
- Better context retention
**Selection via**: `get_chunking_strategy(strategy: str)`

---

## Database Schema

### 🧠 Table: `chunks_vector`
Stores semantic chunks and vector embeddings.

```sql
id BIGSERIAL PRIMARY KEY,
author TEXT,
title TEXT,
summary TEXT,
content TEXT,
source_link TEXT,
source_type TEXT,
fetched_at TIMESTAMPTZ,
published_at TIMESTAMPTZ,
chunk TEXT,
chunk_index INT,
embedding VECTOR(768),
article_id TEXT
```

---

## Cloud Run Deployment

### Configuration

```yaml
Service: loader-service
Region: us-central1
Timeout: 3600s (60 min max)
Memory: 4Gi
CPU: 2 cores (always allocated)
Concurrency: 1
Max Instances: 10
```

### Environment Variables

```bash
DATABASE_URL=postgresql://user:pass@/db?host=/cloudsql/PROJECT:REGION:INSTANCE
GOOGLE_CLOUD_PROJECT=newsjuice-123456
CHUNKING_STRATEGY=recursive
LOG_LEVEL=INFO
```

### Deployment Command

```bash
gcloud run deploy loader-service \
  --source . \
  --region us-central1 \
  --memory 4Gi \
  --cpu 2 \
  --timeout 3600 \
  --cpu-always-allocated \
  --max-instances 10 \
  --add-cloudsql-instances PROJECT:REGION:INSTANCE \
  --set-env-vars DATABASE_URL=${DATABASE_URL}
```

---

## Scheduling

**Cloud Scheduler Job**:
```bash
gcloud scheduler jobs update http article-loader-job \
  --location us-central1 \
  --schedule="0 */2 * * *"  # Every 2 hours
  --uri="https://loader-service-xxx.run.app/api/v1/ingest" \
  --http-method=POST \
  --oidc-service-account-email=scheduler@PROJECT.iam.gserviceaccount.com
```

**Schedule**: Every 2 hours at :00 (00:00, 02:00, 04:00, etc.)

---

## API Endpoints

```
@app.get("/"). Healthcheck
returns {"status": "ok"}

@app.post("/process"). Triggers article retrieval, chunking, embedding and storing of chunks
returns {"status": "started"}

@app.post("/process-sync")
return {"status": "error", "message": str(e)}

```

---

## Monitoring

### Cloud Logging Query
```bash
gcloud logging read "resource.type=cloud_run_revision 
  AND resource.labels.service_name=loader-service" \
  --limit=100 \
  --format=json
```

---

## Testing

Testing is set up in separate Service folder "services/loader_testing"

### Local Testing
```bash
cd services/loader_faster
uv sync
pytest tests/unit/ -v --cov=api

# System tests with Docker
docker-compose -f docker-compose.test.yml up --build
```

### CI/CD
GitHub Actions workflow (`.github/workflows/ci-unit_only_loader.yaml`):
- Triggers on changes to `services/loader_moduler/**`
- Runs unit tests with coverage
- Python 3.12 environment
- UV package management

---

## Security

- **No API Keys in Code**: Environment variables only
- **Cloud SQL Private IP**: Accessed via Unix socket
- **Service Account**: Minimal permissions (Cloud SQL Client, Storage Admin)
- **Non-root Container**: Security best practice
- **OIDC Authentication**: Scheduler → Cloud Run

---

## Data Versioning

**DVC (Data Version Control)**:
- Exports key tables (articles, chunks_vector) as snapshot
- Tracks PostgreSQL database exports
- Backend: Google Cloud Storage
- Enables reproducibility of training data
- Version control for article datasets

```bash
# Export database snapshot
dvc add data/exports/db_export_YYYYMMDD.sql
dvc push
```


