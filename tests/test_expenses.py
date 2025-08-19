"""
Test expense management endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestExpenseEndpoints:
    """Test expense-related endpoints."""

    def test_create_expense_success(self, authenticated_client, sample_expense_data):
        """Test successful expense creation."""
        client, test_user = authenticated_client
        
        response = client.post("/expenses/", json=sample_expense_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == sample_expense_data["title"]
        assert data["amount"] == sample_expense_data["amount"]
        assert data["category"] == sample_expense_data["category"]
        assert data["user_id"] == test_user.id
        assert "id" in data

    def test_create_expense_unauthenticated(self, client: TestClient, sample_expense_data):
        """Test expense creation without authentication."""
        response = client.post("/expenses/", json=sample_expense_data)
        
        assert response.status_code == 401

    def test_create_expense_invalid_data(self, authenticated_client):
        """Test expense creation with invalid data."""
        client, _ = authenticated_client
        
        invalid_data = {
            "title": "",  # Empty title
            "amount": -10,  # Negative amount
            "category": "Food"
        }
        
        response = client.post("/expenses/", json=invalid_data)
        
        assert response.status_code == 422  # Validation error

    def test_get_user_expenses(self, authenticated_client, sample_expense_data):
        """Test retrieving user expenses."""
        client, test_user = authenticated_client
        
        # Create some expenses
        client.post("/expenses/", json=sample_expense_data)
        
        expense_2 = sample_expense_data.copy()
        expense_2["title"] = "Second Expense"
        expense_2["amount"] = 50.0
        client.post("/expenses/", json=expense_2)
        
        # Get expenses
        response = client.get("/expenses/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(expense["user_id"] == test_user.id for expense in data)

    def test_get_expenses_unauthenticated(self, client: TestClient):
        """Test getting expenses without authentication."""
        response = client.get("/expenses/")
        
        assert response.status_code == 401

    def test_get_expenses_with_filters(self, authenticated_client, sample_expense_data):
        """Test getting expenses with category filter."""
        client, test_user = authenticated_client
        
        # Create expenses in different categories
        food_expense = sample_expense_data.copy()
        food_expense["category"] = "Food"
        client.post("/expenses/", json=food_expense)
        
        transport_expense = sample_expense_data.copy()
        transport_expense["category"] = "Transport"
        transport_expense["title"] = "Gas"
        client.post("/expenses/", json=transport_expense)
        
        # Filter by category
        response = client.get("/expenses/?category=Food")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["category"] == "Food"

    def test_get_expense_by_id(self, authenticated_client, sample_expense_data):
        """Test getting a specific expense by ID."""
        client, test_user = authenticated_client
        
        # Create expense
        create_response = client.post("/expenses/", json=sample_expense_data)
        expense_id = create_response.json()["id"]
        
        # Get specific expense
        response = client.get(f"/expenses/{expense_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == expense_id
        assert data["title"] == sample_expense_data["title"]

    def test_get_nonexistent_expense(self, authenticated_client):
        """Test getting an expense that doesn't exist."""
        client, _ = authenticated_client
        
        response = client.get("/expenses/999999")
        
        assert response.status_code == 404

    def test_update_expense(self, authenticated_client, sample_expense_data):
        """Test updating an expense."""
        client, test_user = authenticated_client
        
        # Create expense
        create_response = client.post("/expenses/", json=sample_expense_data)
        expense_id = create_response.json()["id"]
        
        # Update expense
        update_data = {
            "title": "Updated Expense",
            "amount": 35.99,
            "currency": "USD",
            "date": "2024-01-16",
            "category": "Shopping"
        }
        
        response = client.put(f"/expenses/{expense_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["amount"] == update_data["amount"]
        assert data["category"] == update_data["category"]

    def test_delete_expense(self, authenticated_client, sample_expense_data):
        """Test deleting an expense."""
        client, test_user = authenticated_client
        
        # Create expense
        create_response = client.post("/expenses/", json=sample_expense_data)
        expense_id = create_response.json()["id"]
        
        # Delete expense
        response = client.delete(f"/expenses/{expense_id}")
        
        assert response.status_code == 200
        
        # Verify expense is deleted
        get_response = client.get(f"/expenses/{expense_id}")
        assert get_response.status_code == 404

    def test_delete_nonexistent_expense(self, authenticated_client):
        """Test deleting an expense that doesn't exist."""
        client, _ = authenticated_client
        
        response = client.delete("/expenses/999999")
        
        assert response.status_code == 404
