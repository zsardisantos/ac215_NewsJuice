# Extractor Dockerfile
FROM python:3.12-slim-bookworm

ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/home/app/.venv
ENV VIRTUAL_ENV=/home/app/.venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"
ENV PORT=8080

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends build-essential ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip && \
    pip install uv

# Set working directory
WORKDIR /app

# Create secrets directory for mounting
RUN mkdir -p /app/secrets

# Copy the source code
#COPY --chown=app:app . ./
COPY pyproject.toml uv.lock ./

# Install all dependencies including dev tools
RUN uv sync --extra dev


# Copy application code
COPY src/api-service/api/ ./api/
COPY tests/ ./tests/
COPY pytest.ini ./
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["/bin/bash", "docker-entrypoint.sh"]
