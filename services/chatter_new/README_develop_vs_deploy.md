# Chatter service (FastAPI)

* Receives user brief from Frontend
* Returns mp3 file with cutomized audio-podcast to the Frontend


Set up as zero-touch environment which allows easy switching between LOCAL DEVELOPMENT and CLOUD RUN DEPLOYMENT


## Local build/run VERSUS production (Could Run) build/deploy

The following changes when switching between LOCAL DEVELOPMENT and DEPLOYMENT/PRODUCTION on CLOUD RUN are considered in the code and files set up.
Just follow the below WORKFLOW to switch between both. Make sure in LOCAL DEVELOPMENT not to do changes that compromise the zero-touch set up.

### Database: 

- Deployment/production: Cloud SQL Unix socket
- *DATABASE_URL=postgresql://postgres:Newsjuice25%2B@/newsdb?host=/cloudsql/newsjuice-123456:us-central1:newsdb-instance*
- Local Development: Cloud SQL Proxy TCP connection. Need to set
- *DATABASE_URL=postgresql://postgres:Newsjuice25%2B@cloud-sql-proxy:5432/newsdb*
- ✅ Where to Set These
- Deployment/production: In your env.yaml or Cloud Run environment variables
- Local Development: In your .env.local file


### Secrets 

- Deployment/productionoyment: Service Account Keys: Workload Identity
- Local Development: Mounted JSON service account files
You can download them, e.g.
```yaml
mkdir -p secrets
gcloud iam service-accounts keys create secrets/sa-key.json --iam-account=YOUR-SA@newsjuice-123456.iam.gserviceaccount.com
gcloud iam service-accounts keys create secrets/gemini-service-account.json --iam-account=GEMINI-SA@newsjuice-123456.iam.gserviceaccount.com
```

### Environment Variables: 

- Deployment/production: Cloud Run: env.yaml + Secret Manager
- Local development; .env.local 

###  Docker compose

- Deployment/production:  Cloud Run: managed service
- Local development: use docker-compose.local.yml with Clound Proxy Container

### Fontend:

- Deployment/Production
```yaml
const BACKEND_URL = "https://chatter-919568151211.us-central1.run.app/api/chatter";
```
- Local Development
```yaml
const BACKEND_URL = "http://localhost:8080/api/chatter";
```

### CORS issues for Frontend 

We use Auto-Detection for BACKEND URL in the index.html Frontend
```yaml
const BACKEND_URL = window.location.hostname.includes('newsjuiceapp.com')
  ? "https://chatter-919568151211.us-central1.run.app/api/chatter"
  : "http://localhost:8080/api/chatter";
```

## WORKFLOW

### Build and run LOCALLY (note: we use ".env.local" instead of ".env" for clarity)
```yaml
docker-compose -f docker-compose.local.yml --env-file .env.local up --build
```

### Build and deploy on CLOUD RUN in one command (due to enhanced cloudbuild.yaml file)

```yaml
gcloud builds submit \
  --config cloudbuild.yaml \
  --substitutions _HUGGING_FACE_HUB_TOKEN=hf_XXXXXXXXXXXXXX (substitute)
```

### Monitor when building + deploying on Cloud Run
See status: 
```yaml
gcloud builds list --limit=1 --format='table(id,status,createTime,duration())'
```
See revisions:
```yaml
gcloud run revisions list --service chatter --region us-central1 --limit=5
```
See logs:
```yaml
gcloud builds log $(gcloud builds list --limit=1 --format='value(id)')
```
See Cloud Run logs
```yaml
gcloud run services logs read chatter --region us-central1
```


### Testing 

- DEVELOPMENT
```yaml
curl http://localhost:8080/healthz
curl -X POST http://localhost:8080/api/chatter \
  -H "Content-Type: application/json" \
  -d '{"text": "What is happening in AI today?"}'

```
Should return: {"ok":true} and an URL for mp3 file

For Frontend testing in development need run (from within the directory that contains index.html) 
```yaml
python3 -m http.server 3000 (or change CORS including *)
```
Then go to in browser: http://localhost:3000

- PRODUCTION
```yaml
curl https://chatter-919568151211.us-central1.run.app/api/healthz
curl -X POST https://chatter-919568151211.us-central1.run.app/api/chatter \
  -H "Content-Type: application/json" \
  -d '{"text": "What is happening in AI today?"}'
```
Should return: {"ok":true} and an URL for mp3 file

For frontend testing:
Visit: https://chatter-919568151211.us-central1.run.app/api/healthz
Should return: {"ok":true}




## Files structure for chatter service backend and for frontend


chatter-app/
│
├── 📱 Backend (FastAPI)
│   ├── main.py                      # FastAPI app entry point & routes
│   ├── chatter_handler.py           # Main business logic for podcast generation
│   ├── helpers.py                   # Helper functions (DB, Gemini API, retriever)
│   ├── retriever.py                 # News article search & retrieval
│   ├── pyproject.toml               # Python dependencies
│   └── Dockerfile                   # Container image definition
│
├── 🌐 Frontend
│   ├── index.html                   # Single-page web interface
│   └── logo.jpeg                    # App logo
│
├── ☁️ Production Deployment (Cloud Run)
│   ├── env.yaml                     # Environment variables for Cloud Run
│   └── cloudbuild.yaml              # Cloud Build configuration (build & deploy)
│
├── 🐳 Local Development (Docker)
│   ├── docker-compose.local.yml     # Docker Compose for local development
│   └── .env.local                   # Local secrets (API keys) - NOT COMMITTED
│
├── 🔐 Secrets (Local Only - NOT COMMITTED)
│   └── secrets/
│       ├── sa-key.json              # Service account for GCS & Cloud SQL
│       └── gemini-service-account.json  # Service account for Gemini API
│
├── 📚 Documentation
│   └── README.md                    # Project documentation
│
└── 🔒 Security
    └── .gitignore                   # Prevents committing secrets



## Appendix

SOME CHECKS

docker-compose -f docker-compose.local.yml config | grep HUGGING_FACE_HUB_TOKEN

Make sure that service account has permissions:
+ Cloud SQL Client
+ Secret Manager Secret Accessor
+ Storage Object Admin (for GCS bucket)




