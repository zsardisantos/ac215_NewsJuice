#!/usr/bin/env python3
"""
Script to create LLM conversation tables in the NewsJuice PostgreSQL database
"""

import os
import psycopg
from pgvector.psycopg import register_vector
from datetime import datetime

def create_conversation_tables():
    """Create the llm_conversations and llm_messages tables"""
    
    # Get database URL from environment
    DB_URL = os.environ.get("DATABASE_URL")
    if not DB_URL:
        print("❌ DATABASE_URL environment variable not set!")
        print("Please set it to: postgresql://postgres:Newsjuice25%2B@localhost:5432/newsdb")
        return False
    
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
                
                # Check if tables already exist
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('llm_conversations', 'llm_messages');
                """)
                existing_tables = [row[0] for row in cur.fetchall()]
                
                if 'llm_conversations' in existing_tables:
                    print("⚠️  llm_conversations table already exists!")
                    response = input("Do you want to drop and recreate it? (y/N): ")
                    if response.lower() == 'y':
                        cur.execute("DROP TABLE IF EXISTS llm_messages CASCADE;")
                        cur.execute("DROP TABLE IF EXISTS llm_conversations CASCADE;")
                        print("🗑️  Dropped existing tables")
                    else:
                        print("✅ Keeping existing llm_conversations table")
                        return True
                
                # Create llm_conversations table
                print("📝 Creating llm_conversations table...")
                cur.execute("""
                    CREATE TABLE llm_conversations (
                        id SERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        model_name TEXT NOT NULL,
                        conversation_data JSONB NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # Create llm_messages table (optional - for individual message tracking)
                print("📝 Creating llm_messages table...")
                cur.execute("""
                    CREATE TABLE llm_messages (
                        id SERIAL PRIMARY KEY,
                        conversation_id INTEGER REFERENCES llm_conversations(id) ON DELETE CASCADE,
                        role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
                        content TEXT NOT NULL,
                        token_count INTEGER,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # Create indexes for better performance
                print("🔍 Creating indexes...")
                cur.execute("CREATE INDEX idx_llm_conversations_user_id ON llm_conversations(user_id);")
                cur.execute("CREATE INDEX idx_llm_conversations_model_name ON llm_conversations(model_name);")
                cur.execute("CREATE INDEX idx_llm_conversations_created_at ON llm_conversations(created_at);")
                cur.execute("CREATE INDEX idx_llm_conversations_data_gin ON llm_conversations USING GIN (conversation_data);")
                cur.execute("CREATE INDEX idx_llm_messages_conversation_id ON llm_messages(conversation_id);")
                cur.execute("CREATE INDEX idx_llm_messages_role ON llm_messages(role);")
                
                # Create trigger to update updated_at timestamp
                cur.execute("""
                    CREATE OR REPLACE FUNCTION update_updated_at_column()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.updated_at = CURRENT_TIMESTAMP;
                        RETURN NEW;
                    END;
                    $$ language 'plpgsql';
                """)
                
                cur.execute("""
                    CREATE TRIGGER update_llm_conversations_updated_at 
                    BEFORE UPDATE ON llm_conversations 
                    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
                """)
                
                print("✅ Successfully created LLM conversation tables!")
                print()
                print("📋 Tables created:")
                print("  • llm_conversations - Main conversation storage")
                print("  • llm_messages - Individual message tracking (optional)")
                print()
                print("🔍 Indexes created for optimal performance")
                print("⚡ Trigger created for automatic updated_at timestamps")
                
                return True
                
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Creating LLM Conversation Database Tables")
    print("=" * 50)
    
    success = create_conversation_tables()
    
    if success:
        print("\n🎉 Setup complete! You can now use the conversation database.")
        print("\nNext steps:")
        print("1. Run: python3 test_conversation_db.py")
        print("2. Use conversation_helpers.py in your applications")
    else:
        print("\n❌ Setup failed. Please check the error messages above.")