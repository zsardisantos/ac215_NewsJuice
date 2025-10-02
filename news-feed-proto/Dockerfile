# Use the official Debian-hosted Python image
FROM python:3.12-slim-bookworm

ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/home/app/.venv
#ENV GOOGLE_APPLICATION_CREDENTIALS=secrets/mega-pipeline.json

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends build-essential ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip && \
    pip install uv

RUN mkdir -p /app

# Set working directory 
WORKDIR /app

# Copy the source code
COPY --chown=app:app . ./

RUN uv sync

ENTRYPOINT ["/bin/bash"]

CMD ["-c", "source /home/app/.venv/bin/activate && exec bash"]
# TEST