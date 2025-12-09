# Loader module

- Loads articles from `articles` table in the DB (only entries with vflag = 0, this flag indicates which article is already chunked and vectorized) 
   - Performs **chunking & embedding**  
   - Adds new article chunks to the **vector DB** (table `chunks_vector`)  
- uses Vertex AI ("text-embedding-004") for final chunk embeddings

Uses Vertex AI for embeddings of the chunks
**Chunking option available**
- `char-split` character splitting
- `recursive-split` recursive splitting (**CHOSEN**)
- `semantic-split` (using embedding model below)


Database Information
- **Account:** `harvardnewsjuice@gmail.com`  
- **Project:** `NewsJuice`  
- **Project ID:** `newsjuice-123456`
- **Instance:** `newsdb-instance`  
- **Region:** `us-central1`
- **Database:** `newsdb` (PostgreSQL 15)  
- **Table:** 
PRODUCTION: IN: `articles`, OUT:`chunks_vector`  
TEST: IN: `articles_test`, OUT:`chunks_vector_test` (set via env variables ARTICLE_TABLE and CHUNKS_VECTOR_TABLE)  

---


## This loader container is currently deployed on GCS (Cloud Run)

Service URL of deployed loader:
https://article-loader-919568151211.us-central1.run.app

	

## Instructions for local deployment  

1. Test that secrets exist:  
```bash
ls -la ../../../secrets/sa-key.json
ls -la ../../../secrets/gemini-service-account.json
```

2. Make sure .env.local has OpenAI key  
```bash
cat .env.local
```

3. Make sure Docker is running  
```bash
docker ps
```

4. Start with logs visible (Note: I use .env.local and docker-compose.local.yml)
```bash
docker-compose -f docker-compose.local.yml --env-file .env.local up --build
```

## LOCAL TESTING

Health:
```bash
curl http://localhost:8080/
```

Run the loader once 
```bash
curl -X POST http://localhost:8080/process
```

Watch logs to see results
```bash
docker compose -f docker-compose.local.yml logs -f loader
```

Stop and remove loader and cloud-sql-proxy containers
```bash
docker compose -f docker-compose.local.yml down
```

Start the containers again
```bash
docker compose -f docker-compose.local.yml up
```


LOGGING:

Local:
For each loader run a timestamped logfile is created and stored in the 
logs folder (./logs is mounted to /app/logs/ in the container)

For Cloud Run:
Logs go to Google Cloud Logging (not files)
File logging in Cloud Run is not recommended
Use gcloud logging read to view logs instead


## Instructions for deployment with Cloud Run

Run:
```bash
chmod +x deploy.sh
./deploy.sh
```

## Prerequisites

Make sure right account set
```bash
gcloud auth list
gcloud config get-value account
gcloud auth login harvardnewsjuice@gmail.com
gcloud config set account harvardnewsjuice@gmail.com
```

## Switch between test and production tables

Go to production  

Make sure right project
```bash
gcloud config set project newsjuice-123456
gcloud config get-value project
```
```bash
gcloud run services update article-loader \
  --region us-central1 \
  --project=newsjuice-123456 \
  --update-env-vars ARTICLES_TABLE_NAME=articles,VECTOR_TABLE_NAME=chunks_vector
```

Back to test tables

```bash
gcloud run services update article-loader \
  --region us-central1 \
  --project=newsjuice-123456 \
  --update-env-vars ARTICLES_TABLE_NAME=articles_test,VECTOR_TABLE_NAME=chunks_vector_test
```

Check the environmental variables
```bash
gcloud run services describe article-loader \
  --region us-central1 \
  --format="value(spec.template.spec.containers[0].env)"
```


## APPENDIX

**Cloud Run's architecture:**
Internet → Cloud Run (HTTPS 443) → Container (port 8080)

Cloud Run automatically:

- Exposes service on HTTPS (port 443) publicly
- Routes traffic to container's internal port (8080)
- Handles load balancing, scaling, etc.
- You never directly expose port 8080 to the internet. Cloud Run manages that.



### STEP BY STEP - DEPLOYMENT

Make sure right account: (switch if needed)
```bash
gcloud auth list
gcloud config set account harvardnewsjuice@gmail.com
```

mMke sure right project:
```bash
gcloud config get-value project
gcloud config set project newsjuice-123456
```

RUN DEPLOY script
```bash
chmod +x deploy.sh
./deploy.sh
```

WATCH DEPLOYMENT
```bash
gcloud builds list --limit 3
```
SEE DEPLOYED SERIVCES
```bash
gcloud run services list --region us-central1
```

## Set up Scheduler

Create SA (cloud-run-invoker):
```bash
gcloud iam service-accounts create cloud-run-invoker \
  --display-name "Cloud Run Invoker" \
  --project newsjuice-123456
```

Grant permissions:
```bash
gcloud run services add-iam-policy-binding article-loader \
  --member="serviceAccount:cloud-run-invoker@newsjuice-123456.iam.gserviceaccount.com" \
  --role="roles/run.invoker" \
  --region=us-central1 \
  --project=newsjuice-123456
```

Enable API [cloudscheduler.googleapis.com] on project [newsjuice-123456]

Grant Vertex AI User role

```bash
gcloud projects add-iam-policy-binding newsjuice-123456 \
  --member="serviceAccount:919568151211-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.serviceAgent"
gcloud projects add-iam-policy-binding newsjuice-123456 \
  --member="serviceAccount:919568151211-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

Create schedule job (name: article-loader-job)

```bash
gcloud scheduler jobs create http article-loader-job \
  --location us-central1 \
  --schedule="*/10 * * * *" \
  --uri="https://article-loader-919568151211.us-central1.run.app/process" \
  --http-method POST \
  --oidc-service-account-email=cloud-run-invoker@newsjuice-123456.iam.gserviceaccount.com \
  --oidc-token-audience="https://article-loader-919568151211.us-central1.run.app" \
  --project newsjuice-123456
```

Test scheduler manually:

```bash
gcloud scheduler jobs run article-loader-job \
  --location us-central1 \
  --project newsjuice-123456
```

After running check:  

View Cloud Run logs  
```bash
gcloud run services logs read article-loader \
  --region us-central1 \
  --limit 20
```

Check scheduler logs
```bash
gcloud logging read "resource.type=cloud_scheduler_job" --limit 10
```

View all cloud builds and revisions
```bash
gcloud builds list --limit 20
```

### CHANGE SCHEDULE:

```bash
gcloud scheduler jobs update http article-loader-job \
--location us-central1 \
--schedule="0 0 * * *"
```

```bash
force a run  
gcloud scheduler jobs run article-loader-job \
--location us-central1
```

See the print to standard i/o:
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=article-loader" \
--limit=100 \
--format="value(timestamp,textPayload)" \
--freshness=1h
```

Deploy with secret
```bash
gcloud run deploy article-loader \
  --source . \
  --region us-central1 \
  --env-vars-file env.yaml \
  --set-secrets DATABASE_URL=database-url:latest \
  --add-cloudsql-instances newsjuice-123456:us-central1:newsdb-instance
```