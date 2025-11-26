# Sets the scheduler and runs

# Grant the roles/run.invoker permission on the article-scraper service:

gcloud run services add-iam-policy-binding article-scraper \
  --member="serviceAccount:cloud-run-invoker@newsjuice-123456.iam.gserviceaccount.com" \
  --role="roles/run.invoker" \
  --region us-central1 \
  --project newsjuice-123456

# Create schedule job (name: article-scraper-job)

gcloud scheduler jobs create http article-scraper-job \
  --location us-central1 \
  --schedule="0 0,12 * * *" \
  --uri="https://article-scraper-919568151211.us-central1.run.app/process" \
  --http-method POST \
  --oidc-service-account-email=cloud-run-invoker@newsjuice-123456.iam.gserviceaccount.com \
  --oidc-token-audience="https://article-scraper-919568151211.us-central1.run.app" \
  --project newsjuice-123456
