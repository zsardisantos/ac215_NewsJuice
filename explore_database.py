#!/usr/bin/env python3
"""
Database Explorer Script for NewsJuice PostgreSQL Database
This script connects to the database and shows all tables with their contents.
"""

import psycopg2
import os
import json
from datetime import datetime

def connect_to_database():
    """Connect to the PostgreSQL database"""
    try:
        # Try different connection methods
        connection_strings = [
            'postgresql://postgres:Newsjuice25%2B@localhost:5432/newsdb',
            'postgresql://postgres:Newsjuice25%2B@127.0.0.1:5432/newsdb',
            os.environ.get('DATABASE_URL', 'postgresql://postgres:Newsjuice25%2B@localhost:5432/newsdb')
        ]
        
        for conn_str in connection_strings:
            try:
                print(f"Trying connection: {conn_str}")
                conn = psycopg2.connect(conn_str)
                print("✓ Connected successfully!")
                return conn
            except Exception as e:
                print(f"✗ Failed: {e}")
                continue
        
        raise Exception("Could not connect with any connection string")
        
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def get_table_info(cursor, table_name):
    """Get detailed information about a table"""
    # Get column information
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default, character_maximum_length
        FROM information_schema.columns 
        WHERE table_name = %s
        ORDER BY ordinal_position;
    """, (table_name,))
    
    columns = cursor.fetchall()
    
    # Get row count
    cursor.execute(f'SELECT COUNT(*) FROM "{table_name}";')
    count = cursor.fetchone()[0]
    
    # Get table size
    cursor.execute("""
        SELECT pg_size_pretty(pg_total_relation_size(%s)) as size
    """, (table_name,))
    size = cursor.fetchone()[0]
    
    return columns, count, size

def format_value(value, max_length=100):
    """Format a value for display"""
    if value is None:
        return "NULL"
    
    value_str = str(value)
    if len(value_str) > max_length:
        return value_str[:max_length] + "..."
    return value_str

def explore_database():
    """Main function to explore the database"""
    print("=" * 80)
    print("🗄️  NEWSJUICE DATABASE EXPLORER")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Connect to database
    conn = connect_to_database()
    if not conn:
        print("\n❌ Could not connect to database.")
        print("Please make sure:")
        print("1. Cloud SQL proxy is running: ./cloud-sql-proxy --credentials-file=./secrets/sa-key.json --port 5432 newsjuice-123456:us-central1:newsdb-instance")
        print("2. Service account key file exists at ./secrets/sa-key.json")
        print("3. Database credentials are correct")
        return
    
    cursor = conn.cursor()
    
    try:
        # Get database info
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()[0]
        print(f"📊 Database: {db_version}")
        print()
        
        # Get list of all tables
        cursor.execute("""
            SELECT table_name, table_type
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        
        if not tables:
            print("❌ No tables found in the database.")
            return
        
        print(f"📋 Found {len(tables)} table(s):")
        for table_name, table_type in tables:
            print(f"  • {table_name} ({table_type})")
        print()
        
        # Explore each table
        for table_name, table_type in tables:
            print("=" * 80)
            print(f"📋 TABLE: {table_name.upper()}")
            print("=" * 80)
            
            # Get table information
            columns, row_count, table_size = get_table_info(cursor, table_name)
            
            print(f"📊 Rows: {row_count:,} | Size: {table_size}")
            print()
            
            # Show column information
            print("🏗️  COLUMNS:")
            for col in columns:
                col_name, data_type, nullable, default, max_length = col
                nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
                length_str = f"({max_length})" if max_length else ""
                default_str = f" DEFAULT {default}" if default else ""
                print(f"  • {col_name}: {data_type}{length_str} {nullable_str}{default_str}")
            print()
            
            # Show sample data
            if row_count > 0:
                print("📄 SAMPLE DATA (first 5 rows):")
                cursor.execute(f'SELECT * FROM "{table_name}" LIMIT 5;')
                sample_data = cursor.fetchall()
                
                for i, row in enumerate(sample_data, 1):
                    print(f"\n  Row {i}:")
                    for j, (col, value) in enumerate(zip(columns, row)):
                        col_name = col[0]
                        formatted_value = format_value(value, 50)
                        print(f"    {col_name}: {formatted_value}")
            else:
                print("📄 No data in this table.")
            
            print()
            
            # Show some statistics for tables with data
            if row_count > 0:
                print("📈 QUICK STATS:")
                try:
                    # Get some basic statistics
                    cursor.execute(f'SELECT COUNT(DISTINCT *) FROM "{table_name}";')
                    unique_rows = cursor.fetchone()[0]
                    print(f"  • Unique rows: {unique_rows:,}")
                    
                    # Show data types distribution
                    type_counts = {}
                    for col in columns:
                        data_type = col[1]
                        type_counts[data_type] = type_counts.get(data_type, 0) + 1
                    
                    print(f"  • Column types: {dict(type_counts)}")
                    
                except Exception as e:
                    print(f"  • Could not compute stats: {e}")
                
                print()
        
        print("=" * 80)
        print("✅ DATABASE EXPLORATION COMPLETE")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error during exploration: {e}")
    
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    explore_database()
