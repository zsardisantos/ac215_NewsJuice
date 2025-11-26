# Scraper module
Scrapes articles from various Harvard-related news sources (currently a hard-coded list in "scrapers.py"), performs a tagging operation (stored later in a column in the articles table) and loads the articles not previously loaded into the articles table.


## Instructions for local deployment  

1. Test that secrets exist:  
```bash
ls -la ../../../secrets/sa-key.json
ls -la ../../../secrets/gemini-service-account.json 
```

2. .env.local not needed (only contained the OpenAI key which is not needed)


3. Make sure Docker is running  
```bash
docker ps
```

Make sure port is free, otherwise close other containers using it
```bash
lsof -i :5432
````


4. Start with logs visible (Note: we use docker-compose.local.yml; .env.local not needed)
```bash
docker compose -f docker-compose.local.yml --env-file .env.local up --build
```

## LOCAL TESTING

Health:
```bash
curl http://localhost:8080/
```

Run the scraper once 
```bash
curl -X POST http://localhost:8080/process
```

Watch logs to see results
```bash
docker compose -f docker-compose.local.yml logs -f scrapers
```

Stop and remove scrapers and cloud-sql-proxy containers
```bash
docker compose -f docker-compose.local.yml down
```

Start the containers again
```bash
docker compose -f docker-compose.local.yml up
```


## Deployment

As no service account is specified, Cloud Run will use the default Compute Engine service account for this:
```bash
cloud-run-invoker@newsjuice-123456.iam.gserviceaccount.com
```

Make sure you have the deploy.sh and the env.yaml files.

Run:
```bash
chmod +x deploy.sh
./deploy.sh
```


RESULT: 
```bash
https://article-scraper-919568151211.us-central1.run.app
```

### Test deployment:

/
can do in browser

```bash
/process endpoint (as POST need curl)
curl -X POST \
  https://article-scraper-919568151211.us-central1.run.app/process
```

should show: 
```bash
{"status":"started"}%    
```

How to see what it is doing while processing: in GCS console look at LOG files of service deployed


## Prerequisites

Make sure right account set (harvardnewsjuice@gmail.com)
```bash
gcloud config get-value account
```
If not, set:
```bash
gcloud auth login harvardnewsjuice@gmail.com
gcloud config set account harvardnewsjuice@gmail.com
```

## Set up Scheduler

---

### ONE TIME SET UP (DONE)

Create SA (cloud-run-invoker) - only once (already set up)
```bash
gcloud iam service-accounts create cloud-run-invoker \
  --display-name "Cloud Run Invoker" \
  --project newsjuice-123456
```
Enable API [cloudscheduler.googleapis.com] on project [newsjuice-123456] (only once, done)

### ONE TIME SET UP - END
---

Run the following to set and deploy the scheduler on Cloud Run
```bash
chmod +x set-scheduler.sh
./set-scheduler.sh
```

Test scheduler manually:

```bash
gcloud scheduler jobs run article-scraper-job \
  --location us-central1 \
  --project newsjuice-123456
```

Change schedule, .e.g.:

```bash
  gcloud scheduler jobs update http article-scraper-job \
  --location us-central1 \
  --schedule="0 0 * * *"
```

Force a run:

```bash
  gcloud scheduler jobs run article-scraper-job \
  --location us-central1
```


### EXTRAS

How see what schduler jobs are on cloud-run-invoker@newsjuice-123456.iam.gserviceaccount.com:

```bash
gcloud scheduler jobs list \
  --location=us-central1 \
  --project=newsjuice-123456
  ```
