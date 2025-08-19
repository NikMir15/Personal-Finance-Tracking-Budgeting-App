"""
Pytest configuration and fixtures for testing.
"""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.main import app
from app.database import Base, get_db
from app.dependencies.jwt_auth import get_current_user


# Test database configuration
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "expense_tracker_test")

# Create test database URL
encoded_password = quote_plus(MYSQL_PASSWORD)
TEST_DATABASE_URL = f"mysql://{MYSQL_USER}:{encoded_password}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"

# Create test engine
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def db_engine():
    """Create database engine for testing."""
    return engine


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a fresh database session for each test."""
    # Create tables
    Base.metadata.create_all(bind=db_engine)
    
    # Create session
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        # Clean up tables after each test
        Base.metadata.drop_all(bind=db_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database dependency override."""
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up dependency overrides
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def authenticated_client(client, db_session):
    """Create an authenticated test client with a test user."""
    from app.models.user import User
    from app.core.security import get_password_hash
    from app.dependencies.jwt_auth import create_access_token
    
    # Create test user
    test_user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpassword"),
        base_currency="USD"
    )
    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)
    
    # Create access token
    access_token = create_access_token(data={"sub": test_user.username})
    
    # Override the auth dependency
    def override_get_current_user():
        return test_user.username
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    # Set authorization header
    client.headers = {"Authorization": f"Bearer {access_token}"}
    
    yield client, test_user
    
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def sample_expense_data():
    """Sample expense data for testing."""
    return {
        "title": "Test Expense",
        "amount": 25.99,
        "currency": "USD",
        "date": "2024-01-15",
        "category": "Food"
    }


@pytest.fixture
def sample_budget_data():
    """Sample budget data for testing."""
    return {
        "category": "Food",
        "amount": 500.0,
        "currency": "USD",
        "period": "monthly"
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "username": "testuser2",
        "email": "test2@example.com",
        "password": "testpassword123",
        "base_currency": "USD"
    }
