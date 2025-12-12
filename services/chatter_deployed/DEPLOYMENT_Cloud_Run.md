# Deployment Guide - Local Development vs Cloud Run

This guide is a **quick reference for developers** who need to switch between local development and production Cloud Run deployment.

**For complete setup instructions**, see [README.md](README.md).

---

## Overview

The NewsJuice backend (chatter_deployed) supports **zero-touch switching** between:
- **Local Development**: Docker Compose with Cloud SQL Proxy
- **Production**: Google Cloud Run with direct Cloud SQL connection

---

## Key Differences: Local vs Production

| Component | Local Development | Production (Cloud Run) |
|-----------|-------------------|------------------------|
| **Database Connection** | Cloud SQL Proxy (TCP)<br>`postgresql://postgres:Newsjuice25%2B@cloud-sql-proxy:5432/newsdb` | Cloud SQL Unix Socket<br>`postgresql://postgres:Newsjuice25%2B@/newsdb?host=/cloudsql/newsjuice-123456:us-central1:newsdb-instance` |
| **Environment Config** | `.env.local` file | `env.yaml` + Cloud Run environment variables |
| **Service Accounts** | Mounted JSON keys<br>`../../../secrets/sa-key.json`<br>`../../../secrets/gemini-service-account.json` | Workload Identity (automatic)<br>Attached to Cloud Run service |
| **Docker Orchestration** | `docker-compose.local.yml` | Cloud Run (managed service) |
| **Frontend URL** | `http://localhost:3000` | `https://www.newsjuiceapp.com` |
| **Backend URL** | `http://localhost:8080` | `https://chatter-919568151211.us-central1.run.app` |
| **WebSocket URL** | `ws://localhost:8080/ws/chat` | `wss://chatter-919568151211.us-central1.run.app/ws/chat` |
| **CORS Origins** | `http://localhost:3000,http://localhost:8080` | `https://www.newsjuiceapp.com` |

---

## Local Development Workflow

### 1. Environment Setup

Ensure you have `.env.local` in `services/chatter_deployed/`:

```bash
# Database (Cloud SQL Proxy)
DATABASE_URL=postgresql://postgres:Newsjuice25%2B@cloud-sql-proxy:5432/newsdb
DB_URL=postgresql://postgres:Newsjuice25%2B@cloud-sql-proxy:5432/newsdb

# Google Cloud
GOOGLE_CLOUD_PROJECT=newsjuice-123456
GOOGLE_CLOUD_REGION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/app/sa-key.json
GEMINI_SERVICE_ACCOUNT_PATH=/secrets/gemini-service-account.json

# Google AI API
GOOGLE_API_KEY=your_api_key_here

# CORS (local frontend)
CORS_ALLOW_ORIGINS=http://localhost:3000,http://localhost:8080

# Server
PORT=8080
```

### 2. Start Backend

```bash
cd services/chatter_deployed
docker-compose -f docker-compose.local.yml --env-file .env.local up --build
```

### 3. Start Frontend

```bash
cd services/k-frontend/podcast-app
npm run dev
```

**Access at**: `http://localhost:3000`

### 4. Testing Local Development

```bash
# Health check
curl http://localhost:8080/healthz
# Expected: {"ok":true}

# WebSocket connection
# Use browser at http://localhost:3000 to test voice recording
```

---

## Cloud Run Deployment Workflow

### 1. Prerequisites

Ensure the following are configured:

- **GCP Project**: `newsjuice-123456`
- **Cloud Run Service**: `chatter`
- **Region**: `us-central1`
- **Cloud SQL Instance**: `newsjuice-123456:us-central1:newsdb-instance`
- **Service Account**: Attached to Cloud Run with roles:
  - `roles/cloudsql.client`
  - `roles/aiplatform.user`
  - `roles/secretmanager.secretAccessor` (if using Secret Manager)

### 2. Environment Configuration

Ensure `env.yaml` is configured for production:

