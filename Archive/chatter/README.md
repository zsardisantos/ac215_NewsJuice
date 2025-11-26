# Chatter Service

A microservice that orchestrates the complete NewsJuice RAG pipeline, providing interactive podcast generation using Google's Gemini API, vector retrieval, and text-to-speech conversion.

## Features

- **RAG Pipeline Integration**: Retrieves relevant news chunks using vector similarity search
- **AI-Powered Podcast Generation**: Uses Google Gemini API to create personalized news podcasts
- **Text-to-Speech**: Converts generated text to audio using Google Cloud TTS
- **Interactive Terminal Interface**: User-friendly command-line interface
- **Conversation Logging**: Stores all interactions in PostgreSQL database
- **Volume-Mounted Services**: Integrates retriever and TTS as Python modules
- **Docker Containerization**: Fully containerized with dependency management

## Prerequisites

1. **Google Cloud Services**:
   - Vertex AI API enabled for Gemini access
   - Cloud Text-to-Speech API enabled
   - Service account with appropriate permissions
2. **Database Access**: Access to the newsdb PostgreSQL database with pgvector extension
3. **Vector Database**: Pre-populated `chunks_vector` table with embedded news chunks
4. **Environment Variables**: Proper configuration of environment variables

## Database Schema

The service uses the `llm_conversations` table with the following schema:

```sql
CREATE TABLE llm_conversations (
    id bigint NOT NULL DEFAULT,
    user_id text NOT NULL,
    model_name text NOT NULL,
    conversation_data jsonb NOT NULL containing fields for "error", "question", and "response",
    created_at timestamp with time zone DEFAULT (now()),
    updated_at timestamp with time zone DEFAULT (now())
);
```

## Environment Variables

- `DATABASE_URL`: PostgreSQL connection string
- `GEMINI_SERVICE_ACCOUNT_PATH`: Path to Gemini service account JSON file
- `TTS_SERVICE_ACCOUNT_PATH`: Path to TTS service account JSON file
- `GOOGLE_CLOUD_PROJECT`: Google Cloud project ID
- `GOOGLE_CLOUD_REGION`: Google Cloud region
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to GCP service account credentials

## Usage

### Running with Makefile (Recommended)

The service is designed to run as part of the NewsJuice pipeline:

```bash
# From the project root directory
make -f MakefileChatter chat
```

### Running with Docker Compose

```bash
# Start database proxy
docker compose up -d dbproxy

# Run chatter service
docker compose run --rm chatter
```

### Complete Pipeline Workflow

1. **Data Ingestion** (if needed):
   ```bash
   make -f MakefileChatter scrape  # Scrape news articles
   make -f MakefileChatter load    # Process and embed articles
   ```

2. **Interactive Podcast Generation**:
   ```bash
   make -f MakefileChatter chat    # Start interactive mode
   ```

### Interactive Usage

1. **Enter User ID**: The service prompts for a user identifier
2. **Enter Question**: Ask about any news topic (e.g., "What's happening with AI regulation?")
3. **RAG Pipeline Execution**:
   - Service embeds your question using sentence transformers
   - Searches `chunks_vector` table for top 2 most relevant chunks
   - Retrieves relevant news content via cosine similarity
4. **AI Podcast Generation**:
   - Sends question + retrieved chunks to Gemini API
   - Generates personalized 1-minute podcast script
5. **Text-to-Speech Conversion**:
   - Converts podcast text to audio using Google Cloud TTS
   - Saves MP3 file to `audio_output/` directory
   - Attempts to play audio automatically (if `mpv` is installed)
6. **Database Logging**: Stores conversation and response in `llm_conversations` table

## API Integration

### Google Gemini API (Vertex AI)

- Uses the `gemini-2.5-flash` model via Vertex AI
- Configured with service account authentication
- Handles API errors gracefully with fallback logging
- Generates 1-minute podcast scripts with retrieved context

### Google Cloud Text-to-Speech

- Uses `en-US-Neural2-J` voice by default
- Converts podcast text to high-quality MP3 audio
- Saves audio files to mounted `audio_output/` directory
- Supports automatic audio playback with local players

### Vector Database Integration

