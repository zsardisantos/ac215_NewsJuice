#!/usr/bin/env python3
"""
Test different connection methods to the database
"""

import psycopg2
import os
import socket

def test_port(host, port):
    """Test if a port is open"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def test_connection(host, port, user, password, database):
    """Test database connection"""
    try:
        conn_str = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        conn = psycopg2.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return True, version
    except Exception as e:
        return False, str(e)

def main():
    print("🔍 TESTING DATABASE CONNECTIONS")
    print("=" * 50)
    
    # Test port availability
    print("1. Testing port availability:")
    hosts_to_test = ['localhost', '127.0.0.1', '0.0.0.0']
    for host in hosts_to_test:
        if test_port(host, 5432):
            print(f"   ✓ {host}:5432 is open")
        else:
            print(f"   ✗ {host}:5432 is closed")
    
    print("\n2. Testing database connections:")
    
    # Test different connection parameters
    test_configs = [
        ("localhost", 5432, "postgres", "Newsjuice25+", "newsdb"),
        ("127.0.0.1", 5432, "postgres", "Newsjuice25+", "newsdb"),
        ("localhost", 5432, "postgres", "Newsjuice25%2B", "newsdb"),
    ]
    
    for host, port, user, password, database in test_configs:
        print(f"\n   Testing: {user}@{host}:{port}/{database}")
        success, result = test_connection(host, port, user, password, database)
        if success:
            print(f"   ✓ SUCCESS: {result}")
        else:
            print(f"   ✗ FAILED: {result}")
    
    print("\n3. Environment variables:")
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        print(f"   DATABASE_URL: {db_url}")
    else:
        print("   DATABASE_URL: Not set")
    
    print("\n4. Next steps:")
    print("   - If no ports are open, start Cloud SQL proxy:")
    print("     ./cloud-sql-proxy --credentials-file=./secrets/sa-key.json --port 5432 newsjuice-123456:us-central1:newsdb-instance")
    print("   - If you have direct access, set DATABASE_URL environment variable")
    print("   - Make sure you have the correct service account key file")

if __name__ == "__main__":
    main()
