# Chatter Service - Setup & Usage Guide

This guide provides instructions to run the **NewsJuice Backend (chatter_deployed)** and **Frontend** locally for development and testing.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Backend Setup](#backend-setup)
4. [Frontend Setup](#frontend-setup)
5. [Running the Application](#running-the-application)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)

---

## 🔧 Prerequisites

Before starting, ensure you have the following installed:

- **Docker** and **Docker Compose**
- **Node.js** (v16 or higher) and **npm**
- **Google Cloud SDK** (`gcloud`)
- Access to the following Google Cloud resources:
  - Cloud SQL instance: `newsjuice-123456:us-central1:newsdb-instance`
  - Vertex AI API enabled
  - Speech-to-Text API enabled

### Required Service Account Keys

You need the following service account JSON files in the parent `secrets/` directory (three levels up from this folder):

```
../../../secrets/
├── sa-key.json                    # GCP service account for Cloud SQL & Vertex AI
└── gemini-service-account.json    # Service account for Gemini API
```

**To obtain these keys:**

1. **Create or use existing GCP project** (`newsjuice-123456` or your own)
2. **Enable required APIs**:
   ```bash
   gcloud services enable sqladmin.googleapis.com
   gcloud services enable aiplatform.googleapis.com
   gcloud services enable speech.googleapis.com
   ```

3. **Create service accounts and download keys**:
   ```bash
   mkdir -p ../../../secrets

   # Create service account for Cloud SQL and general GCP access
   gcloud iam service-accounts create newsjuice-sa \
     --display-name="NewsJuice Service Account"

   # Grant necessary roles
   gcloud projects add-iam-policy-binding newsjuice-123456 \
     --member="serviceAccount:newsjuice-sa@newsjuice-123456.iam.gserviceaccount.com" \
     --role="roles/cloudsql.client"

   gcloud projects add-iam-policy-binding newsjuice-123456 \
     --member="serviceAccount:newsjuice-sa@newsjuice-123456.iam.gserviceaccount.com" \
     --role="roles/aiplatform.user"

   # Download key
   gcloud iam service-accounts keys create ../../../secrets/sa-key.json \
     --iam-account=newsjuice-sa@newsjuice-123456.iam.gserviceaccount.com

   # Use same key for Gemini (or create separate one)
   cp ../../../secrets/sa-key.json ../../../secrets/gemini-service-account.json
   ```

---

## ⚙️ Environment Configuration

### Create `.env.local` File (if not already present)

In the `services/chatter_deployed/` directory, create a `.env.local` file with the following configuration:

```bash
# Google AI API (for Gemini Live API TTS)
# Instructions:
# 1. Visit https://aistudio.google.com/app/apikey
# 2. Create a new API key
# 3. Replace the value below with your key (PASTE INSIDE .env.local FILE YOU HAVE CREATED!)
GOOGLE_API_KEY=your_google_api_key_here

# Firebase (Optional - for user authentication)
# If you want to test Firebase authentication:
# 1. Create Firebase project at https://console.firebase.google.com/
# 2. Go to Project Settings → Service Accounts
# 3. Generate new private key and save as ../../../secrets/firebase-service-account.json
# 4. Uncomment the line below
# FIREBASE_SERVICE_ACCOUNT_PATH=../../../secrets/firebase-service-account.json
```

### Notes on API Keys

- **GOOGLE_API_KEY**: Required for text-to-speech (TTS) functionality. Get from [Google AI Studio](https://aistudio.google.com/app/apikey)
- **Firebase**: Optional for MS4 grading - the app can run without authentication for basic testing
- **Database password**: `Newsjuice25+` (URL-encoded as `Newsjuice25%2B`) 

---

## 🚀 Backend Setup

### 1. Navigate to Backend Directory

```bash
cd services/chatter_deployed
```

### 2. Verify Environment File Exists

Ensure `.env.local` is created with the configuration above.

### 3. Start Backend Services

The backend runs in Docker Compose with Cloud SQL Proxy:

```bash
# Build and start all services (Cloud SQL Proxy + API)
docker-compose -f docker-compose.local.yml build
```

This will:
- Start Cloud SQL Proxy container (connects to Cloud SQL on port 5432)
- Start the FastAPI backend on port 8080
- Mount service account keys and secrets

**Wait for the following output**:
```
api-1  | INFO:     Application startup complete.
api-1  | INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
```

### 4. Verify Backend is Running

In a new terminal:

```bash
# Check health endpoint
curl http://localhost:8080/healthz
# Should return: {"ok":true}
```

### Backend Architecture

The backend consists of:
- **FastAPI** web framework with WebSocket support
- **Speech-to-Text Client**: Converts audio to text using Google Cloud Speech-to-Text API
- **Query Enhancement**: Uses Gemini to expand user queries into sub-queries
- **RAG Retrieval**: Searches vector database (pgvector) for relevant news chunks
- **Podcast Generation**: Uses Gemini 2.5 Flash to generate podcast scripts
- **TTS (Text-to-Speech)**: Uses Gemini Live API to convert text to audio
- **User Database**: Stores user preferences and audio history in Cloud SQL

---

## 🎨 Frontend Setup

### 1. Navigate to Frontend Directory

```bash
cd services/k-frontend/podcast-app
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Start Frontend Development Server

```bash
npm run dev
```

The frontend will start on **http://localhost:3000** (configured in `vite.config.js`).

**Expected output**:
```
  VITE v5.4.21  ready in 142 ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
```

### 4. Access the Application

Open your browser and navigate to:
```
http://localhost:3000
```

### Frontend Features

- **Login/Registration**: Firebase Authentication (optional for MS4 testing)
- **Podcast Page**: Voice recording and real-time podcast generation
- **Settings**: User preferences management
- **About Us**: Team information
- **Audio History**: View past podcast interactions

---

## 🎯 Running the Application

### Step-by-Step Startup

**Terminal 1 - Start Backend**:
```bash
cd services/chatter_deployed
docker-compose -f docker-compose.local.yml --env-file .env.local up --build
```
Wait for: `Uvicorn running on http://0.0.0.0:8080`

**Terminal 2 - Start Frontend**:
```bash
cd services/k-frontend/podcast-app
npm run dev
```
Wait for: `Local: http://localhost:3000/`

**Browser**:
- Navigate to `http://localhost:3000`
- Click "Get Started" or navigate directly to the Podcast page

### Application Flow (Without Authentication)

1. **Voice Interaction**:
   - User presses and holds the record button
   - Audio is streamed via WebSocket to backend (`ws://localhost:8080/ws/chat`)
   - Backend transcribes audio using Google Cloud Speech-to-Text
   - Backend enhances query using Gemini (breaks into sub-queries)
   - Backend retrieves relevant news chunks from vector database
   - Backend generates podcast script using Gemini 2.5 Flash
   - Backend streams audio response back via WebSocket using Gemini Live API
   - Frontend plays the audio response

2. **Status Updates**:
   - Frontend displays real-time status messages during processing:
     - "Transcribing audio..."
     - "Enhancing query..."
     - "Retrieving articles..."
     - "Generating podcast..."
     - "Streaming audio..."

---

## 🧪 Testing

### Backend Health Check

```bash
curl http://localhost:8080/healthz
```
**Expected response**: `{"ok":true}`

### WebSocket Connection Test

1. Open `http://localhost:3000` in browser
2. Open browser DevTools (F12) → Console tab
3. Navigate to Podcast page
4. Press and hold the record button
5. Speak a question (e.g., "What's happening with AI research at Harvard?")
6. Release the button
7. Verify in console:
   - WebSocket connection established
   - Status messages received
   - Audio playback starts

### Backend Logs

Monitor backend logs in the terminal where Docker Compose is running:

```bash
# Look for these log messages:
[websocket] Authenticated user: <user_id>
[websocket] Received audio chunk: <size> bytes
[websocket] Starting transcription...
[websocket] Transcription complete, text: ...
[websocket] Enhancing query...
[websocket] Query enhanced into N sub-queries
[websocket] Retrieving articles...
[websocket] Generating podcast...
[websocket] Streaming audio...
```

### Testing Without Microphone

If microphone access is not available, you can test the backend directly:

```bash
# Test transcription endpoint (requires audio file)
# Note: WebSocket is the primary interface, direct HTTP testing requires custom scripts
```

---

## 🔍 Troubleshooting

### Backend Issues

**Problem**: `Database connection failed`
- **Solution**:
  - Ensure Cloud SQL Proxy container is running: `docker ps | grep cloud-sql-proxy`
  - Check `DATABASE_URL` in `.env.local` is correct
  - Verify service account has `cloudsql.client` role
  - Check logs: `docker-compose -f docker-compose.local.yml logs cloud-sql-proxy`

**Problem**: `Gemini API errors` or `GOOGLE_API_KEY not set`
- **Solution**:
  - Verify `GOOGLE_API_KEY` is set in `.env.local`
  - Get a valid key from [Google AI Studio](https://aistudio.google.com/app/apikey)
  - Restart backend after updating `.env.local`

**Problem**: `WebSocket connection fails`
- **Solution**:
  - Verify backend is running: `curl http://localhost:8080/healthz`
  - Check CORS settings: Ensure `CORS_ALLOW_ORIGINS` includes `http://localhost:3000`
  - Check browser console for specific error messages
  - Disable browser extensions that might block WebSocket connections

**Problem**: `Service account authentication failed`
- **Solution**:
  - Verify service account keys exist at `../../../secrets/sa-key.json` and `../../../secrets/gemini-service-account.json`
  - Check file permissions: `ls -la ../../../secrets/`
  - Verify service account has required roles:
    ```bash
    gcloud projects get-iam-policy newsjuice-123456 \
      --flatten="bindings[].members" \
      --filter="bindings.members:serviceAccount:*newsjuice*"
    ```

**Problem**: `No articles found` or `Empty retrieval results`
- **Solution**:
  - The scraper and loader services need to be run first to populate the database
  - Navigate to project root and run:
    ```bash
    # Run scraper to fetch articles
    cd services/scraper
    docker-compose up --build

    # Run loader to create embeddings
    cd services/loader_deployed
    docker-compose up --build
    ```
  - These are batch jobs that populate the `articles` and `chunks_vector` tables

### Frontend Issues

**Problem**: `Cannot connect to backend`
- **Solution**:
  - Verify backend is running: `curl http://localhost:8080/healthz`
  - Check browser console for CORS errors
  - Verify frontend URL in `CORS_ALLOW_ORIGINS` (`.env.local`)
  - Clear browser cache and reload

**Problem**: `Microphone not working`
- **Solution**:
  - Grant microphone permissions in browser (Chrome: Settings → Privacy → Microphone)
  - Use HTTPS or localhost (required for Web Audio API)
  - Check browser console for permission errors
  - Try a different browser (Chrome recommended)

**Problem**: `Audio playback not working`
- **Solution**:
  - Check browser console for audio errors
  - Verify browser supports Web Audio API
  - Ensure speakers/headphones are working
  - Check system volume settings

**Problem**: `npm install` fails
- **Solution**:
  - Verify Node.js version: `node --version` (should be v16+)
  - Clear npm cache: `npm cache clean --force`
  - Delete `node_modules` and `package-lock.json`, then retry:
    ```bash
    rm -rf node_modules package-lock.json
    npm install
    ```

### Database Issues

**Problem**: `Cloud SQL Proxy fails to start`
- **Solution**:
  - Check Cloud SQL instance is running in GCP Console
  - Verify instance connection string: `newsjuice-123456:us-central1:newsdb-instance`
  - Check service account key has Cloud SQL Client role
  - View proxy logs: `docker-compose -f docker-compose.local.yml logs cloud-sql-proxy`

**Problem**: `User preferences not saving`
- **Solution**:
  - Verify user is authenticated (check browser console for Firebase token)
  - Check Cloud SQL connection is active
  - Verify `users` and `user_preferences` tables exist in database

---

## 📚 Additional Information

### API Endpoints

- **Health Check**: `GET http://localhost:8080/healthz`
- **WebSocket Chat**: `ws://localhost:8080/ws/chat?token=<firebase-token>`
- **User Creation**: `POST http://localhost:8080/api/user/create` (requires auth)
- **User Preferences**:
  - `GET http://localhost:8080/api/user/preferences` (requires auth)
  - `POST http://localhost:8080/api/user/preferences` (requires auth)
- **Audio History**: `GET http://localhost:8080/api/user/history` (requires auth)

### Database Schema

The application uses PostgreSQL with pgvector extension:

- **articles**: Raw scraped news articles
- **chunks_vector**: Semantic chunks with 768-dimensional embeddings
- **users**: User profiles (Firebase UID, email)
- **user_preferences**: Key-value preferences per user
- **audio_history**: Log of questions and generated podcasts

### Cloud Deployment

The backend is deployed to Google Cloud Run:
- **Production URL**: `https://chatter-919568151211.us-central1.run.app`
- **Deployment**: Via `cloudbuild.yaml` using Cloud Build
- **Environment**: Production uses `env.yaml` instead of `.env.local`

For deployment instructions, see `README_develop_vs_deploy.md`.

---

## 🔐 Security Notes

- **Never commit** `.env.local` or service account keys to git (already in `.gitignore`)
- Use Secret Manager for production secrets
- Firebase tokens should be validated on every authenticated request
- CORS should be restricted to known origins in production

---

## 🎉 Success Checklist

- [ ] Backend running on `http://localhost:8080`
- [ ] Backend health check returns `{"ok":true}`
- [ ] Frontend running on `http://localhost:3000`
- [ ] Can access Podcast page in browser
- [ ] Can record voice input (microphone permission granted)
- [ ] Transcript appears in UI after recording
- [ ] Podcast audio is generated and plays automatically
- [ ] No errors in backend logs or browser console

Once all items are checked, you're ready to use NewsJuice! 🚀

---

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review service logs: `docker-compose -f docker-compose.local.yml logs`
3. Check browser console for frontend errors (F12 → Console tab)
4. Verify all prerequisites and environment configuration

---

## 📝 Quick Start Summary

```bash
# 1. Setup (one-time)
cd services/chatter_deployed
# Create .env.local file with configuration above
# Ensure service account keys exist in ../../../secrets/

# 2. Start Backend
docker-compose -f docker-compose.local.yml --env-file .env.local up --build

# 3. Start Frontend (new terminal)
cd services/k-frontend/podcast-app
npm install
npm run dev

# 4. Open Browser
# Navigate to http://localhost:3000
```