```yaml
# env.yaml (example - adjust as needed)
DATABASE_URL: "postgresql://postgres:Newsjuice25%2B@/newsdb?host=/cloudsql/newsjuice-123456:us-central1:newsdb-instance"
DB_URL: "postgresql://postgres:Newsjuice25%2B@/newsdb?host=/cloudsql/newsjuice-123456:us-central1:newsdb-instance"
GOOGLE_CLOUD_PROJECT: "newsjuice-123456"
GOOGLE_CLOUD_REGION: "us-central1"
CORS_ALLOW_ORIGINS: "https://www.newsjuiceapp.com,https://chatter-919568151211.us-central1.run.app"
PORT: "8080"

# API keys - use Secret Manager in production
GOOGLE_API_KEY: "your_production_api_key"
```

**Security Note**: For production, use [Secret Manager](https://cloud.google.com/secret-manager) instead of storing API keys in `env.yaml`.

### 3. Deploy to Cloud Run

```bash
cd services/chatter_deployed

# Single command deployment (builds + deploys)
gcloud builds submit \
  --config cloudbuild.yaml
```

**What this does**:
1. Builds Docker image
2. Pushes to Artifact Registry (`us-central1-docker.pkg.dev/newsjuice-123456/cloud-run-source-deploy/chatter`)
3. Deploys to Cloud Run service `chatter` in `us-central1`
4. Uses `env.yaml` for environment variables
5. Connects to Cloud SQL via Unix socket

### 4. Monitor Deployment

**Check build status**:
```bash
gcloud builds list --limit=1 --format='table(id,status,createTime,duration())'
```

**Check Cloud Run service**:
```bash
gcloud run services describe chatter --region us-central1
```

**View Cloud Run logs**:
```bash
gcloud run services logs read chatter --region us-central1 --limit=50
```

**View build logs**:
```bash
gcloud builds log $(gcloud builds list --limit=1 --format='value(id)')
```

**List recent revisions**:
```bash
gcloud run revisions list --service chatter --region us-central1 --limit=5
```

### 5. Testing Production

**Health check**:
```bash
curl https://chatter-919568151211.us-central1.run.app/healthz
# Expected: {"ok":true}
```

**WebSocket connection**:
- Access frontend: `https://www.newsjuiceapp.com`
- Test voice recording and podcast generation
- Check browser console for WebSocket connection (`wss://...`)

---

## Frontend Configuration

The frontend automatically detects the environment using hostname-based logic:

### Current Implementation (in React frontend)

```javascript
// Podcast.jsx or similar
const getBackendUrl = () => {
  const hostname = window.location.hostname;

  // Production
  if (hostname.includes('newsjuiceapp.com')) {
    return 'https://chatter-919568151211.us-central1.run.app';
  }

  // Local development
  return 'http://localhost:8080';
};

// WebSocket connection
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${protocol}//${backendHost}/ws/chat?token=${token}`;
```

**This means**:
- No code changes needed when switching environments
- Frontend detects local vs production automatically
- CORS must be configured correctly on backend

---

## File Structure

```bash
services/chatter_deployed/
│
├── main.py                          # FastAPI app entry point
├── speech_to_text_client.py         # Audio transcription
├── query_enhancement.py             # Query expansion with Gemini
├── retriever.py                     # Vector database retrieval
├── text_to_speech_client.py         # Text-to-speech with Google Cloud TTS API
├── helpers.py                       # Gemini API calls
├── user_db.py                       # User management (Cloud SQL)
├── firebase_auth.py                 # Firebase token verification
│
├── Dockerfile                       # Container image
├── pyproject.toml                   # Python dependencies
│
├── 🐳 Local Development
│   ├── docker-compose.local.yml     # Docker Compose with Cloud SQL Proxy
│   └── .env.local                   # Local environment variables (gitignored)
│
├── ☁️ Cloud Run Deployment
│   ├── cloudbuild.yaml              # Cloud Build configuration
│   └── env.yaml                     # Production environment variables
│
└── 📚 Documentation
    ├── README.md                    # Complete setup guide
    └── DEPLOYMENT.md                # This file (deployment reference)
```

---

## Troubleshooting

### Local Development Issues

**Problem**: Cloud SQL Proxy not connecting
```bash
# Check proxy logs
docker-compose -f docker-compose.local.yml logs cloud-sql-proxy

# Verify service account has cloudsql.client role
gcloud projects get-iam-policy newsjuice-123456 \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:*newsjuice*"
```

**Problem**: Service account key not found
```bash
# Verify keys exist
ls -la ../../../secrets/

# Should show:
# sa-key.json
# gemini-service-account.json
```

### Cloud Run Deployment Issues

**Problem**: Deployment fails during build
```bash
# Check build logs
gcloud builds log $(gcloud builds list --limit=1 --format='value(id)')

# Common causes:
# - Dockerfile syntax errors
# - Missing dependencies in pyproject.toml
# - Build timeout (increase in cloudbuild.yaml)
```

**Problem**: Service won't start or crashes
```bash
# Check Cloud Run logs
gcloud run services logs read chatter --region us-central1 --limit=100

# Common causes:
# - env.yaml missing required variables
# - Database connection string incorrect
# - Service account lacks permissions
```

**Problem**: Database connection fails in production
```bash
# Verify Cloud SQL connection is configured
gcloud run services describe chatter --region us-central1 | grep cloudsql

# Should show: --add-cloudsql-instances=newsjuice-123456:us-central1:newsdb-instance

# Check service account has Cloud SQL Client role
gcloud run services describe chatter --region us-central1 | grep serviceAccountName
```

---

## Security Best Practices

### Local Development
- ✅ Use `.env.local` (gitignored)
- ✅ Mount service account keys as read-only volumes
- ✅ Never commit secrets to git

### Production (Cloud Run)
- ✅ Use Workload Identity (no service account keys needed)
- ✅ Store API keys in Secret Manager
- ✅ Restrict CORS to production domain only
- ✅ Use environment variables from `env.yaml` or Secret Manager
- ✅ Enable Cloud Run authentication if not public

### Secret Manager Integration (Recommended)

Instead of storing `GOOGLE_API_KEY` in `env.yaml`, use Secret Manager:

```bash
# Create secret
echo -n "your_api_key_here" | gcloud secrets create google-ai-api-key --data-file=-

# Grant Cloud Run service account access
gcloud secrets add-iam-policy-binding google-ai-api-key \
  --member="serviceAccount:YOUR-SA@newsjuice-123456.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Update cloudbuild.yaml to mount secret
# See: https://cloud.google.com/run/docs/configuring/secrets
```

---

## Service Account Permissions Checklist

Ensure your service account has these roles:

- ✅ `roles/cloudsql.client` - Connect to Cloud SQL
- ✅ `roles/aiplatform.user` - Use Vertex AI (Gemini, embeddings)
- ✅ `roles/secretmanager.secretAccessor` - Access Secret Manager (if used)
- ✅ `roles/storage.objectAdmin` - GCS bucket access (for audio storage)

**Verify permissions**:
```bash
gcloud projects get-iam-policy newsjuice-123456 \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:YOUR-SA@newsjuice-123456.iam.gserviceaccount.com"
```

---

## Quick Command Reference

### Local Development
```bash
# Start backend
cd services/chatter_deployed
docker-compose -f docker-compose.local.yml --env-file .env.local up --build

# Stop backend
docker-compose -f docker-compose.local.yml down

# View logs
docker-compose -f docker-compose.local.yml logs -f

# Rebuild without cache
docker-compose -f docker-compose.local.yml build --no-cache
```

### Cloud Run Deployment
```bash
# Deploy
cd services/chatter_deployed
gcloud builds submit --config cloudbuild.yaml

# View logs
gcloud run services logs read chatter --region us-central1 --limit=50

# Check status
gcloud run services describe chatter --region us-central1

# List revisions
gcloud run revisions list --service chatter --region us-central1

# Rollback to previous revision
gcloud run services update-traffic chatter --to-revisions=REVISION_NAME=100 --region us-central1
```

---

## Additional Resources

- **README.md**: Complete setup instructions for local development
- **Cloud Run Documentation**: https://cloud.google.com/run/docs
- **Cloud SQL Proxy**: https://cloud.google.com/sql/docs/postgres/sql-proxy
- **Secret Manager**: https://cloud.google.com/secret-manager/docs
- **Vertex AI**: https://cloud.google.com/vertex-ai/docs

---

## Support

For deployment issues:
1. Check troubleshooting section above
2. Review Cloud Run logs: `gcloud run services logs read chatter --region us-central1`
3. Verify all environment variables in `env.yaml`
4. Confirm service account has required permissions
