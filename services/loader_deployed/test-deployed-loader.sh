#!/bin/bash

# TESTING THE DEPLOYED LOADER
# run with the following from CLI
# chmod +x test-deployed-loader.sh
# ./test-deployed-loader.sh

# Check environmental variables: 
# ARTICLE_TABLE_NAME and VECTOR_TABLE_NAME
gcloud run services describe article-loader \
  --region us-central1 \
  --format="yaml(spec.template.spec.containers[0].env)" | grep -A1 "ARTICLES_TABLE_NAME\|VECTOR_TABLE_NAME"

# Get service URL
SERVICE_URL=$(gcloud run services describe article-loader \
  --region us-central1 \
  --format='value(status.url)')

echo "Service URL: ${SERVICE_URL}"
echo ""

# Get auth token
TOKEN=$(gcloud auth print-identity-token)

# Test health
echo "1. Testing health check:"
curl -H "Authorization: Bearer ${TOKEN}" ${SERVICE_URL}/
echo -e "\n"

# Test processing
echo "2. Triggering article processing:"
curl -X POST -H "Authorization: Bearer ${TOKEN}" ${SERVICE_URL}/process
echo -e "\n"

echo "3. Generating logs.text file"
gcloud logging read "resource.labels.service_name=article-loader" \
  --limit=1000 \
  --format="value(timestamp,textPayload)" > logs.txt

