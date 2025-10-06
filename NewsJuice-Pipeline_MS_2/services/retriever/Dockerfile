# Retriever Dockerfile
FROM python:3.12-slim-bookworm

ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/home/app/.venv
ENV VIRTUAL_ENV=/home/app/.venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends build-essential ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip && \
    pip install uv

# Set working directory 
WORKDIR /app

# Copy the source code
#COPY --chown=app:app . ./
COPY pyproject.toml ./
#COPY uv.lock

RUN uv sync

COPY . ./

#ENTRYPOINT ["/bin/bash"]
#CMD ["-c", "source /home/app/.venv/bin/activate && exec bash"]
# Default command (Compose will override with wait_for_db + your script)
CMD ["python", "retriever.py"]