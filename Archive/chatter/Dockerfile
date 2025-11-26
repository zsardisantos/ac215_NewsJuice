# Chatter service Dockerfile
FROM python:3.12-slim-bookworm

ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/home/app/.venv
ENV VIRTUAL_ENV=/home/app/.venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip && \
    pip install uv

# Set working directory 
WORKDIR /app

# Copy the source code
COPY pyproject.toml ./

RUN uv sync

COPY . ./

# Default command (Compose will override with wait_for_db + your script)
CMD ["python", "chatter.py"]
