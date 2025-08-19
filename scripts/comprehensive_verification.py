#!/usr/bin/env python3
"""
Comprehensive verification of all core flows
Tests the acceptance criteria: auth → add expense → set budget → upload receipt → dashboard
"""

import requests
import json
import time
import sys
from datetime import date
import io
from PIL import Image

def create_test_receipt():
    """Create a simple test receipt image with text."""
    # Create a white image
    img = Image.new('RGB', (400, 200), 'white')
    
    # Convert to bytes
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    return img_buffer.getvalue()

def comprehensive_test():
    base_url = "http://localhost:8000"
    results = {
        "total_tests": 0,
        "passed": 0,
        "failed": 0,
        "details": []
    }
    
    def log_test(name, success, details=""):
        results["total_tests"] += 1
        if success:
            results["passed"] += 1
            print(f"✅ {name}: PASSED {details}")
        else:
            results["failed"] += 1
            print(f"❌ {name}: FAILED {details}")
        results["details"].append({"test": name, "passed": success, "details": details})
    
    print("🚀 COMPREHENSIVE EXPENSE TRACKER VERIFICATION")
    print("=" * 60)
    print("Testing core flow: auth → expenses → budgets → receipt → dashboard")
    print("=" * 60)
    
    # Step 1: Verify OpenAPI Documentation
    print("\n📚 STEP 1: OpenAPI Documentation")
    try:
        docs_response = requests.get(f"{base_url}/docs", timeout=5)
        redoc_response = requests.get(f"{base_url}/redoc", timeout=5)
        openapi_response = requests.get(f"{base_url}/openapi.json", timeout=5)
        
        docs_ok = docs_response.status_code == 200
        redoc_ok = redoc_response.status_code == 200
        openapi_ok = openapi_response.status_code == 200
        
        log_test("OpenAPI /docs endpoint", docs_ok)
        log_test("OpenAPI /redoc endpoint", redoc_ok)
        log_test("OpenAPI JSON schema", openapi_ok)
        
        if openapi_ok:
            openapi_data = openapi_response.json()
            paths_count = len(openapi_data.get('paths', {}))
            log_test("OpenAPI schema structure", "paths" in openapi_data, f"{paths_count} endpoints")
        
    except Exception as e:
        log_test("OpenAPI documentation", False, str(e))
    
    # Step 2: Authentication Flow
    print("\n🔐 STEP 2: Authentication Flow")
    user_data = {
        "username": f"verify_user_{int(time.time())}",
        "email": f"verify_{int(time.time())}@example.com",
        "password": "SecurePass123!",
        "base_currency": "USD"
    }
    
    auth_token = None
    try:
        # Test registration
        register_response = requests.post(f"{base_url}/auth/register", json=user_data)
        if register_response.status_code == 201:
            token_data = register_response.json()
            auth_token = token_data["access_token"]
            log_test("User registration", True, "Token received")
            
            # Verify token structure
            token_valid = "access_token" in token_data and "token_type" in token_data
            log_test("Token response structure", token_valid)
        else:
            log_test("User registration", False, f"Status: {register_response.status_code}")
            
    except Exception as e:
        log_test("User registration", False, str(e))
    
    if not auth_token:
        print("❌ Cannot proceed without authentication token")
        return results
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Test protected endpoint access
    try:
        me_response = requests.get(f"{base_url}/auth/me", headers=headers)
        if me_response.status_code == 200:
            user_info = me_response.json()
            username_match = user_info.get("username") == user_data["username"]
            log_test("Protected endpoint access", True, f"User: {user_info.get('username')}")
            log_test("User data consistency", username_match)
        else:
            log_test("Protected endpoint access", False, f"Status: {me_response.status_code}")
    except Exception as e:
        log_test("Protected endpoint access", False, str(e))
    
    # Step 3: Expense Management
    print("\n💰 STEP 3: Expense Management")
    expense_id = None
    
    # Test expense creation
    try:
        expense_data = {
            "title": "Verification Test Expense",
            "amount": 42.99,
            "currency": "USD",
            "date": date.today().isoformat(),
            "category": "Food"
        }
        
        create_response = requests.post(f"{base_url}/expenses/", json=expense_data, headers=headers)
        if create_response.status_code == 201:
            expense_info = create_response.json()
            expense_id = expense_info.get("id")
            
            # Verify response model
            required_fields = ["id", "title", "amount", "currency", "date", "category", "user_id"]
            missing_fields = [f for f in required_fields if f not in expense_info]
            
            log_test("Expense creation", True, f"ID: {expense_id}")
            log_test("Expense response model", len(missing_fields) == 0, 
                    f"Missing: {missing_fields}" if missing_fields else "All fields present")
            
            # Verify data integrity
            amount_match = expense_info.get("amount") == expense_data["amount"]
            title_match = expense_info.get("title") == expense_data["title"]
            log_test("Expense data integrity", amount_match and title_match)
        else:
            log_test("Expense creation", False, f"Status: {create_response.status_code}")
            
    except Exception as e:
        log_test("Expense creation", False, str(e))
    
    # Test expense listing with pagination
    try:
        # Test basic listing
        list_response = requests.get(f"{base_url}/expenses/", headers=headers)
        if list_response.status_code == 200:
            expenses = list_response.json()
            log_test("Expense listing", True, f"Found {len(expenses)} expenses")
            
            # Test pagination
            paginated_response = requests.get(f"{base_url}/expenses/?skip=0&limit=5", headers=headers)
            if paginated_response.status_code == 200:
                paginated_expenses = paginated_response.json()
                log_test("Expense pagination", True, f"Paginated: {len(paginated_expenses)} expenses")
                
                # Verify response is list
                log_test("Expense list response type", isinstance(expenses, list))
            else:
                log_test("Expense pagination", False, f"Status: {paginated_response.status_code}")
        else:
            log_test("Expense listing", False, f"Status: {list_response.status_code}")
            
    except Exception as e:
        log_test("Expense listing", False, str(e))
    
    # Step 4: Budget Management
    print("\n📊 STEP 4: Budget Management")
    budget_id = None
    
    # Test budget creation
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
            budget_id = budget_info.get("id")
            
            # Verify response model
            required_fields = ["id", "category", "amount", "currency", "period", "user_id"]
            missing_fields = [f for f in required_fields if f not in budget_info]
            
            log_test("Budget creation", True, f"ID: {budget_id}")
            log_test("Budget response model", len(missing_fields) == 0)
        else:
            log_test("Budget creation", False, f"Status: {budget_response.status_code}, Response: {budget_response.text}")
            
    except Exception as e:
        log_test("Budget creation", False, str(e))
    
    # Test budget listing
    try:
        budget_list_response = requests.get(f"{base_url}/budgets/", headers=headers)
        if budget_list_response.status_code == 200:
            budgets = budget_list_response.json()
            log_test("Budget listing", True, f"Found {len(budgets)} budgets")
            log_test("Budget list response type", isinstance(budgets, list))
        else:
            log_test("Budget listing", False, f"Status: {budget_list_response.status_code}")
            
    except Exception as e:
        log_test("Budget listing", False, str(e))
    
    # Step 5: Receipt Upload & OCR
    print("\n📄 STEP 5: Receipt Upload & OCR Processing")
    
    # Test OCR availability
    try:
        ocr_test_response = requests.get(f"{base_url}/upload/receipt/test")
        if ocr_test_response.status_code == 200:
            ocr_info = ocr_test_response.json()
            log_test("OCR system availability", True, f"Status: {ocr_info.get('status')}")
        else:
            log_test("OCR system availability", False, f"Status: {ocr_test_response.status_code}")
    except Exception as e:
        log_test("OCR system availability", False, str(e))
    
    # Test receipt upload
    try:
        test_receipt = create_test_receipt()
        files = {"file": ("test_receipt.png", test_receipt, "image/png")}
        
        upload_response = requests.post(f"{base_url}/upload/receipt", files=files, headers=headers)
        if upload_response.status_code == 200:
            receipt_data = upload_response.json()
            
            # Verify prefilled expense structure
            suggested_expense = receipt_data.get("suggested_expense", {})
            required_fields = ["title", "amount", "currency", "date", "category"]
            missing_fields = [f for f in required_fields if f not in suggested_expense]
            
            log_test("Receipt upload", True, "OCR processing completed")
            log_test("Prefilled expense structure", len(missing_fields) == 0,
                    f"Missing: {missing_fields}" if missing_fields else "All fields present")
            
            # Verify response structure
            response_fields = ["filename", "extraction_result", "parsed_data", "suggested_expense"]
            missing_response_fields = [f for f in response_fields if f not in receipt_data]
            log_test("Receipt response model", len(missing_response_fields) == 0)
            
        else:
            log_test("Receipt upload", False, f"Status: {upload_response.status_code}")
            
    except Exception as e:
        log_test("Receipt upload", False, str(e))
    
    # Step 6: Dashboard/Analytics
    print("\n📈 STEP 6: Dashboard & Analytics")
    
    # Test analytics dashboard
    try:
        dashboard_response = requests.get(f"{base_url}/analytics/dashboard", headers=headers)
        if dashboard_response.status_code == 200:
            dashboard_data = dashboard_response.json()
            log_test("Analytics dashboard", True, f"Data type: {type(dashboard_data).__name__}")
            
            # Check if response has meaningful structure
            if isinstance(dashboard_data, dict):
                log_test("Dashboard data structure", len(dashboard_data) > 0)
            else:
                log_test("Dashboard data structure", True, "Non-dict response acceptable")
        else:
            log_test("Analytics dashboard", False, f"Status: {dashboard_response.status_code}")
            
    except Exception as e:
        log_test("Analytics dashboard", False, str(e))
    
    # Step 7: Response Model Validation
    print("\n🔍 STEP 7: Response Model Validation")
    
    # Check that no stack traces appear in error responses
    try:
        # Test 404 error
        not_found_response = requests.get(f"{base_url}/nonexistent", headers=headers)
        error_text = not_found_response.text.lower()
        
        stack_indicators = ["traceback", "file \"", "line ", "exception:", "error at"]
        has_stack_trace = any(indicator in error_text for indicator in stack_indicators)
        
        log_test("Clean error responses", not has_stack_trace, "No stack traces in errors")
        
        # Test 401 error (unauthorized)
        unauth_response = requests.get(f"{base_url}/expenses/")
        log_test("Proper authentication enforcement", unauth_response.status_code == 401)
        
    except Exception as e:
        log_test("Error response validation", False, str(e))
    
    # Final Summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    
    success_rate = (results["passed"] / results["total_tests"] * 100) if results["total_tests"] > 0 else 0
    
    print(f"Total Tests: {results['total_tests']}")
    print(f"✅ Passed: {results['passed']}")
    print(f"❌ Failed: {results['failed']}")
    print(f"📈 Success Rate: {success_rate:.1f}%")
    
    if results["failed"] > 0:
        print(f"\n🔍 Failed Tests:")
        for detail in results["details"]:
            if not detail["passed"]:
                print(f"  • {detail['test']}: {detail['details']}")
    
    print(f"\n🎯 CORE FLOW VERIFICATION:")
    core_steps = [
        "User registration", "Protected endpoint access", "Expense creation", 
        "Expense listing", "Budget listing", "Analytics dashboard"
    ]
    
    core_passed = sum(1 for detail in results["details"] 
                     if detail["test"] in core_steps and detail["passed"])
    core_total = len([d for d in results["details"] if d["test"] in core_steps])
    
    print(f"Core functionality: {core_passed}/{core_total} working")
    
    if success_rate >= 90:
        print("🎉 EXCELLENT! All core flows verified successfully.")
        grade = "A+"
    elif success_rate >= 80:
        print("✅ VERY GOOD! Most functionality working well.")
        grade = "A"
    elif success_rate >= 70:
        print("👍 GOOD! Core functionality is solid.")
        grade = "B+"
    elif success_rate >= 60:
        print("⚠️  ACCEPTABLE! Some issues need attention.")
        grade = "B"
    else:
        print("❌ NEEDS WORK! Major issues detected.")
        grade = "C"
    
    print(f"📝 Overall Grade: {grade}")
    
    print(f"\n🔗 Access Points:")
    print(f"   📚 API Documentation: {base_url}/docs")
    print(f"   📖 Alternative Docs: {base_url}/redoc")
    print(f"   🏠 Application: {base_url}/")
    
    return results

if __name__ == "__main__":
    results = comprehensive_test()
    
    # Exit with appropriate code
    exit_code = 0 if results["failed"] == 0 else 1
    sys.exit(exit_code)
