# News Feed Proto v3

This project demonstrates a prototype pipeline that:

- Reads **10 articles** from the [Harvard Gazette RSS feed](https://news.harvard.edu/gazette/feed/).  
- Treats each article’s content as **one chunk**.  
- Embeds each chunk into a **768-dimensional embedding vector** using [SentenceTransformers](https://www.sbert.net/).  
- Stores each article entry in a **PostgreSQL vector database** running on **Google Cloud SQL (GCS)**.
- The program "Vector_DB_query.py" asks for a search text, creates and embedding, does a search against the vector database and returns the top 2 articles.

---

## Database Information

- **Account:** `harvardnewsjuice@gmail.com`  
- **Project:** `NewsJuice`  
- **Instance:** `newsdb-instance`  
- **Database:** `newsdb` (PostgreSQL 15)  
- **Table:** `articles_vec`  

⚠️ The database password is managed separately (not included in this repo).

---

## Prerequisites

1. **Install Cloud SQL Proxy** (to connect to GCS database from local dev):

   ```bash
   brew install cloud-sql-proxy
   ```
   or install as part of Google Cloud SDK:

   ```bash
   brew install google-cloud-sdk
   ```

2. **Have the GCP Service Account key file** (`sa-key.json`) in your project folder.  
   This is required for authentication with the Cloud SQL instance.

---

## Usage

### 1. Start the Cloud SQL Proxy

In one terminal, from the project root:

```bash
cloud-sql-proxy   --credentials-file=./sa-key.json   --port 5432   newsjuice-123456:us-central1:newsdb-instance
```

This opens a local port (`5432`) connected securely to the Cloud SQL instance.

---

### 2. Build the Docker Container

In a **second terminal**, build the project container:

```bash
docker build -t news-feed-proto-v2 -f Dockerfile .
```

---

### 3. Run the Container

Run the pipeline and connect to the proxy:

```bash
docker run --rm -it   -e DATABASE_URL="postgresql://postgres:Newsjuice25%2B@host.docker.internal:5432/newsdb"   -v "$(pwd)":/app   news-feed-proto-v2
```

---

### 4. Execute main.py 

Run the app in the container:

```bash
python main.py
```

### 5. Execute main.py 

Run the app in the container:

```bash
python Vector_DB_query.py
```

---

## Expected Result

If everything is configured correctly:

main.py:

- The program will fetch **10 latest Harvard Gazette articles**.  
- Each article will be embedded into a **768-dim vector**.  
- 10 rows will be inserted into the `articles_vec` table in the `newsdb` database.

Check the table contents to verify:

```sql
SELECT *
FROM articles_vec
ORDER BY pubdate DESC;
```

Vector_DB_query.py:

- Asks for a search text
- Generates an embedding for it
- Accesses the database table articles_vec
- Returns the top 2 matches


---

## Notes

- In **development**, you must run the Cloud SQL proxy locally.  
- In **production**, direct access to the managed Cloud SQL database can be configured, and the proxy may not be needed.  
- Embeddings are generated using the `sentence-transformers` library, model: `all-mpnet-base-v2`.
---

## License

This project is part of the **NewsJuice** prototype. All rights reserved.
