#!/usr/bin/env python3
"""
Simple Database Viewer - Run this in your terminal where the proxy is running
"""

import psycopg2
import sys

def main():
    # Connection parameters
    conn_params = {
        'host': 'localhost',
        'port': 5432,
        'database': 'newsdb',
        'user': 'postgres',
        'password': 'Newsjuice25+'
    }
    
    try:
        print("🔌 Connecting to database...")
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        print("✅ Connected successfully!")
        print("\n" + "="*60)
        print("📋 DATABASE TABLES")
        print("="*60)
        
        # Get list of tables
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
        
        print(f"Found {len(tables)} table(s):\n")
        
        for i, (table_name, table_type) in enumerate(tables, 1):
            print(f"{i}. {table_name} ({table_type})")
        
        print("\n" + "="*60)
        print("📊 TABLE DETAILS")
        print("="*60)
        
        # Get details for each table
        for table_name, table_type in tables:
            print(f"\n🏷️  TABLE: {table_name.upper()}")
            print("-" * 40)
            
            # Get column information
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = %s
                ORDER BY ordinal_position;
            """, (table_name,))
            
            columns = cursor.fetchall()
            print("Columns:")
            for col in columns:
                col_name, data_type, nullable, default = col
                nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
                default_str = f" DEFAULT {default}" if default else ""
                print(f"  • {col_name}: {data_type} {nullable_str}{default_str}")
            
            # Get row count
            cursor.execute(f'SELECT COUNT(*) FROM "{table_name}";')
            count = cursor.fetchone()[0]
            print(f"\nRow count: {count:,}")
            
            # Show sample data (first 3 rows)
            if count > 0:
                print("\nSample data (first 3 rows):")
                cursor.execute(f'SELECT * FROM "{table_name}" LIMIT 3;')
                sample_data = cursor.fetchall()
                
                for i, row in enumerate(sample_data, 1):
                    print(f"\n  Row {i}:")
                    for j, (col, value) in enumerate(zip(columns, row)):
                        col_name = col[0]
                        value_str = str(value) if value is not None else "NULL"
                        if len(value_str) > 50:
                            value_str = value_str[:50] + "..."
                        print(f"    {col_name}: {value_str}")
            else:
                print("\nNo data in this table.")
            
            print()
        
        print("="*60)
        print("✅ Database exploration complete!")
        print("="*60)
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure Cloud SQL proxy is running")
        print("2. Check if port 5432 is accessible")
        print("3. Verify database credentials")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        if 'conn' in locals():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    main()
