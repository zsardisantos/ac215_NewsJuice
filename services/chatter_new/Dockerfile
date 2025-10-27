FROM python:3.11-slim-bookworm


# make sure any fallback HF downloads (if any) go to a writable tmp
ENV PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/home/app/.venv \
    VIRTUAL_ENV=/home/app/.venv \
    PATH="/home/app/.venv/bin:${PATH}" \
    PORT=8080 \
    HF_HOME=/tmp \
    HUGGINGFACE_HUB_CACHE=/tmp/transformers \
    HF_HUB_ENABLE_HF_TRANSFERS=1

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip && pip install uv

WORKDIR /app

# Install deps (cache-friendly)
COPY pyproject.toml ./
RUN uv lock && uv sync --no-dev


# Allow passing an HF token at build time to avoid 429s when baking the model
ARG HUGGING_FACE_HUB_TOKEN
ENV HUGGING_FACE_HUB_TOKEN=${HUGGING_FACE_HUB_TOKEN}


# --- Bake the SentenceTransformer model into the image (no heredoc) ---
RUN mkdir -p /app/models/all-mpnet-base-v2 && \
    uv run python -c "from sentence_transformers import SentenceTransformer as S; \
m=S('sentence-transformers/all-mpnet-base-v2'); \
m.save('/app/models/all-mpnet-base-v2'); \
print('Saved model to /app/models/all-mpnet-base-v2')"
# Expose model path to the app
ENV SENTENCE_MODEL_PATH=/app/models/all-mpnet-base-v2

# App code
COPY . .

EXPOSE 8080
#CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
#CMD python wait_for_db.py && uv run uvicorn main:app --host 0.0.0.0 --port 8080
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]