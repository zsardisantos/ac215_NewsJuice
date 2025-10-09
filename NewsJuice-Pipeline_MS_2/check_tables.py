#!/usr/bin/env python3
"""
Script to check existing tables in the NewsJuice database
"""

import os
import psycopg
from pgvector.psycopg import register_vector

def check_database_tables():
    """Connect to database and list all existing tables"""
    
    # Get database URL from environment
    DB_URL = os.environ.get("DATABASE_URL")
    if not DB_URL:
        print("❌ DATABASE_URL environment variable not set!")
        print("Please set it to: postgresql://postgres:Newsjuice25%2B@localhost:5432/newsdb")
        return
    
    try:
        # Connect to database
        with psycopg.connect(DB_URL, autocommit=True) as conn:
            register_vector(conn)
            
            with conn.cursor() as cur:
                # Get database info
                cur.execute("SELECT current_database(), version();")
                db_name, db_version = cur.fetchone()
                print(f"🔗 Connected to database: '{db_name}'")
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
                    else:
                        print("❌ llm_conversations table does NOT exist")
                    
                    if 'llm_messages' in table_names:
                        print("✅ llm_messages table EXISTS!")
                    else:
                        print("❌ llm_messages table does NOT exist")
                        
                else:
                    print("📭 No tables found in the database")
                    
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        print("\n💡 Make sure:")
        print("   1. Cloud SQL Proxy is running")
        print("   2. DATABASE_URL is set correctly")
        print("   3. Database credentials are valid")

if __name__ == "__main__":
    check_database_tables()