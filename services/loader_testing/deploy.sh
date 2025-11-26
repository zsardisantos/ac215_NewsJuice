#!/bin/bash

SERVICE_NAME="article-loader"
REGION="us-central1"
PROJECT_ID="newsjuice-123456"
SQL_INSTANCE="newsjuice-123456:us-central1:newsdb-instance"

echo "Deploying ${SERVICE_NAME} to Cloud Run..."

gcloud run deploy ${SERVICE_NAME} \
  --source . \
  --region ${REGION} \
  --platform managed \

  --env-vars-file env.yaml \
  --add-cloudsql-instances ${SQL_INSTANCE} \
  --timeout 60m \
  --memory 4Gi \
  --cpu 2 \
  --project ${PROJECT_ID}
 # --project newsjuice-123456 \
 # --account harvardnewsjuice@gmail.com
 # --no-allow-unauthenticated \

echo ""
echo "Deployment complete!"
echo ""
ECHO "Get service URL:"
echo "gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format='value(status.url)'"
