# 📆 NewsJuice (AC215 - Milestone 2)

> Personalized daily podcast summaries of Harvard-related news — built with a scalable RAG pipeline.

---

## 👥 Team

- **Khaled Aly**  
- **Zac Sardi-Santos**  
- **Joshua Rosenblum**  
- **Christian Michel**

**Team name:** `NewsJuice`

---

## 📚 Project Overview

**NewsJuice** is an application that generates a **customized podcasts** summarizing the latest news based on the user’s interests.  
It is primarily designed for the **Harvard community**, pulling content from Harvard-related news sources.

Users can:
- Set preferences and topics of interest  
- Provide a short news brief  
- Receive an **audio podcast** generated automatically  
- *(Future)* Interactively **ask follow-up questions** during playback  

---

## 🎯 Milestone 2 — Prototype Scope

In Milestone 2, we built a complete **RAG (Retrieval-Augmented Generation)** pipeline with the following features:

1. **Scraping:** Collect Harvard-related news (RSS/Atom feeds, websites, etc.)  
2. **Ingestion:** Load scraped data into a **PostgreSQL database** (hosted on GCP)  
3. **Processing:**  
   - Semantic chunking (using Vertex AI)  
   - Text embedding (using `sentence-transformers/all-mpnet-base-v2`)  
4. **Vector Storage:** Store embeddings in a **pgvector**-enabled PostgreSQL database  
5. **Retrieval & Summarization:**  
   - Retrieve the most relevant news based on user brief  
   - Generate a summary with an LLM  
   - Convert it to audio (mp3) via TTS  

---

## ⚙️ Pipeline Architecture

![Project Architecture](app_architecture.png)

The pipeline consists of **three containers**, each responsible for a specific stage.  
A **PostgreSQL vector database** (on **Google Cloud SQL**) serves as the central data store.

### 🧱 Containers

1. **🕸️ Scraper**  
   - Fetches news articles from multiple Harvard-related sources on the web 
   - Stores them in the `articles` table of the PostgreSQL database `newsdb`

2. **📥 Loader**  
   - Loads unprocessed articles (`vflag = 0`) from the `articles` table of `newsdb`
   - Performs **chunking** and **embedding**  
   - Stores the chunks in the `chunks_vector` table of `newsdb`

3. **🔍 Chatter**  
   - Accepts a user’s **news briefing** via user interface
   - **Embeds** the briefing and **retrieves the most relevant chunks** (top-n)
   - **Combines** retrieved chunks with the briefing and user preferences (**promt augmentation**) 
   - Generates a summary via an **LLM** from the augmented prompt
   - Produces an **audio podcast file** (MP3) from the summary via text-to-speech conversion
   - The chat history is stored in the `newsdb`


---

## 🚀 Usage

This project supports both **one-line execution** and **step-by-step** runs using `docker-compose` and `Makefile`.

### ▶️ Quick Start (One-line)

**Option 1: Makefile** for a scraper - loader batch cycle and for a chatter cycle

```bash
make -f MakefileBatch run
make -f MakefileChatter run

```

**Option 2: Docker Compose**

**one command**

```bash
docker compose build \
  && docker compose up -d dbproxy \
  && docker compose run --rm scraper \
  && docker compose run --rm loader \
  && docker compose run --rm chatter
```

**step by step**

```bash
docker compose build
docker compose up -d dbproxy
docker compose run --rm scraper
docker compose run --rm loader
docker compose run --rm chatter
```

---


To stop all services:
```bash
docker compose down
```

---

## 🔑 Prerequisites

1. **Install Cloud SQL Proxy** (to connect locally to the GCS-hosted database):

```bash
brew install cloud-sql-proxy
```
Or via Google Cloud SDK:
```bash
brew install google-cloud-sdk
```

2. **Service Account Key**  
   Place your GCP service account key file here:
```
../secrets/sa-key.json
```
Service account:  
`newsjuice-proxy@newsjuice-123456.iam.gserviceaccount.com`

The SQL proxy runs automatically via `docker-compose`, opening a local port (`5432`) that connects securely to the Cloud SQL instance.

---

## 📊 Data

**News Sources:** (WIP)

✅ The Harvard Gazette
    https://news.harvard.edu/gazette/feed/
✅ The Harvard Crimson
    https://www.thecrimson.com/
- Harvard Magazine
    https://www.harvardmagazine.com/harvard-headlines
- Colloquy: The alumni newsletter for the Graduate School of Arts and Sciences.
    https://gsas.harvard.edu/news/all
- Harvard Business School Communications Office: Publishes news and research from the business school.
    https://www.hbs.edu/news/Pages/browse.aspx
- Harvard Law Today: The news hub for Harvard Law School.
    https://hls.harvard.edu/today/
- Harvard Medical School Office of Communications and External Relations - News: Disseminates news from the medical school.
    https://hms.harvard.edu/news

---

---

## 🗄️ Database Details

- **Account:** `harvardnewsjuice@gmail.com`  
- **Project:** `NewsJuice`  
- **Project ID:** `newsjuice-123456`  
- **Instance:** `newsdb-instance`  
- **Region:** `us-central1`  
- **Database:** `newsdb` (PostgreSQL 15)  
- **Tables:** `articles`, `chunks_vector`  

> ⚠️ **Note:** The above identifiers are for documentation and environment setup. Do not commit actual secrets to version control.

---

## 📊 Database Schema

### 📰 Table: `articles`
Stores raw scraped news articles.

```sql
id BIGSERIAL PRIMARY KEY,
author TEXT,
title TEXT,
summary TEXT,
content TEXT,
source_link TEXT, 
source_type TEXT,
fetched_at TIMESTAMPTZ,
published_at TIMESTAMPTZ,
vflag INT,
article_id TEXT
```

### 🧠 Table: `chunks_vector`
Stores semantic chunks and vector embeddings.

```sql
id BIGSERIAL PRIMARY KEY,
author TEXT,
title TEXT,
summary TEXT,
content TEXT,
source_link TEXT, 
source_type TEXT,
fetched_at TIMESTAMPTZ,
published_at TIMESTAMPTZ,
chunk TEXT,
chunk_index INT,
embedding VECTOR(768),
article_id TEXT
```

### 🧠 Table: `llm conversations`
Stores the history of conversations

```sql
id BIGSERIAL PRIMARY KEY,
user_id
model_name
conversation_date
created_at
updated_at
```

---


## References

For this project we have used ChatGPT, Gemini and tools like app.eraser.io for learrning purposes.

## 📜 License

This project is part of the **NewsJuice** prototype.  
All rights reserved.