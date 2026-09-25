# NewsJuice — local demo runbook

Goal: the full voice loop running on your laptop, no GKE, no Pulumi, no Cloud SQL,
no CI/CD. Everything below is localhost except three managed Google APIs.

**Target: working end-to-end, then a backup screen recording.**

---

## Step 0 — Install the CLI (5 min)

```bash
brew install --cask google-cloud-sdk
```

Then `gcloud init` and sign in.

---

## Step 1 — The 20-minute lottery ticket (timeboxed, do not overrun)

If you still have access to the old project, you get the real 53MB corpus and skip
all the scraping. **Set a timer for 20 minutes.**

```bash
gcloud auth login
gcloud auth application-default login
gsutil ls gs://newsjuice-data-versions-loader/
```

- **It lists** → you have access. Go to Step 1a.
- **403 / does not exist** → you don't. Skip to Step 2 and forget this path.

### Step 1a — pull the dump (only if the bucket listed)

```bash
cd services/loader_deployed/data/exports
dvc pull db_export_20251112_232618.sql.dvc
```

That gives you a full Postgres dump. After Step 3, restore it instead of seeding:

```bash
docker exec -i newsjuice-db psql -U postgres -d newsdb < db_export_20251112_232618.sql
```

If the dump's schema conflicts, don't fight it — drop the volume and let the dump
create its own tables.

---

## Step 2 — New GCP project + the three APIs (20 min)

New accounts get $300 in credits. You need Vertex AI (embeddings + Gemini),
Speech-to-Text, and Text-to-Speech. Nothing else.

```bash
gcloud projects create newsjuice-demo-$RANDOM --name="NewsJuice Demo"
gcloud config set project <the-id-it-printed>
```

Link billing in the console (required even on free credits), then:

```bash
gcloud services enable aiplatform.googleapis.com speech.googleapis.com texttospeech.googleapis.com
```

Service account + key:

```bash
gcloud iam service-accounts create newsjuice-demo --display-name="NewsJuice Demo"

PROJECT=$(gcloud config get-value project)
SA="newsjuice-demo@${PROJECT}.iam.gserviceaccount.com"

for ROLE in roles/aiplatform.user roles/speech.client roles/cloudtranslate.user; do
  gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$SA" --role="$ROLE"
done

mkdir -p ~/secrets
gcloud iam service-accounts keys create ~/secrets/newsjuice-demo-sa.json --iam-account="$SA"
```

> Note: `~/secrets/sa-key.json` and `~/secrets/gemini-service-account.json` currently
> exist as **empty directories**. Delete them so nothing mounts over your new key:
> `rmdir ~/secrets/sa-key.json ~/secrets/gemini-service-account.json`

---

## Step 3 — Local Postgres + pgvector (5 min)

```bash
docker compose -f demo-local/docker-compose.yml up -d
docker compose -f demo-local/docker-compose.yml logs -f db   # wait for "ready to accept connections"
```

Verify the schema applied:

```bash
docker exec -it newsjuice-db psql -U postgres -d newsdb -c "\dt"
```

You should see `articles`, `chunks_vector`, `users`, `user_preferences`, `audio_history`.

---

## Step 4 — Seed the corpus (30–45 min)

Only if Step 1a didn't give you the dump.

```bash
export DATABASE_URL="postgresql://postgres:newsjuice@localhost:5433/newsdb"
export GOOGLE_CLOUD_PROJECT="$(gcloud config get-value project)"
export GOOGLE_CLOUD_REGION=us-central1
export GOOGLE_APPLICATION_CREDENTIALS=~/secrets/newsjuice-demo-sa.json
```

Dry run first — no GCP, no cost, proves the scrape works:

```bash
uv run --with feedparser --with trafilatura --with httpx \
       --with "psycopg[binary]" --with pgvector --with google-genai \
       demo-local/seed.py --limit 5 --dry-run
```

Four feeds are wired and **verified working on 2026-09-24**: Harvard Gazette,
Harvard Magazine, Harvard Law School, Harvard Kennedy School. The Gazette and
Magazine give long, substantive articles (5k–34k chars); HLS/HKS entries are
short stubs. The Crimson's RSS endpoints all 404 now, so it's omitted.

Then the real thing (~40 articles per feed ≈ 1500+ chunks, a few cents):

