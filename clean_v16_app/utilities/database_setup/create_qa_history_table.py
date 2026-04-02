#!/usr/bin/env python3
"""
Create Q&A History Table for Document Question Answering System
This table stores conversation history for each company's document Q&A sessions.
"""

import sqlite3
import os
from datetime import datetime

def create_qa_history_table():
    """Create the qa_history table in the main credit risk database."""
    
    # Database path
    db_path = '/Users/kaunteyshah/Databricks/Credit_Risk/clean_modular_app/data/credit_risk.db'
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return False
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Create qa_history table
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS qa_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                company_number TEXT,
                company_name TEXT,
                document_id TEXT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                confidence_score REAL DEFAULT 0.0,
                sources_count INTEGER DEFAULT 0,
                response_time_ms INTEGER DEFAULT 0,
                session_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Foreign key constraint
                FOREIGN KEY (company_id) REFERENCES companies(id)
            );
            """
            
            cursor.execute(create_table_sql)
            
            # Create indexes for better performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_qa_history_company_id ON qa_history(company_id);",
                "CREATE INDEX IF NOT EXISTS idx_qa_history_company_number ON qa_history(company_number);",
                "CREATE INDEX IF NOT EXISTS idx_qa_history_document_id ON qa_history(document_id);",
                "CREATE INDEX IF NOT EXISTS idx_qa_history_session_id ON qa_history(session_id);",
                "CREATE INDEX IF NOT EXISTS idx_qa_history_created_at ON qa_history(created_at);"
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
            
            conn.commit()
            
            # Verify table creation
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='qa_history';")
            table_exists = cursor.fetchone()
            
            if table_exists:
                print("✅ qa_history table created successfully")
                
                # Show table schema
                cursor.execute("PRAGMA table_info(qa_history);")
                columns = cursor.fetchall()
                print("\n📋 Table Schema:")
                for col in columns:
                    print(f"  - {col[1]} ({col[2]})")
                
                return True
            else:
                print("❌ Failed to create qa_history table")
                return False
                
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_qa_history_table():
    """Test the qa_history table with sample data."""
    
    db_path = '/Users/kaunteyshah/Databricks/Credit_Risk/clean_modular_app/data/credit_risk.db'
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Insert test record
            test_data = (
                1,  # company_id
                "03236483",  # company_number
                "IMPERIAL BRANDS PLC",  # company_name
                "caxBmF0n41YnfoZ_vvTE4KdaNPY-4GUUI8J-VPPipPs",  # document_id
                "What is the company's revenue?",  # question
                "Imperial Brands reported revenue of £7.6 billion for the latest reporting period.",  # answer
                0.87,  # confidence_score
                3,  # sources_count
                1250,  # response_time_ms
                "session_123"  # session_id
            )
            
            insert_sql = """
            INSERT INTO qa_history (
                company_id, company_number, company_name, document_id,
                question, answer, confidence_score, sources_count,
                response_time_ms, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            cursor.execute(insert_sql, test_data)
            
            # Retrieve and display test record
            cursor.execute("SELECT * FROM qa_history ORDER BY id DESC LIMIT 1")
            record = cursor.fetchone()
            
            if record:
                print("✅ Test record inserted successfully")
                print(f"📄 Record ID: {record[0]}")
                print(f"🏢 Company: {record[3]} ({record[2]})")
                print(f"❓ Question: {record[5]}")
                print(f"💬 Answer: {record[6][:100]}...")
                print(f"📊 Confidence: {record[7]:.1%}")
                
                # Clean up test record
                cursor.execute("DELETE FROM qa_history WHERE id = ?", (record[0],))
                print("🧹 Test record cleaned up")
                
                return True
            else:
                print("❌ Failed to retrieve test record")
                return False
                
    except sqlite3.Error as e:
        print(f"❌ Database error during test: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Creating Q&A History Table")
    print("=" * 40)
    
    success = create_qa_history_table()
    
    if success:
        print("\n🧪 Testing Q&A History Table")
        print("=" * 30)
        test_success = test_qa_history_table()
        
        if test_success:
            print("\n🎉 Q&A History Table Setup Complete!")
            print("✅ Ready for document Q&A conversations")
        else:
            print("\n⚠️ Table created but test failed")
    else:
        print("\n❌ Failed to create Q&A History Table")