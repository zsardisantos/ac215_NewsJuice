# services/chatter/wait_for_db.py
import os, time, sys, psycopg

url = os.environ["DATABASE_URL"]  # e.g. postgresql://...@dbproxy:5432/newsdb
timeout = float(os.getenv("DB_WAIT_TIMEOUT", "20"))  # seconds
deadline = time.time() + timeout

while time.time() < deadline:
    try:
        # small connect timeout so retries are quick
        with psycopg.connect(url, connect_timeout=5):
            print("DB reachable.")
            sys.exit(0)
    except Exception as e:
        print(f"DB not ready yet: {e.__class__.__name__}", flush=True)
        time.sleep(2)

print("Timed out waiting for DB", file=sys.stderr)
sys.exit(1)