```bash
uv run --with feedparser --with trafilatura --with httpx \
       --with "psycopg[binary]" --with pgvector --with google-genai \
       demo-local/seed.py --limit 40
```

Sanity check what you can now demo:

```bash
docker exec -it newsjuice-db psql -U postgres -d newsdb -c \
  "SELECT source_type, count(*) FROM chunks_vector GROUP BY 1;"
docker exec -it newsjuice-db psql -U postgres -d newsdb -c \
  "SELECT DISTINCT title FROM chunks_vector LIMIT 30;"
```

**Read those titles.** They are the only things your demo can answer about. Write
your demo questions from this list, not from memory of November's corpus.

---

## Step 5 — Run chatter (20 min)

> `--env-file .env` matters: `main.py` imports `user_db` (which requires `DATABASE_URL`)
> before it calls `load_dotenv()`, so without it the server fails to start in a fresh tab.

```bash
cp demo-local/env.local.example services/chatter_deployed/.env
# edit: GOOGLE_CLOUD_PROJECT + GOOGLE_APPLICATION_CREDENTIALS
```

```bash
cd services/chatter_deployed
uv sync --all-extras
uv run uvicorn main:app --env-file .env --host 0.0.0.0 --port 8080 --reload
```

Health check:

```bash
curl -s localhost:8080/health
```

---

## Step 6 — Run the frontend (15 min)

The dev build already points at `http://localhost:8080` and
`ws://localhost:8080/ws/chat` ([Podcast.jsx:640](../services/frontend/podcast-app/src/pages/Podcast.jsx:640)),
so no rewiring.

```bash
cd services/frontend/podcast-app
npm install
npm run dev        # http://localhost:5173
```

### Auth: the one thing that needs a decision

The committed Firebase web config points at the old `newsjuice-123456` project. Client-side
login may still work (Firebase Auth has no expiry), **but your backend can't verify those
tokens without that project's admin credentials** — and an unverifiable token is *worse*
than none: [main.py:344](../services/chatter_deployed/main.py:344) closes the socket on a
failed verify, while [main.py:357](../services/chatter_deployed/main.py:357) happily
proceeds with no token at all.

So for the demo: **send no token.** In `Podcast.jsx`, make the WebSocket URL tokenless:

```js
return `ws://localhost:8080/ws/chat`
```

and route straight to `/podcast` instead of through `/login`. You lose saved preferences
and history (voice falls back to the Chirp3-HD default); the voice loop is unaffected.

---

## Step 7 — Verify, then RECORD (30 min)

Walk the whole loop: hold to record → ask a question → hear the answer.

**The moment it works, record a 3-minute QuickTime screen capture** (⌘⇧5, include
microphone audio). This is your insurance. Do it before polishing anything.

Then find 3–4 questions that retrieve well against your seeded titles and rehearse
those exact questions. Include one follow-up ("tell me more about that") to trigger
the `CONTEXTUAL` branch that skips retrieval.

---

## Troubleshooting

| Symptom | Cause |
|---|---|
| `relation "chunks_vector" does not exist` | Schema didn't apply. `docker compose down -v` and up again. |
| Retrieval returns 0 chunks | Nothing seeded, or asking about topics outside your ~40 articles. |
| Fluent answer with invented facts | Empty-context bug. Check the `[gemini-debug]` logs for `context_text` length. |
| Transcription fails | STT probes 5 sample rates; if all fail check the mic gave 16-bit PCM. |
| `403 PERMISSION_DENIED` on embed | Missing `roles/aiplatform.user`, or `GOOGLE_APPLICATION_CREDENTIALS` unset in that shell. |
| `cannot import name 'Vector' from 'pgvector.psycopg'` | pgvector moved `Vector` to the package root after 0.4.1. `uv.lock` pins 0.4.1 so `uv sync` is safe — **never** `uv pip install pgvector` unpinned in the chatter venv, or `retriever.py:22` will fail at import and chatter won't boot. |
| WebSocket closes instantly | A token is being sent that the backend can't verify. Strip it. |

---

## Do NOT do before Friday

Pulumi, GKE, Cloud Run, CI/CD, Cloud SQL, DNS, TLS, the load test. None of it is
demoable on Zoom and none of it is yours to claim.
