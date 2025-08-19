import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Load environment variables
load_dotenv()

# MySQL Database Configuration
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "expense_tracker")

# URL encode the password to handle special characters
encoded_password = quote_plus(MYSQL_PASSWORD)

# Construct MySQL URL with proper encoding
DATABASE_URL = f"mysql://{MYSQL_USER}:{encoded_password}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"

# Create engine with optimized connection pool settings
engine = create_engine(
    DATABASE_URL,
    # Connection pool settings for performance and reliability
    pool_size=10,              # Number of connections to maintain in the pool
    max_overflow=20,           # Maximum overflow connections beyond pool_size
    pool_timeout=30,           # Timeout in seconds to get connection from pool
    pool_recycle=3600,         # Recycle connections every hour (3600 seconds)
    pool_pre_ping=True,        # Validate connections before use
    
    # MySQL-specific settings
    connect_args={
        "charset": "utf8mb4",
        "connect_timeout": 10,  # Connection timeout in seconds
        "read_timeout": 30,     # Read timeout in seconds
        "write_timeout": 30,    # Write timeout in seconds
    },
    
    # Logging and debugging
    echo=False,  # Set to True for SQL query logging in development
    echo_pool=False,  # Set to True for connection pool logging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 