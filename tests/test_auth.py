"""
Test authentication endpoints and functionality.
"""

import pytest
from fastapi.testclient import TestClient


class TestAuthenticationEndpoints:
    """Test authentication-related endpoints."""

    def test_signup_success(self, client: TestClient, sample_user_data):
        """Test successful user registration."""
        response = client.post("/auth/signup", json=sample_user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == sample_user_data["username"]
        assert data["email"] == sample_user_data["email"]
        assert "id" in data
        assert "hashed_password" not in data  # Password should not be returned

    def test_signup_duplicate_username(self, client: TestClient, sample_user_data):
        """Test signup with duplicate username."""
        # Create first user
        client.post("/auth/signup", json=sample_user_data)
        
        # Try to create second user with same username
        response = client.post("/auth/signup", json=sample_user_data)
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_signup_duplicate_email(self, client: TestClient, sample_user_data):
        """Test signup with duplicate email."""
        # Create first user
        client.post("/auth/signup", json=sample_user_data)
        
        # Try to create second user with same email but different username
        duplicate_email_data = sample_user_data.copy()
        duplicate_email_data["username"] = "differentuser"
        response = client.post("/auth/signup", json=duplicate_email_data)
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_login_success(self, client: TestClient, sample_user_data):
        """Test successful login."""
        # First create user
        client.post("/auth/signup", json=sample_user_data)
        
        # Then login
        login_data = {
            "username": sample_user_data["username"],
            "password": sample_user_data["password"]
        }
        response = client.post("/auth/login", data=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, client: TestClient, sample_user_data):
        """Test login with invalid credentials."""
        # Create user
        client.post("/auth/signup", json=sample_user_data)
        
        # Try login with wrong password
        login_data = {
            "username": sample_user_data["username"],
            "password": "wrongpassword"
        }
        response = client.post("/auth/login", data=login_data)
        
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with non-existent user."""
        login_data = {
            "username": "nonexistent",
            "password": "password"
        }
        response = client.post("/auth/login", data=login_data)
        
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_get_current_user_authenticated(self, authenticated_client):
        """Test getting current user info when authenticated."""
        client, test_user = authenticated_client
        
        response = client.get("/auth/me")
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email
        assert "id" in data

    def test_get_current_user_unauthenticated(self, client: TestClient):
        """Test getting current user info when not authenticated."""
        response = client.get("/auth/me")
        
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    def test_invalid_token(self, client: TestClient):
        """Test API access with invalid token."""
        client.headers = {"Authorization": "Bearer invalid_token"}
        
        response = client.get("/auth/me")
        
        assert response.status_code == 401
