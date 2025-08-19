"""
Test script to verify router polish improvements:
- Response models on all endpoints
- Standardized error responses
- Authentication enforcement
- Pagination on list endpoints
- Server-side validation
- OpenAPI documentation
"""

import requests
import json
from datetime import date, timedelta

BASE_URL = "http://localhost:8000"

def test_auth_endpoints():
    """Test authentication endpoints with proper validation."""
    print("Testing Auth Endpoints...")
    
    # Test registration with validation
    register_data = {
        "username": "testuser",
        "password": "testpass123",
        "email": "test@example.com"
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    print(f"Register response: {response.status_code}")
    if response.status_code == 201:
        token_data = response.json()
        print(f"Token received: {token_data['access_token'][:20]}...")
        return token_data['access_token']
    else:
        print(f"Register failed: {response.json()}")
        return None

def test_expense_validation(token):
    """Test expense creation with validation."""
    print("\nTesting Expense Validation...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test valid expense
    valid_expense = {
        "title": "Test Expense",
        "amount": 50.0,
        "date": str(date.today()),
        "category": "Food"
    }
    
    response = requests.post(f"{BASE_URL}/expenses/", json=valid_expense, headers=headers)
    print(f"Valid expense response: {response.status_code}")
    
    # Test invalid amount
    invalid_amount = {
        "title": "Test Expense",
        "amount": -10.0,  # Negative amount
        "date": str(date.today()),
        "category": "Food"
    }
    
    response = requests.post(f"{BASE_URL}/expenses/", json=invalid_amount, headers=headers)
    print(f"Invalid amount response: {response.status_code}")
    if response.status_code == 422:
        print("✓ Amount validation working")
    
    # Test future date
    future_date = {
        "title": "Test Expense",
        "amount": 50.0,
        "date": str(date.today() + timedelta(days=1)),  # Future date
        "category": "Food"
    }
    
    response = requests.post(f"{BASE_URL}/expenses/", json=future_date, headers=headers)
    print(f"Future date response: {response.status_code}")
    if response.status_code == 422:
        print("✓ Date validation working")

def test_pagination(token):
    """Test pagination on list endpoints."""
    print("\nTesting Pagination...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test expenses pagination
    response = requests.get(f"{BASE_URL}/expenses/?skip=0&limit=5", headers=headers)
    print(f"Expenses pagination response: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Pagination working: {data['total']} total, {len(data['items'])} items")
    
    # Test budgets pagination
    response = requests.get(f"{BASE_URL}/budgets/?skip=0&limit=5", headers=headers)
    print(f"Budgets pagination response: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Pagination working: {data['total']} total, {len(data['items'])} items")

def test_authentication():
    """Test authentication enforcement."""
    print("\nTesting Authentication...")
    
    # Test protected endpoint without token
    response = requests.get(f"{BASE_URL}/expenses/")
    print(f"Unauthenticated expenses response: {response.status_code}")
    if response.status_code == 401:
        print("✓ Authentication enforcement working")
    
    # Test protected endpoint with invalid token
    headers = {"Authorization": "Bearer invalid_token"}
    response = requests.get(f"{BASE_URL}/expenses/", headers=headers)
    print(f"Invalid token response: {response.status_code}")
    if response.status_code == 401:
        print("✓ Invalid token handling working")

def test_error_standardization():
    """Test standardized error responses."""
    print("\nTesting Error Standardization...")
    
    # Test 404 error
    response = requests.get(f"{BASE_URL}/nonexistent/")
    print(f"404 response: {response.status_code}")
    if response.status_code == 404:
        error_data = response.json()
        if "code" in error_data and "message" in error_data:
            print("✓ Standardized error format working")

def test_openapi_docs():
    """Test OpenAPI documentation."""
    print("\nTesting OpenAPI Documentation...")
    
    response = requests.get(f"{BASE_URL}/openapi.json")
    print(f"OpenAPI schema response: {response.status_code}")
    if response.status_code == 200:
        schema = response.json()
        print(f"✓ OpenAPI schema available with {len(schema['paths'])} endpoints")
        
        # Check for proper documentation
        if "info" in schema and "title" in schema["info"]:
            print(f"✓ API title: {schema['info']['title']}")
        
        # Check for response models
        auth_paths = [path for path in schema["paths"] if path.startswith("/auth")]
        if auth_paths:
            print(f"✓ Auth endpoints documented: {len(auth_paths)} endpoints")

def main():
    """Run all tests."""
    print("Starting Router Polish Tests...")
    print("=" * 50)
    
    # Test authentication
    test_authentication()
    
    # Test auth endpoints
    token = test_auth_endpoints()
    
    if token:
        # Test validation
        test_expense_validation(token)
        
        # Test pagination
        test_pagination(token)
    
    # Test error standardization
    test_error_standardization()
    
    # Test OpenAPI docs
    test_openapi_docs()
    
    print("\n" + "=" * 50)
    print("Router Polish Tests Complete!")

if __name__ == "__main__":
    main() 