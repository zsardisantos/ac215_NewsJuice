#!/usr/bin/env python3
"""
Database Explorer Script for NewsJuice PostgreSQL Database

This script helps you explore your PostgreSQL database by:
1. Listing all tables
2. Showing table schemas and structure
3. Displaying sample data from each table
4. Providing useful database statistics

Usage:
    python3 database_explorer.py

Make sure to:
1. Start the Cloud SQL proxy first:
   cloud-sql-proxy --credentials-file=./secrets/sa-key.json --port 5432 newsjuice-123456:us-central1:newsdb-instance

2. Set the DATABASE_URL environment variable:
   export DATABASE_URL="postgresql://postgres:Newsjuice25%2B@localhost:5432/newsdb"
"""

import psycopg2
import os
import json
from datetime import datetime
import sys

def connect_to_database():
    """Connect to the PostgreSQL database"""
    try:
        # Get database URL from environment or use default
        database_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:Newsjuice25%2B@localhost:5432/newsdb')
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        print("\n💡 Make sure:")
        print("1. Cloud SQL proxy is running on port 5432")
        print("2. DATABASE_URL environment variable is set correctly")
        print("3. Database credentials are correct")
        return None

def list_tables(conn):
    """List all tables in the database"""
    print("=" * 60)
    print("📋 TABLES IN DATABASE")
    print("=" * 60)
    
    cur = conn.cursor()
    
    # Get all tables
    cur.execute("""
        SELECT table_name, table_type
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    
    tables = cur.fetchall()
    
    if not tables:
        print("No tables found in the database.")
        return []
    
    for i, (table_name, table_type) in enumerate(tables, 1):
        print(f"{i:2d}. {table_name} ({table_type})")
    
    print(f"\nTotal tables: {len(tables)}")
    return [table[0] for table in tables]

def show_table_schema(conn, table_name):
    """Show detailed schema for a specific table"""
    print(f"\n{'='*60}")
    print(f"🏗️  SCHEMA FOR TABLE: {table_name}")
    print(f"{'='*60}")
    
    cur = conn.cursor()
    
    # Get column information
    cur.execute("""
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length
        FROM information_schema.columns 
        WHERE table_name = %s AND table_schema = 'public'
        ORDER BY ordinal_position;
    """, (table_name,))
    
    columns = cur.fetchall()
    
    if not columns:
        print(f"Table '{table_name}' not found or has no columns.")
        return
    
    print(f"{'Column Name':<25} {'Type':<20} {'Nullable':<10} {'Default':<15} {'Max Length'}")
    print("-" * 80)
    
    for col_name, data_type, is_nullable, default, max_length in columns:
        nullable = "YES" if is_nullable == "YES" else "NO"
        default_str = str(default)[:14] if default else ""
        max_len = str(max_length) if max_length else ""
        print(f"{col_name:<25} {data_type:<20} {nullable:<10} {default_str:<15} {max_len}")
    
    # Get primary key information
    cur.execute("""
        SELECT column_name
        FROM information_schema.key_column_usage
        WHERE table_name = %s AND table_schema = 'public'
        AND constraint_name IN (
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = %s AND table_schema = 'public'
            AND constraint_type = 'PRIMARY KEY'
        );
    """, (table_name, table_name))
    
    pk_columns = cur.fetchall()
    if pk_columns:
        pk_names = [col[0] for col in pk_columns]
        print(f"\n🔑 Primary Key: {', '.join(pk_names)}")
    
    # Get foreign key information
    cur.execute("""
        SELECT 
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.key_column_usage AS kcu
        JOIN information_schema.referential_constraints AS rcs
            ON kcu.constraint_name = rcs.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = rcs.constraint_name
        WHERE kcu.table_name = %s AND kcu.table_schema = 'public';
    """, (table_name,))
    
    fk_columns = cur.fetchall()
    if fk_columns:
        print(f"\n🔗 Foreign Keys:")
        for col_name, foreign_table, foreign_column in fk_columns:
            print(f"   {col_name} -> {foreign_table}.{foreign_column}")

def show_table_data(conn, table_name, limit=5):
    """Show sample data from a table"""
    print(f"\n{'='*60}")
    print(f"📊 SAMPLE DATA FROM TABLE: {table_name}")
    print(f"{'='*60}")
    
    cur = conn.cursor()
    
    # Get row count
    cur.execute(f"SELECT COUNT(*) FROM {table_name};")
    row_count = cur.fetchone()[0]
    print(f"Total rows: {row_count}")
    
    if row_count == 0:
        print("Table is empty.")
        return
    
    # Get sample data
    cur.execute(f"SELECT * FROM {table_name} LIMIT {limit};")
    rows = cur.fetchall()
    
    # Get column names
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns 
        WHERE table_name = %s AND table_schema = 'public'
        ORDER BY ordinal_position;
    """, (table_name,))
    
    column_names = [col[0] for col in cur.fetchall()]
    
    if not rows:
        print("No data to display.")
        return
    
    # Display data in a formatted table
    print(f"\nShowing first {min(limit, len(rows))} rows:")
    print("-" * 80)
    
    for i, row in enumerate(rows, 1):
        print(f"Row {i}:")
        for j, (col_name, value) in enumerate(zip(column_names, row)):
            # Truncate long values for display
            display_value = str(value)
            if len(display_value) > 50:
                display_value = display_value[:47] + "..."
            print(f"  {col_name}: {display_value}")
        print()

def show_database_stats(conn):
    """Show database statistics"""
    print(f"\n{'='*60}")
    print("📈 DATABASE STATISTICS")
    print(f"{'='*60}")
    
    cur = conn.cursor()
    
    # Get table sizes
    cur.execute("""
        SELECT 
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
        FROM pg_tables 
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
    """)
    
    table_sizes = cur.fetchall()
    
    if table_sizes:
        print("Table sizes:")
        for schema, table, size in table_sizes:
            print(f"  {table}: {size}")
    
    # Get total database size
    cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()));")
    db_size = cur.fetchone()[0]
    print(f"\nTotal database size: {db_size}")

def main():
    """Main function to explore the database"""
    print("🔍 NewsJuice Database Explorer")
    print("=" * 60)
    
    # Connect to database
    conn = connect_to_database()
    if not conn:
        sys.exit(1)
    
    try:
        # List all tables
        tables = list_tables(conn)
        
        if not tables:
            print("No tables found in the database.")
            return
        
        # Show schema and data for each table
        for table_name in tables:
            show_table_schema(conn, table_name)
            show_table_data(conn, table_name)
        
        # Show database statistics
        show_database_stats(conn)
        
        print(f"\n{'='*60}")
        print("✅ Database exploration complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error during database exploration: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()