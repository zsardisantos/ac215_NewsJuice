from fastapi import FastAPI, BackgroundTasks
from loader import chunk_embed_load
import os

app = FastAPI()


@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/process")
def process(background_tasks: BackgroundTasks):
    background_tasks.add_task(chunk_embed_load, "semantic-split")
    return {"status": "started"}


# For testing only
@app.post("/process-sync")
def process_sync():
    """Synchronous processing - waits for completion"""
    try:
        result = chunk_embed_load(method="semantic-split")
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
