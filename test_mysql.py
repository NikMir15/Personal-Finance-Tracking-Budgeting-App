#!/usr/bin/env python3
"""
MySQL Connection Test Script
This script tests the MySQL connection using your .env configuration
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

# Load environment variables
load_dotenv()

# MySQL Configuration
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "expense_tracker")

def test_connection():
    """Test MySQL connection"""
    print("🔍 Testing MySQL Connection...")
    print(f"Host: {MYSQL_HOST}")
    print(f"Port: {MYSQL_PORT}")
    print(f"User: {MYSQL_USER}")
    print(f"Database: {MYSQL_DATABASE}")
    print(f"Password: {'*' * len(MYSQL_PASSWORD) if MYSQL_PASSWORD else 'None'}")
    print()
    
    try:
        # URL encode the password to handle special characters
        encoded_password = quote_plus(MYSQL_PASSWORD)
        
        # Test connection to MySQL server (without database)
        connection_string = f"mysql://{MYSQL_USER}:{encoded_password}@{MYSQL_HOST}:{MYSQL_PORT}"
        engine = create_engine(connection_string)
        
        with engine.connect() as connection:
            # Test basic connection
            result = connection.execute(text("SELECT VERSION()"))
            version = result.fetchone()[0]
            print(f"✅ Successfully connected to MySQL!")
            print(f"📊 MySQL Version: {version}")
            
            # Test database creation
            connection.execute(text(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DATABASE}"))
            connection.commit()
            print(f"✅ Database '{MYSQL_DATABASE}' is ready")
            
            return True
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print()
        print("🔧 Troubleshooting tips:")
        print("1. Make sure MySQL is running")
        print("2. Check your .env file has correct password")
        print("3. Verify MySQL user permissions")
        print("4. Try connecting with MySQL command line client first")
        return False

def main():
    print("🎯 MySQL Connection Test")
    print("=" * 40)
    
    if not test_connection():
        sys.exit(1)
    
    print()
    print("🎉 MySQL connection test passed!")
    print("📝 You can now run the application")

if __name__ == "__main__":
    main() 