#!/usr/bin/env python3
"""
Quick start script for the Expense Tracker application
This script checks prerequisites and starts the application
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")

def check_virtual_environment():
    """Check if virtual environment is activated"""
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Virtual environment not detected")
        print("💡 Please activate your virtual environment first:")
        print("   Windows: venv\\Scripts\\activate")
        print("   macOS/Linux: source venv/bin/activate")
        return False
    print("✅ Virtual environment detected")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
        import mysqlclient
        import python_multipart
        print("✅ All required dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("💡 Please install dependencies: pip install -r requirements.txt")
        return False

def check_env_file():
    """Check if .env file exists"""
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  .env file not found")
        print("💡 Please create a .env file with your MySQL configuration")
        print("   Example:")
        print("   MYSQL_HOST=localhost")
        print("   MYSQL_PORT=3306")
        print("   MYSQL_USER=root")
        print("   MYSQL_PASSWORD=your_password")
        print("   MYSQL_DATABASE=expense_tracker")
        return False
    print("✅ .env file found")
    return True

def setup_database():
    """Run database setup"""
    try:
        print("🔧 Setting up database...")
        subprocess.run([sys.executable, "setup_database.py"], check=True)
        print("✅ Database setup completed")
        return True
    except subprocess.CalledProcessError:
        print("❌ Database setup failed")
        return False

def start_application():
    """Start the FastAPI application"""
    try:
        print("🚀 Starting Expense Tracker application...")
        print("📱 Application will be available at: http://localhost:8000")
        print("📚 API Documentation: http://localhost:8000/docs")
        print("⏹️  Press Ctrl+C to stop the application")
        print()
        
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--reload", 
            "--host", "0.0.0.0", 
            "--port", "8000"
        ])
    except KeyboardInterrupt:
        print("\n👋 Application stopped")
    except Exception as e:
        print(f"❌ Error starting application: {e}")

def main():
    print("🎯 Expense Tracker - Quick Start")
    print("=" * 40)
    
    # Check prerequisites
    check_python_version()
    
    if not check_virtual_environment():
        return
    
    if not check_dependencies():
        return
    
    if not check_env_file():
        return
    
    # Setup database
    if not setup_database():
        return
    
    print("\n" + "=" * 40)
    
    # Start application
    start_application()

if __name__ == "__main__":
    main() 