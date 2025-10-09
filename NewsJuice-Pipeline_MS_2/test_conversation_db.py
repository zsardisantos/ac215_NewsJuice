#!/usr/bin/env python3
"""
Test script to verify the LLM conversation database setup works correctly
"""

import os
import sys
from conversation_helpers import ConversationManager

def test_conversation_database():
    """Test all conversation database functionality"""
    
    print("🧪 Testing LLM Conversation Database")
    print("=" * 50)
    
    try:
        # Initialize conversation manager
        manager = ConversationManager()
        print("✅ ConversationManager initialized successfully")
        
        # Test data
        test_user_id = "test_user_123"
        test_model = "gpt-4"
        test_conversation = [
            {"role": "user", "content": "Hello! Can you help me with Python?", "token_count": 8},
            {"role": "assistant", "content": "Of course! I'd be happy to help you with Python. What specific topic would you like to learn about?", "token_count": 20},
            {"role": "user", "content": "How do I create a list comprehension?", "token_count": 7},
            {"role": "assistant", "content": "List comprehensions are a concise way to create lists in Python. The basic syntax is: [expression for item in iterable if condition]. For example: [x**2 for x in range(10) if x % 2 == 0]", "token_count": 35}
        ]
        
        print("\n📝 Testing conversation save...")
        conv_id = manager.save_conversation(test_user_id, test_model, test_conversation)
        print(f"✅ Conversation saved with ID: {conv_id}")
        
        print("\n🔍 Testing conversation retrieval...")
        retrieved_conv = manager.get_conversation_by_id(conv_id)
        if retrieved_conv:
            print("✅ Conversation retrieved successfully")
            print(f"   User ID: {retrieved_conv['user_id']}")
            print(f"   Model: {retrieved_conv['model_name']}")
            print(f"   Messages: {len(retrieved_conv['conversation_data'])}")
        else:
            print("❌ Failed to retrieve conversation")
            return False
        
        print("\n👤 Testing user conversations...")
        user_convs = manager.get_user_conversations(test_user_id, limit=5)
        print(f"✅ Found {len(user_convs)} conversations for user {test_user_id}")
        
        print("\n🤖 Testing model conversations...")
        model_convs = manager.get_conversations_by_model(test_model, limit=5)
        print(f"✅ Found {len(model_convs)} conversations for model {test_model}")
        
        print("\n🔍 Testing conversation search...")
        search_results = manager.search_conversations("Python", limit=5)
        print(f"✅ Found {len(search_results)} conversations containing 'Python'")
        
        print("\n📊 Testing conversation statistics...")
        stats = manager.get_conversation_stats()
        print("✅ Conversation statistics:")
        print(f"   Total conversations: {stats['total_conversations']}")
        print(f"   By model: {stats['by_model']}")
        print(f"   Avg messages per conversation: {stats['avg_messages_per_conversation']}")
        print(f"   Recent conversations (24h): {stats['recent_conversations_24h']}")
        
        print("\n✏️  Testing conversation update...")
        updated_conversation = test_conversation + [
            {"role": "user", "content": "Thanks for the help!", "token_count": 4},
            {"role": "assistant", "content": "You're welcome! Feel free to ask if you have more questions.", "token_count": 12}
        ]
        
        update_success = manager.update_conversation(conv_id, updated_conversation)
        if update_success:
            print("✅ Conversation updated successfully")
            
            # Verify update
            updated_conv = manager.get_conversation_by_id(conv_id)
            if updated_conv and len(updated_conv['conversation_data']) == len(updated_conversation):
                print("✅ Update verification successful")
            else:
                print("❌ Update verification failed")
                return False
        else:
            print("❌ Failed to update conversation")
            return False
        
        print("\n🗑️  Testing conversation deletion...")
        delete_success = manager.delete_conversation(conv_id)
        if delete_success:
            print("✅ Conversation deleted successfully")
            
            # Verify deletion
            deleted_conv = manager.get_conversation_by_id(conv_id)
            if deleted_conv is None:
                print("✅ Deletion verification successful")
            else:
                print("❌ Deletion verification failed")
                return False
        else:
            print("❌ Failed to delete conversation")
            return False
        
        print("\n🎉 All tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_connection():
    """Test basic database connection"""
    print("🔌 Testing database connection...")
    
    try:
        manager = ConversationManager()
        stats = manager.get_conversation_stats()
        print("✅ Database connection successful")
        print(f"   Current total conversations: {stats['total_conversations']}")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 LLM Conversation Database Test Suite")
    print("=" * 60)
    
    # Check if DATABASE_URL is set
    if not os.environ.get("DATABASE_URL"):
        print("❌ DATABASE_URL environment variable not set!")
        print("Please set it to: postgresql://postgres:Newsjuice25%2B@localhost:5432/newsdb")
        sys.exit(1)
    
    # Test database connection first
    if not test_database_connection():
        print("\n💡 Make sure:")
        print("   1. Cloud SQL Proxy is running")
        print("   2. DATABASE_URL is set correctly")
        print("   3. Database tables exist (run add_new_table.py first)")
        sys.exit(1)
    
    # Run full test suite
    success = test_conversation_database()
    
    if success:
        print("\n🎊 Database setup is working perfectly!")
        print("\nYou can now use the ConversationManager in your applications.")
    else:
        print("\n💥 Some tests failed. Please check the error messages above.")
        sys.exit(1)