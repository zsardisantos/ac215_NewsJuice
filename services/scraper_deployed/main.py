import logging
import os
import sys
from datetime import datetime

from fastapi import BackgroundTasks, FastAPI

from scrapers import scrape_tag_load

# ============== Create log file with timestamp ==============
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f"scrapers_{timestamp}.log")

# Configure logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)
logger.info(f"Logging to file: {log_file}")
# ======================================================================

app = FastAPI()


@app.get("/")
def health():
    logger.info("Health check from scrapers called")
    return {"status": "ok"}


@app.post("/process")
def process(background_tasks: BackgroundTasks):
    logger.info("=== Starting background article scraping process ===")
    background_tasks.add_task(scrape_tag_load)
    logger.info("Background task for scrapers queued successfully")
    return {"status": "started"}


@app.post("/process-sync")
def process_sync():
    """Synchronous processing - waits for completion"""
    logger.info("=== Starting synchronous article scarping process ===")
    try:
        result = scrape_tag_load()
        logger.info(f"Processing by scrapers completed successfully: {result}")
        return result
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting scraper service...")
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), log_level="info")
