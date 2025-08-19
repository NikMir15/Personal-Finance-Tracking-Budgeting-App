"""
Database migration script to add multi-currency support.

This script adds:
1. currency field to expenses table
2. base_currency field to users table  
3. creates currency_rates table

Run this script before starting the updated application.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.database import Base, engine
from app.models import *  # Import all models to ensure they're registered

def migrate_database():
    """Add currency support to existing database."""
    
    print("Starting currency support migration...")
    
    try:
        with engine.connect() as conn:
            # Check if currency column exists in expenses table (MySQL syntax)
            result = conn.execute(text("""
                SELECT COUNT(*) as count 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE table_name = 'expenses' 
                AND column_name = 'currency'
                AND table_schema = DATABASE()
            """))
            
            if result.fetchone()[0] == 0:
                print("Adding currency column to expenses table...")
                conn.execute(text("ALTER TABLE expenses ADD COLUMN currency VARCHAR(3) DEFAULT 'USD'"))
                conn.commit()
                print("✓ Currency column added to expenses table")
            else:
                print("✓ Currency column already exists in expenses table")
            
            # Check if base_currency column exists in users table (MySQL syntax)
            result = conn.execute(text("""
                SELECT COUNT(*) as count 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE table_name = 'users' 
                AND column_name = 'base_currency'
                AND table_schema = DATABASE()
            """))
            
            if result.fetchone()[0] == 0:
                print("Adding base_currency column to users table...")
                conn.execute(text("ALTER TABLE users ADD COLUMN base_currency VARCHAR(3) DEFAULT 'USD'"))
                conn.commit()
                print("✓ Base currency column added to users table")
            else:
                print("✓ Base currency column already exists in users table")
                
        # Create all tables (including new currency_rates table)
        print("Creating/updating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✓ All tables created/updated successfully")
        
        print("\n🎉 Migration completed successfully!")
        print("\nNext steps:")
        print("1. Start the application: python run.py")
        print("2. The application will automatically fetch exchange rates on first use")
        print("3. Users can now select currencies when adding expenses")
        print("4. Dashboard will show amounts in user's base currency")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    migrate_database()
