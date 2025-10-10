# Database Setup Guide

## Prerequisites
You need a Google Cloud service account key file to connect to your Cloud SQL instance.

## Step 1: Get Service Account Key
1. Go to Google Cloud Console
2. Navigate to IAM & Admin > Service Accounts
3. Find your service account or create one
4. Generate a JSON key file
5. Download the key file and save it as `./secrets/sa-key.json`

## Step 2: Start Cloud SQL Proxy
```bash
./cloud-sql-proxy \
  --credentials-file=./secrets/sa-key.json \
  --port 5432 \
  newsjuice-123456:us-central1:newsdb-instance
```

## Step 3: Explore Database
```bash
python3 explore_database.py
```

## Alternative: Direct Connection
If you have the database credentials and it's accessible directly, you can set the DATABASE_URL environment variable:
```bash
export DATABASE_URL="postgresql://username:password@host:port/database"
python3 explore_database.py
```

## Troubleshooting
- Make sure port 5432 is not already in use
- Check that your service account has Cloud SQL Client permissions
- Verify the instance connection name is correct
- Ensure the database exists and is accessible
