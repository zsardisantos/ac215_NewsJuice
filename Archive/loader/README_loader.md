# Loader module


- Loads articles from `articles` table in the DB (only entries with vflag = 0, this flag indicates which article is already chunked and vectorized) 
   - Performs **chunking & embedding**  
   - Adds new article chunks to the **vector DB** (table `chunks_vector`)  
- use the same embedder for final chunk embedding as Zac 


Uses Vertex AI for embeddings of the chunks
**Chunking option available**
- `char-split` character splitting
- `recursive-split` recursive splitting
- `semantic-split` (using embedding model below)

Database Information
- **Account:** `harvardnewsjuice@gmail.com`  
- **Project:** `NewsJuice`  
- **Project ID:** `newsjuice-123456`
- **Instance:** `newsdb-instance`  
- **Region:** `us-central1`
- **Database:** `newsdb` (PostgreSQL 15)  
- **Table:** IN: `articles`, OUT:`chunks_vector`  
- Service account used for all GC services in this module (PosgresSQL, VertexAI) = 


## Usage 
```bash
make -f MakefileLoader_new run (ups SQL proxy, builds and runs)  
```
```bash
docker compose run --rm loader (just run)  
```



# APPENDIX

##E mbedding used:  

Library: google-genai is Google’s official Python SDK for interacting with the Gemini family of generative AI models (like gemini-1.5-pro, gemini-2.0-flash, etc.).  
It lets your code talk directly to Google’s GenAI API, which can be accessed in two ways:  
- **Directly** via Google AI Studio (using an API key)  
- **Via Vertex** AI (in Google Cloud) — using a GCP project and service account  
Here: We are accessing Google’s Gemini models through Vertex AI’s managed GenAI service rather than through the lightweight public API key route.  

The google-genai library:
- Handles all the API calls to Gemini models
- Authenticates automatically (with a Google Cloud project or API key)
- Provides simple methods for: 
text generation (generate_content)
chat (start_chat, send_message)
embeddings (embed_content)
multimodal inputs (text + image)
streaming responses

vertexai=True in your client:
tells the library to:
- Send requests to Vertex AI’s managed Gemini endpoint

- Use your GCP project billing, IAM permissions, and regional deployment

- Integrate with other Vertex services (data, tuning, monitoring)
