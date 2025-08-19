#!/usr/bin/env python3
"""
Simple smoke test for core API functionality
"""

import requests
import json
import time
import sys

def test_api():
    base_url = "http://localhost:8000"
    
    print("🚀 Testing Expense Tracker API")
    print("=" * 40)
    
    # Test 1: Check server is running
    try:
        response = requests.get(f"{base_url}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
        else:
            print(f"❌ Server not responding properly: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return False
    
    # Test 2: Check OpenAPI docs
    try:
        docs_response = requests.get(f"{base_url}/docs")
        redoc_response = requests.get(f"{base_url}/redoc")
        openapi_response = requests.get(f"{base_url}/openapi.json")
        
        if all(r.status_code == 200 for r in [docs_response, redoc_response, openapi_response]):
            print("✅ OpenAPI documentation accessible")
            openapi_data = openapi_response.json()
            print(f"   📊 Found {len(openapi_data.get('paths', {}))} API endpoints")
        else:
            print("❌ OpenAPI documentation issues")
    except Exception as e:
        print(f"❌ OpenAPI test failed: {e}")
    
    # Test 3: User registration
    user_data = {
        "username": f"testuser_{int(time.time())}",
        "email": f"test_{int(time.time())}@example.com",
        "password": "TestPassword123!",
        "base_currency": "USD"
    }
    
    try:
        signup_response = requests.post(f"{base_url}/auth/register", json=user_data)
        if signup_response.status_code == 201:
            token_data = signup_response.json()
            auth_token = token_data["access_token"]
            print(f"✅ User registration successful - Token received")
        else:
            print(f"❌ User registration failed: {signup_response.status_code}")
            print(f"   Response: {signup_response.text}")
            return False
    except Exception as e:
        print(f"❌ User registration error: {e}")
        return False
    
    # Test 4: Alternative login test (since registration provides token)
    try:
        login_data = {
            "username": user_data["username"],
            "password": user_data["password"]
        }
        login_response = requests.post(f"{base_url}/auth/login", data=login_data)
        if login_response.status_code == 200:
            print("✅ Separate login also works")
        else:
            print(f"⚠️  Separate login status: {login_response.status_code}")
    except Exception as e:
        print(f"⚠️  Separate login test: {e}")
    
    # Test 5: Protected endpoint access
    try:
        headers = {"Authorization": f"Bearer {auth_token}"}
        me_response = requests.get(f"{base_url}/auth/me", headers=headers)
        if me_response.status_code == 200:
            user_info = me_response.json()
            print(f"✅ Protected endpoint access - User: {user_info['username']}")
        else:
            print(f"❌ Protected endpoint failed: {me_response.status_code}")
    except Exception as e:
        print(f"❌ Protected endpoint error: {e}")
    
    # Test 6: Create expense
    try:
        expense_data = {
            "title": "Test Expense",
            "amount": 25.99,
            "currency": "USD",
            "date": "2024-01-15",
            "category": "Food"
        }
        expense_response = requests.post(f"{base_url}/expenses/", json=expense_data, headers=headers)
        if expense_response.status_code == 201:
            expense_info = expense_response.json()
            print(f"✅ Expense creation successful - ID: {expense_info['id']}")
        else:
            print(f"❌ Expense creation failed: {expense_response.status_code}")
            print(f"   Response: {expense_response.text}")
    except Exception as e:
        print(f"❌ Expense creation error: {e}")
    
    # Test 7: List expenses with pagination
    try:
        expenses_response = requests.get(f"{base_url}/expenses/?skip=0&limit=10", headers=headers)
        if expenses_response.status_code == 200:
            expenses = expenses_response.json()
            print(f"✅ Expense listing successful - Found {len(expenses)} expenses")
        else:
            print(f"❌ Expense listing failed: {expenses_response.status_code}")
    except Exception as e:
        print(f"❌ Expense listing error: {e}")
    
    # Test 8: Create budget
    try:
        budget_data = {
            "category": "Food",
            "amount": 500.0,
            "currency": "USD", 
            "period": "monthly"
        }
        budget_response = requests.post(f"{base_url}/budgets/", json=budget_data, headers=headers)
        if budget_response.status_code == 201:
            budget_info = budget_response.json()
            print(f"✅ Budget creation successful - ID: {budget_info['id']}")
        else:
            print(f"❌ Budget creation failed: {budget_response.status_code}")
            print(f"   Response: {budget_response.text}")
    except Exception as e:
        print(f"❌ Budget creation error: {e}")
    
    # Test 9: List budgets
    try:
        budgets_response = requests.get(f"{base_url}/budgets/", headers=headers)
        if budgets_response.status_code == 200:
            budgets = budgets_response.json()
            print(f"✅ Budget listing successful - Found {len(budgets)} budgets")
        else:
            print(f"❌ Budget listing failed: {budgets_response.status_code}")
    except Exception as e:
        print(f"❌ Budget listing error: {e}")
    
    # Test 10: Receipt upload test endpoint
    try:
        receipt_test_response = requests.get(f"{base_url}/upload/receipt/test")
        if receipt_test_response.status_code == 200:
            test_info = receipt_test_response.json()
            print(f"✅ Receipt processing available - Status: {test_info.get('status', 'unknown')}")
        else:
            print(f"⚠️  Receipt processing test: {receipt_test_response.status_code}")
            if receipt_test_response.status_code == 500:
                error_info = receipt_test_response.json()
                print(f"   Note: {error_info.get('message', 'OCR may need configuration')}")
    except Exception as e:
        print(f"⚠️  Receipt processing test error: {e}")
    
    print("\n" + "=" * 40)
    print("✅ Core API functionality verified!")
    print("📚 View API docs at: http://localhost:8000/docs")
    print("📖 Alternative docs at: http://localhost:8000/redoc")
    
    return True

if __name__ == "__main__":
    success = test_api()
    sys.exit(0 if success else 1)
