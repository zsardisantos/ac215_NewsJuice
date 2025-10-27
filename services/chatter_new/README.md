# Chatter FastAPI

Chatter is a self-contained HTTP API. It will:
- receive { "text": "..." }
- summarize it with OpenAI
- TTS → MP3
- upload to GCS auido bucket
- return { "signedUrl": "https://..." } (what the frontend expects)

Frontend:
index.html (deployed in *www.newsjuiceapp.com*)

Audiobucket in GSC:
- bucket name = *ac215-audio-bucket*
- cloud console ID = https://console.cloud.google.com/storage/browser/ac215-audio-bucket
- gsutil uri = gs://ac215-audio-bucket


ENDPOINT FOR THIS APP DEPLOYED ON CLOUD RUN:
https://chatter-919568151211.us-central1.run.app


---

# SOME SET UP DETAILS (WIP)

## Secrets
-API keys for HuggingFace and OpenAI    
in *.env.local* (dockerignored)  
- Secret files (Google Cloud Service Account ,Gemini Service Account)  
In parent directory ../secrets/sa-key.json and ../secrets/gemini-service.account.json  


## Audiobucket details: Setting CORS

*VIA CONSOLE - RUN CLOUD SHELL*
echo '[
  {
    "origin": ["https://newsjuiceapp.com"],
    "method": ["GET"],
    "responseHeader": ["Content-Type", "Content-Disposition", "Range"],
    "maxAgeSeconds": 3600
  }
]' > cors.json
gsutil cors set cors.json gs://ac215-audio-bucket

*Check in CLI*
gsutil cors get gs://ac215-audio-bucket

1) One-time GCP setup
PROJECT_ID="newsjuice-123456"
REGION="us-central1"         
REPO="apps"                  
SERVICE="chatter"            
BUCKET="ac215-audio-bucket"  

2) Make sure right project is set
gcloud config set project "$PROJECT_ID"
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com

3) Create Artifact Registry (one time):
gcloud artifacts repositories create "$REPO" \
  --repository-format=docker \
  --location="$REGION" \
  --description="App containers"


Create secret (first time only)

```yaml
echo -n "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" | \
  gcloud secrets create openai-api-key --data-file=-
```

CHECK:
gcloud artifacts repositories list --project $PROJECT_ID


CHECK
gcloud secrets list
gcloud secrets versions list OPENAI_API_KEY
gcloud secrets versions access latest --secret=OPENAI_API_KEY

*Service account settings*
Service account used: *919568151211-compute@developer.gserviceaccount.com*

BUCKET="ac215-audio-bucket"
SA_EMAIL="919568151211-compute@developer.gserviceaccount.com"

*Check SA*
SERVICE="chatter"
REGION="us-central1"
SA_EMAIL="$(gcloud run services describe "$SERVICE" --region "$REGION" \
  --format='value(template.spec.serviceAccountName)')"
echo "$SA_EMAIL"


*Check on CLI which SA chatter is using*
gcloud run services describe chatter --region us-central1 \
  --format='value(spec.template.spec.serviceAccountName)'
ANSWER SHOULD BE: 919568151211-compute@developer.gserviceaccount.com

*Grant the secret accessor role to SA*
gcloud projects add-iam-policy-binding "newsjuice-123456" \
  --member="serviceAccount:919568151211-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

*Allow SA to upload objects to buckets*
(Project-wide — simple)
gcloud projects add-iam-policy-binding newsjuice-123456 \
  --member="serviceAccount:919568151211-compute@developer.gserviceaccount.com" \
  --role="roles/storage.objectCreator"
(limited to bucket)
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectAdmin"

Get the Cloud Run URL
gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)'

### Revision commands
List all revisions with traffic allocation
gcloud run revisions list --service=chatter --region=us-central1

See which revision is currently serving traffic
gcloud run services describe chatter --region=us-central1

Show traffic distribution
gcloud run services describe chatter \
  --region=us-central1 \
  --format="table(status.traffic.revisionName, status.traffic.percent)"

Get details of a specific revision
gcloud run revisions describe chatter-00029-lwx --region=us-central1

Compare images across revisions
gcloud run revisions list --service=chatter --region=us-central1 \
  --format="table(metadata.name, spec.containers[0].image, status.conditions[0].lastTransitionTime)"

See revisions
gcloud run revisions list --service=chatter --region=us-central1

Rollback (example with previous revision name)
gcloud run services update-traffic chatter \
  --to-revisions=chatter-00028-xxx=100 \
  --region=us-central1

Go back to the latest revision
gcloud run services update-traffic chatter \
  --to-latest \
  --region=us-central1

---

###Some docker commands

docker build -t chatter-api .

docker run -p 8080:8080 --env-file .env chatter-api

Run container with shell to inspect
docker run -it --entrypoint /bin/bash chatter-api

Inside container, check files
ls -la /app/
