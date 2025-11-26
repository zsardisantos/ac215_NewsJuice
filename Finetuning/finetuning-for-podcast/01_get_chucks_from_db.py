#############################################################################
###### This script is designed to run on colab. It was not tested elsewhere
#############################################################################
###### Dont forget to have the env variables setup in colab
#############################################################################

print("Starting Chuncks Extractions")
import os
import json
import csv
import pg8000
from tqdm.auto import trange
from google.cloud.sql.connector import Connector, IPTypes


print("Finished Loading Dependancies")
# Configuration
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "../secrets/gemini-service-account.json"

output ="Output/01_get_chuncks_from_db.csv"

INSTANCE_CONNECTION_NAME = "newsjuice-123456:us-central1:newsdb-instance"
DB_NAME = "newsdb"
DB_USER = "postgres"
try:
    with open("../secrets/DB_password.txt", "r") as f:
         DB_PASSWORD = f.readline().strip()
except FileNotFoundError:
    print("Error: DB_password.txt not found.")
    DB_PASSWORD = None

connector = Connector()

def connect_to_gc_db():
    """Connects to Cloud SQL using the Connector."""
    
    if not DB_PASSWORD:
        print("Cannot connect: DB_PASSWORD is not set.")
        return None
        
    print("Connecting to database...")
    
    conn = connector.connect(
        INSTANCE_CONNECTION_NAME,
        "pg8000",  # This is now the correct driver string
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        ip_type=IPTypes.PUBLIC 
    )
    conn.autocommit = True
    
    print("Connection successful!")
    return conn  # <-- THE MISSING RETURN STATEMENT


def get_random_chunk(conn):
    """Extract a random chunk from the chunks_vector table."""
    cur = None  # Define cursor outside the try block
    try:
        cur = conn.cursor()  # Create the cursor
        
        # Get a random chunk with all relevant fields
        cur.execute("""
            SELECT 
                author, title, summary, content,
                source_link, source_type, fetched_at, published_at,
                chunk, chunk_index, article_id
            FROM chunks_vector
            ORDER BY RANDOM()
            LIMIT 1;
        """)
        
        row = cur.fetchone()
        
        if row:
            chunk_data = {
                "author": row[0],
                "title": row[1],
                "summary": row[2],
                "content": row[3],
                "source_link": row[4],
                "source_type": row[5],
                "fetched_at": row[6],
                "published_at": row[7],
                "chunk": row[8],
                "chunk_index": row[9],
                "article_id": row[10]
            }
            return chunk_data, None
        else:
            return None, "No chunks found in chunks_vector table"
            
    except Exception as e:
        return None, f"Error fetching random chunk: {e}"
    finally:
        # This is critical: make sure the cursor is always closed
        if cur:
            cur.close()

def get_and_save_chunks(conn, training_samples, filename=output):
    """
    Fetch random chunks from the database and save their 'content' 
    field to a single-column CSV file.
    """
    chunks = []
    print(f"Fetching {training_samples} random chunks...")
    
    # Fetch all the chunks first
    for _ in trange(training_samples, desc="Fetching Chunks"):
        chunk, error = get_random_chunk(conn)
        if error:
            print(f"[error] {error}")
        else:
            chunks.append(chunk)
    
    # Now, write only the 'content' field to the CSV
    print(f"Saving 'content' of {len(chunks)} chunks to {filename}...")
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            # Create a CSV writer object
            writer = csv.writer(f)
            
            # Write the header row
            writer.writerow(["content"])
            
            # Write the 'content' from each chunk as a new row
            for chunk in chunks:
                if chunk and 'content' in chunk:
                    writer.writerow([chunk['content']])
                    
    except Exception as e:
        print(f"Error saving to CSV: {e}")

    print(f"Successfully saved 'content' to {filename}")
    return chunks


if __name__=="__main__":
  print("Connecting to Cloud DB")
  conn = connect_to_gc_db()
  print("Starting Extraction") 
  get_and_save_chunks(conn, 2000)
  connector.close() 