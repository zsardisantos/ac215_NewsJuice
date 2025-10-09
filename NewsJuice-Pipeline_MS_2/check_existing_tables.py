#!/usr/bin/env python3
"""
Script to check existing tables in the NewsJuice database
This version tries multiple connection methods
"""

import os
import psycopg
from pgvector.psycopg import register_vector

def check_database_tables():
    """Connect to database and list all existing tables"""
    
    # Try different connection URLs
    connection_urls = [
        os.environ.get("DATABASE_URL"),
        "postgresql://postgres:Newsjuice25%2B@localhost:5432/newsdb",
        "postgresql://postgres:Newsjuice25%2B@127.0.0.1:5432/newsdb",
        "postgresql://postgres:Newsjuice25%2B@dbproxy:5432/newsdb"
    ]
    
    # Filter out None values
    connection_urls = [url for url in connection_urls if url]
    
    if not connection_urls:
        print("❌ No database connection URLs found!")
        print("Please set DATABASE_URL environment variable or ensure Cloud SQL Proxy is running")
        return False
    
    for i, db_url in enumerate(connection_urls):
        print(f"\n🔗 Attempting connection {i+1}/{len(connection_urls)}: {db_url.split('@')[1] if '@' in db_url else 'unknown'}")
        
        try:
            # Connect to database
            with psycopg.connect(db_url, autocommit=True) as conn:
                register_vector(conn)
                
                with conn.cursor() as cur:
                    # Get database info
                    cur.execute("SELECT current_database(), version();")
                    db_name, db_version = cur.fetchone()
                    print(f"✅ Connected to database: '{db_name}'")
                    print(f"📊 PostgreSQL version: {db_version}")
                    print()
                    
                    # List all tables
                    cur.execute("""
                        SELECT table_name, table_type 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public'
                        ORDER BY table_name;
                    """)
                    
                    tables = cur.fetchall()
                    
                    if tables:
                        print("📋 Existing tables in the database:")
                        print("-" * 50)
                        for table_name, table_type in tables:
                            print(f"  • {table_name} ({table_type})")
                        
                        print()
                        
                        # Check specifically for LLM conversation tables
                        table_names = [t[0] for t in tables]
                        
                        if 'llm_conversations' in table_names:
                            print("✅ llm_conversations table EXISTS!")
                            
                            # Get table structure
                            cur.execute("""
                                SELECT column_name, data_type, is_nullable
                                FROM information_schema.columns 
                                WHERE table_name = 'llm_conversations'
                                ORDER BY ordinal_position;
                            """)
                            columns = cur.fetchall()
                            print("   Table structure:")
                            for col_name, data_type, nullable in columns:
                                print(f"     - {col_name}: {data_type} {'NULL' if nullable == 'YES' else 'NOT NULL'}")
                                
                            # Get row count
                            cur.execute("SELECT COUNT(*) FROM llm_conversations;")
                            row_count = cur.fetchone()[0]
                            print(f"   Row count: {row_count}")
                        else:
                            print("❌ llm_conversations table does NOT exist")
                        
                        if 'llm_messages' in table_names:
                            print("✅ llm_messages table EXISTS!")
                            
                            # Get row count
                            cur.execute("SELECT COUNT(*) FROM llm_messages;")
                            row_count = cur.fetchone()[0]
                            print(f"   Row count: {row_count}")
                        else:
                            print("❌ llm_messages table does NOT exist")
                            
                        # Check for other interesting tables
                        interesting_tables = ['chunks_vector', 'news', 'articles']
                        for table in interesting_tables:
                            if table in table_names:
                                cur.execute(f"SELECT COUNT(*) FROM {table};")
                                row_count = cur.fetchone()[0]
                                print(f"📊 {table} table: {row_count} rows")
                        
                        return True
                        
                    else:
                        print("📭 No tables found in the database")
                        return True
                        
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            continue
    
    print("\n❌ All connection attempts failed!")
    print("\n💡 To fix this, try one of these options:")
    print("1. Start Cloud SQL Proxy:")
    print("   cloud-sql-proxy --credentials-file=./secrets/sa-key.json --port 5432 newsjuice-123456:us-central1:newsdb-instance")
    print("2. Use Docker Compose:")
    print("   docker-compose up dbproxy")
    print("3. Set DATABASE_URL environment variable")
    print("   export DATABASE_URL='postgresql://postgres:Newsjuice25%2B@localhost:5432/newsdb'")
    
    return False

if __name__ == "__main__":
    print("🔍 Checking NewsJuice Database Tables")
    print("=" * 50)
    
    success = check_database_tables()
    
    if success:
        print("\n✅ Database check completed successfully!")
    else:
        print("\n❌ Database check failed. Please see the suggestions above.")