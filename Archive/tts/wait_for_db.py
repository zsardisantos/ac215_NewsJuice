#!/usr/bin/env python3
"""
Wait for database to be ready
"""

import time
import os
import sys

# Add the virtual environment to the path
sys.path.insert(0, '/app/.venv/lib/python3.12/site-packages')

import psycopg

def wait_for_db():
    """Wait for database to be available."""
    max_retries = 30
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            conn = psycopg.connect(os.environ["DATABASE_URL"], autocommit=True)
            conn.close()
            print("DB reachable.")
            return True
        except Exception as e:
            retry_count += 1
            print(f"DB not ready, retrying... ({retry_count}/{max_retries})")
            time.sleep(2)
    
    print("DB not reachable after maximum retries")
    return False

if __name__ == "__main__":
    wait_for_db()
