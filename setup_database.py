#!/usr/bin/env python3
"""
Database setup script for MySQL
This script will create the database and tables for the expense tracker application.
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Load environment variables
load_dotenv()

# MySQL Configuration
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "expense_tracker")

def create_database():
    """Create the database if it doesn't exist"""
    try:
        # Connect to MySQL server (without specifying database)
        encoded_user = quote_plus(MYSQL_USER)
        encoded_password = quote_plus(MYSQL_PASSWORD)
        connection_string = f"mysql://{encoded_user}:{encoded_password}@{MYSQL_HOST}:{MYSQL_PORT}"
        engine = create_engine(connection_string)
        
        with engine.connect() as connection:
            # Create database if it doesn't exist
            connection.execute(text(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DATABASE}"))
            connection.commit()
            print(f"✅ Database '{MYSQL_DATABASE}' created successfully or already exists")
            
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        sys.exit(1)

def create_tables():
    """Create all tables in the database"""
    try:
        from app.database import engine, Base
        from app.models import user, expense, budget
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        sys.exit(1)

def main():
    print("🚀 Setting up MySQL database for Expense Tracker...")
    print(f"📊 Database: {MYSQL_DATABASE}")
    print(f"🔗 Host: {MYSQL_HOST}:{MYSQL_PORT}")
    print(f"👤 User: {MYSQL_USER}")
    print()
    
    # Create database
    create_database()
    
    # Create tables
    create_tables()
    
    print()
    print("🎉 Database setup completed successfully!")
    print("📝 You can now run the application with: python -m uvicorn app.main:app --reload")

if __name__ == "__main__":
    main() 