- **Retriever Module**: Embeds user queries using sentence transformers
- **Similarity Search**: Finds top 2 most relevant chunks via cosine similarity
- **Database Tables**: 
  - `articles`: Raw news articles from scraper
  - `chunks_vector`: Embedded and chunked content for retrieval
  - `llm_conversations`: User interactions and AI responses

### Database Logging

- Automatically creates the `llm_conversations` table if it doesn't exist
- Logs all conversations with timestamps and user IDs
- Stores error messages for failed API calls
- Uses PostgreSQL's JSON support for structured conversation data

## Error Handling

The service includes comprehensive error handling for:

- **Database Connection Failures**: Graceful fallback with retry logic
- **Gemini API Errors**: Fallback to error logging when API unavailable
- **TTS Service Errors**: Continues without audio if TTS fails
- **Vector Search Errors**: Handles missing or corrupted vector data
- **Invalid User Input**: Input validation and sanitization
- **Network Connectivity Issues**: Timeout handling and retry mechanisms
- **Service Account Authentication**: Clear error messages for credential issues

## Development

### Project Structure

```
services/chatter/
├── Dockerfile          # Container configuration
├── pyproject.toml      # Python dependencies
├── README.md          # This file
├── chatter.py         # Main application
└── wait_for_db.py     # Database readiness check

Volume-mounted services:
├── ../retriever/retriever.py    # Vector search functionality
└── ../tts/tts.py               # Text-to-speech conversion
```

### Dependencies

- `psycopg[binary]`: PostgreSQL adapter
- `google-cloud-aiplatform`: Vertex AI Gemini API client
- `google-cloud-texttospeech`: Google Cloud TTS client
- `google-auth`: Google Cloud authentication
- `sentence-transformers`: Text embedding for vector search
- `pgvector`: PostgreSQL vector extension support
- `python-dotenv`: Environment variable management

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Ensure the Cloud SQL proxy is running (`make -f MakefileChatter up-proxy`)
   - Verify DATABASE_URL is correctly set
   - Check network connectivity

2. **Gemini API Not Working**
   - Verify service account credentials are properly mounted
   - Check Vertex AI API is enabled in Google Cloud
   - Ensure service account has `roles/aiplatform.user` role

3. **TTS Service Not Working**
   - Verify Cloud Text-to-Speech API is enabled
   - Check service account has `roles/cloudtts.serviceAgent` role
   - Ensure audio output directory is writable

4. **Vector Search Not Working**
   - Verify `chunks_vector` table exists and has data
   - Check if loader service has been run (`make -f MakefileChatter load`)
   - Ensure pgvector extension is installed

5. **Audio Playback Issues**
   - Install `mpv` locally: `brew install mpv` (macOS) or `apt install mpv` (Linux)
   - Check audio files are saved in `audio_output/` directory
   - Verify audio file permissions

### Logs

The service provides detailed logging for:
- Database connection status and vector search results
- Gemini API call results and response generation
- TTS service calls and audio file generation
- Retriever service calls and similarity scores
- Error messages and stack traces
- User interaction flow and conversation logging

## Integration with NewsJuice Pipeline

This service serves as the **orchestration hub** for the complete NewsJuice RAG pipeline:

### Architecture Overview
```
┌─────────────┐    ┌─────────────┐    ┌─────────────────┐
│   Scraper   │───▶│   articles  │───▶│     Loader      │
└─────────────┘    └─────────────┘    └─────────────────┘
                                                     │
                                                     ▼
┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Chatter   │◀───│    Retriever    │◀───│ chunks_vector   │
└─────────────┘    └─────────────────┘    └─────────────────┘
       │                    │
       ▼                    ▼
┌─────────────┐    ┌─────────────────┐
│ Gemini API  │    │  Google Cloud   │
│             │    │      TTS        │
└─────────────┘    └─────────────────┘
```

### Service Integration
- **Volume-Mounted Architecture**: Integrates retriever and TTS as Python modules
- **Database Integration**: Uses same PostgreSQL connection pattern as other services
- **Docker Containerization**: Follows established containerization approach
- **Environment Consistency**: Uses consistent environment variable naming
- **Error Handling**: Implements comprehensive error handling across all integrated services

## License

This project is part of the NewsJuice prototype. All rights reserved.
