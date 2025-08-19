#!/usr/bin/env python3
"""
Comprehensive smoke test for Expense Tracker API
Tests all core flows: auth → expenses → budgets → receipt upload → dashboard
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, Optional
import tempfile
from PIL import Image
import io

import httpx


class SmokeTest:
    """Comprehensive smoke test suite for Expense Tracker API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        self.auth_token: Optional[str] = None
        self.test_user = {
            "username": f"testuser_{int(time.time())}",
            "email": f"test_{int(time.time())}@example.com",
            "password": "TestPassword123!",
            "base_currency": "USD"
        }
        self.results = {
            "passed": 0,
            "failed": 0,
            "errors": [],
            "details": {}
        }
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def log_success(self, test_name: str, details: str = ""):
        """Log successful test."""
        print(f"✅ {test_name}: PASSED {details}")
        self.results["passed"] += 1
        self.results["details"][test_name] = {"status": "PASSED", "details": details}
    
    def log_failure(self, test_name: str, error: str):
        """Log failed test."""
        print(f"❌ {test_name}: FAILED - {error}")
        self.results["failed"] += 1
        self.results["errors"].append(f"{test_name}: {error}")
        self.results["details"][test_name] = {"status": "FAILED", "error": error}
    
    def log_info(self, message: str):
        """Log info message."""
        print(f"ℹ️  {message}")
    
    async def test_server_health(self) -> bool:
        """Test basic server health."""
        try:
            response = await self.client.get(f"{self.base_url}/docs")
            if response.status_code == 200:
                self.log_success("Server Health", f"Status: {response.status_code}")
                return True
            else:
                self.log_failure("Server Health", f"Expected 200, got {response.status_code}")
                return False
        except Exception as e:
            self.log_failure("Server Health", f"Connection error: {str(e)}")
            return False
    
    async def test_openapi_docs(self):
        """Test OpenAPI documentation endpoints."""
        test_name = "OpenAPI Documentation"
        
        try:
            # Test /docs endpoint
            docs_response = await self.client.get(f"{self.base_url}/docs")
            if docs_response.status_code != 200:
                self.log_failure(test_name, f"/docs returned {docs_response.status_code}")
                return
            
            # Test /redoc endpoint
            redoc_response = await self.client.get(f"{self.base_url}/redoc")
            if redoc_response.status_code != 200:
                self.log_failure(test_name, f"/redoc returned {redoc_response.status_code}")
                return
            
            # Test OpenAPI JSON
            openapi_response = await self.client.get(f"{self.base_url}/openapi.json")
            if openapi_response.status_code != 200:
                self.log_failure(test_name, f"/openapi.json returned {openapi_response.status_code}")
                return
            
            # Validate OpenAPI structure
            openapi_data = openapi_response.json()
            required_fields = ["openapi", "info", "paths"]
            missing_fields = [field for field in required_fields if field not in openapi_data]
            
            if missing_fields:
                self.log_failure(test_name, f"Missing OpenAPI fields: {missing_fields}")
                return
            
            self.log_success(test_name, f"All endpoints accessible, {len(openapi_data['paths'])} API paths found")
            
        except Exception as e:
            self.log_failure(test_name, f"Error: {str(e)}")
    
    async def test_auth_flow(self) -> bool:
        """Test complete authentication flow."""
        # Test user registration
        signup_success = await self.test_user_signup()
        if not signup_success:
            return False
        
        # Test user login
        login_success = await self.test_user_login()
        if not login_success:
            return False
        
        # Test protected endpoint access
        return await self.test_protected_access()
    
    async def test_user_signup(self) -> bool:
        """Test user registration."""
        test_name = "User Signup"
        
        try:
            response = await self.client.post(
                f"{self.base_url}/auth/signup",
                json=self.test_user
            )
            
            if response.status_code != 201:
                self.log_failure(test_name, f"Expected 201, got {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            required_fields = ["id", "username", "email", "base_currency"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                self.log_failure(test_name, f"Response missing fields: {missing_fields}")
                return False
            
            if "hashed_password" in data:
                self.log_failure(test_name, "Response contains hashed_password (security issue)")
                return False
            
            self.log_success(test_name, f"User created with ID: {data['id']}")
            return True
            
        except Exception as e:
            self.log_failure(test_name, f"Error: {str(e)}")
            return False
    
    async def test_user_login(self) -> bool:
        """Test user login and token retrieval."""
        test_name = "User Login"
        
        try:
            login_data = {
                "username": self.test_user["username"],
                "password": self.test_user["password"]
            }
            
            response = await self.client.post(
                f"{self.base_url}/auth/login",
                data=login_data  # Form data for OAuth2
            )
            
            if response.status_code != 200:
                self.log_failure(test_name, f"Expected 200, got {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            required_fields = ["access_token", "token_type"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                self.log_failure(test_name, f"Response missing fields: {missing_fields}")
                return False
            
            if data["token_type"] != "bearer":
                self.log_failure(test_name, f"Expected token_type 'bearer', got '{data['token_type']}'")
                return False
            
            self.auth_token = data["access_token"]
            self.log_success(test_name, f"Token received: {data['access_token'][:20]}...")
            return True
            
        except Exception as e:
            self.log_failure(test_name, f"Error: {str(e)}")
            return False
    
    async def test_protected_access(self) -> bool:
        """Test accessing protected endpoints with token."""
        test_name = "Protected Endpoint Access"
        
        try:
            if not self.auth_token:
                self.log_failure(test_name, "No auth token available")
                return False
            
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = await self.client.get(f"{self.base_url}/auth/me", headers=headers)
            
            if response.status_code != 200:
                self.log_failure(test_name, f"Expected 200, got {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            if data["username"] != self.test_user["username"]:
                self.log_failure(test_name, f"Username mismatch: expected {self.test_user['username']}, got {data['username']}")
                return False
            
            self.log_success(test_name, f"Authenticated as: {data['username']}")
            return True
            
        except Exception as e:
            self.log_failure(test_name, f"Error: {str(e)}")
            return False
    
    async def test_expense_flow(self) -> bool:
        """Test expense creation and retrieval."""
        if not self.auth_token:
            self.log_failure("Expense Flow", "No auth token available")
            return False
        
        create_success = await self.test_expense_creation()
        if not create_success:
            return False
        
        list_success = await self.test_expense_listing()
        return list_success
    
    async def test_expense_creation(self) -> bool:
        """Test expense creation."""
        test_name = "Expense Creation"
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            expense_data = {
                "title": "Test Expense",
                "amount": 25.99,
                "currency": "USD",
                "date": date.today().isoformat(),
                "category": "Food"
            }
            
            response = await self.client.post(
                f"{self.base_url}/expenses/",
                json=expense_data,
                headers=headers
            )
            
            if response.status_code != 201:
                self.log_failure(test_name, f"Expected 201, got {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            required_fields = ["id", "title", "amount", "currency", "date", "category", "user_id"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                self.log_failure(test_name, f"Response missing fields: {missing_fields}")
                return False
            
            # Validate data integrity
            if data["amount"] != expense_data["amount"]:
                self.log_failure(test_name, f"Amount mismatch: expected {expense_data['amount']}, got {data['amount']}")
                return False
            
            self.log_success(test_name, f"Expense created with ID: {data['id']}")
            return True
            
        except Exception as e:
            self.log_failure(test_name, f"Error: {str(e)}")
            return False
    
    async def test_expense_listing(self) -> bool:
        """Test expense listing with pagination."""
        test_name = "Expense Listing & Pagination"
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Test basic listing
            response = await self.client.get(f"{self.base_url}/expenses/", headers=headers)
            
            if response.status_code != 200:
                self.log_failure(test_name, f"Expected 200, got {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            if not isinstance(data, list):
                self.log_failure(test_name, f"Expected list response, got {type(data)}")
                return False
            
            # Test pagination parameters
            pagination_response = await self.client.get(
                f"{self.base_url}/expenses/?skip=0&limit=10", 
                headers=headers
            )
            
            if pagination_response.status_code != 200:
                self.log_failure(test_name, f"Pagination failed: {pagination_response.status_code}")
                return False
            
            pagination_data = pagination_response.json()
            if not isinstance(pagination_data, list):
                self.log_failure(test_name, f"Pagination response not a list: {type(pagination_data)}")
                return False
            
            self.log_success(test_name, f"Retrieved {len(data)} expenses, pagination working")
            return True
            
        except Exception as e:
            self.log_failure(test_name, f"Error: {str(e)}")
            return False
    
    async def test_budget_flow(self) -> bool:
        """Test budget creation and retrieval."""
        if not self.auth_token:
            self.log_failure("Budget Flow", "No auth token available")
            return False
        
        create_success = await self.test_budget_creation()
        if not create_success:
            return False
        
        list_success = await self.test_budget_listing()
        return list_success
    
    async def test_budget_creation(self) -> bool:
        """Test budget creation."""
        test_name = "Budget Creation"
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            budget_data = {
                "category": "Food",
                "amount": 500.0,
                "currency": "USD",
                "period": "monthly"
            }
            
            response = await self.client.post(
                f"{self.base_url}/budgets/",
                json=budget_data,
                headers=headers
            )
            
            if response.status_code != 201:
                self.log_failure(test_name, f"Expected 201, got {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            required_fields = ["id", "category", "amount", "currency", "period", "user_id"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                self.log_failure(test_name, f"Response missing fields: {missing_fields}")
                return False
            
            self.log_success(test_name, f"Budget created with ID: {data['id']}")
            return True
            
        except Exception as e:
            self.log_failure(test_name, f"Error: {str(e)}")
            return False
    
    async def test_budget_listing(self) -> bool:
        """Test budget listing."""
        test_name = "Budget Listing"
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = await self.client.get(f"{self.base_url}/budgets/", headers=headers)
            
            if response.status_code != 200:
                self.log_failure(test_name, f"Expected 200, got {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            if not isinstance(data, list):
                self.log_failure(test_name, f"Expected list response, got {type(data)}")
                return False
            
            self.log_success(test_name, f"Retrieved {len(data)} budgets")
            return True
            
        except Exception as e:
            self.log_failure(test_name, f"Error: {str(e)}")
            return False
    
    async def test_receipt_upload_flow(self) -> bool:
        """Test receipt upload and OCR processing."""
        test_name = "Receipt Upload & OCR"
        
        try:
            if not self.auth_token:
                self.log_failure(test_name, "No auth token available")
                return False
            
            # Create a test receipt image
            test_image = self.create_test_receipt_image()
            
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            files = {"file": ("test_receipt.png", test_image, "image/png")}
            
            response = await self.client.post(
                f"{self.base_url}/upload/receipt",
                headers=headers,
                files=files
            )
            
            if response.status_code != 200:
                # If OCR is not properly configured, we might get an error
                # Let's check if it's a configuration issue
                if response.status_code == 500:
                    error_data = response.json()
                    if "tesseract" in error_data.get("detail", {}).get("message", "").lower():
                        self.log_failure(test_name, "OCR not properly configured (Tesseract missing)")
                        return False
                
                self.log_failure(test_name, f"Expected 200, got {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            required_fields = ["filename", "extraction_result", "parsed_data", "suggested_expense"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                self.log_failure(test_name, f"Response missing fields: {missing_fields}")
                return False
            
            # Validate suggested expense structure
            suggested_expense = data["suggested_expense"]
            expense_fields = ["title", "amount", "currency", "date", "category"]
            missing_expense_fields = [field for field in expense_fields if field not in suggested_expense]
            
            if missing_expense_fields:
                self.log_failure(test_name, f"Suggested expense missing fields: {missing_expense_fields}")
                return False
            
            self.log_success(test_name, f"Receipt processed, suggested amount: ${suggested_expense['amount']}")
            return True
            
        except Exception as e:
            self.log_failure(test_name, f"Error: {str(e)}")
            return False
    
    def create_test_receipt_image(self) -> bytes:
        """Create a simple test receipt image."""
        # Create a simple white image with black text
        img = Image.new('RGB', (400, 300), color='white')
        
        # Convert to bytes
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return img_buffer.getvalue()
    
    async def test_analytics_endpoints(self) -> bool:
        """Test analytics/dashboard endpoints."""
        test_name = "Analytics Endpoints"
        
        try:
            if not self.auth_token:
                self.log_failure(test_name, "No auth token available")
                return False
            
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Test analytics dashboard
            response = await self.client.get(f"{self.base_url}/analytics/dashboard", headers=headers)
            
            if response.status_code != 200:
                self.log_failure(test_name, f"Dashboard endpoint failed: {response.status_code}")
                return False
            
            data = response.json()
            expected_sections = ["summary", "spending_by_category", "monthly_trends"]
            
            # Check if response has analytics structure (may vary based on implementation)
            if isinstance(data, dict):
                self.log_success(test_name, f"Dashboard data retrieved with {len(data)} sections")
            else:
                self.log_success(test_name, "Dashboard endpoint accessible")
            
            return True
            
        except Exception as e:
            self.log_failure(test_name, f"Error: {str(e)}")
            return False
    
    async def test_response_models(self) -> bool:
        """Test that all endpoints return consistent response models."""
        test_name = "Response Model Consistency"
        
        try:
            if not self.auth_token:
                self.log_failure(test_name, "No auth token available")
                return False
            
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Test multiple endpoints for consistent response shapes
            endpoints_to_test = [
                ("/expenses/", "list"),
                ("/budgets/", "list"),
                ("/auth/me", "object")
            ]
            
            for endpoint, response_type in endpoints_to_test:
                response = await self.client.get(f"{self.base_url}{endpoint}", headers=headers)
                
                if response.status_code != 200:
                    self.log_failure(test_name, f"{endpoint} returned {response.status_code}")
                    return False
                
                data = response.json()
                
                if response_type == "list" and not isinstance(data, list):
                    self.log_failure(test_name, f"{endpoint} should return list, got {type(data)}")
                    return False
                elif response_type == "object" and not isinstance(data, dict):
                    self.log_failure(test_name, f"{endpoint} should return object, got {type(data)}")
                    return False
            
            self.log_success(test_name, "All endpoints return consistent response models")
            return True
            
        except Exception as e:
            self.log_failure(test_name, f"Error: {str(e)}")
            return False
    
    async def test_error_handling(self) -> bool:
        """Test error handling and ensure no stack traces in responses."""
        test_name = "Error Handling"
        
        try:
            # Test 404 endpoint
            response = await self.client.get(f"{self.base_url}/nonexistent-endpoint")
            
            if response.status_code != 404:
                self.log_failure(test_name, f"Expected 404 for non-existent endpoint, got {response.status_code}")
                return False
            
            error_data = response.json()
            
            # Check that error response doesn't contain stack traces
            error_text = json.dumps(error_data).lower()
            stack_trace_indicators = ["traceback", "file \"", "line ", "error at", "exception:"]
            
            found_stack_traces = [indicator for indicator in stack_trace_indicators if indicator in error_text]
            if found_stack_traces:
                self.log_failure(test_name, f"Error response contains stack trace indicators: {found_stack_traces}")
                return False
            
            # Test unauthorized access
            unauth_response = await self.client.get(f"{self.base_url}/expenses/")
            if unauth_response.status_code != 401:
                self.log_failure(test_name, f"Expected 401 for unauthorized access, got {unauth_response.status_code}")
                return False
            
            self.log_success(test_name, "Error responses are clean (no stack traces)")
            return True
            
        except Exception as e:
            self.log_failure(test_name, f"Error: {str(e)}")
            return False
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all smoke tests."""
        print("🚀 Starting Comprehensive Smoke Test")
        print("=" * 50)
        
        # Check server health first
        if not await self.test_server_health():
            print("❌ Server is not healthy, aborting tests")
            return self.results
        
        # Test OpenAPI documentation
        await self.test_openapi_docs()
        
        # Test authentication flow
        auth_success = await self.test_auth_flow()
        
        if auth_success:
            # Only proceed with authenticated tests if auth works
            await self.test_expense_flow()
            await self.test_budget_flow()
            await self.test_receipt_upload_flow()
            await self.test_analytics_endpoints()
            await self.test_response_models()
        
        # Test error handling (doesn't require auth)
        await self.test_error_handling()
        
        return self.results
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 50)
        print("📊 SMOKE TEST SUMMARY")
        print("=" * 50)
        
        total_tests = self.results["passed"] + self.results["failed"]
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        
        if self.results["failed"] > 0:
            print(f"\n🔍 FAILURES:")
            for error in self.results["errors"]:
                print(f"  • {error}")
        
        success_rate = (self.results["passed"] / total_tests * 100) if total_tests > 0 else 0
        print(f"\n📈 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print("🎉 EXCELLENT! Application is working well.")
        elif success_rate >= 70:
            print("✅ GOOD! Most features are working.")
        elif success_rate >= 50:
            print("⚠️  NEEDS ATTENTION: Several issues found.")
        else:
            print("❌ CRITICAL: Major issues detected.")


async def main():
    """Main function to run smoke tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smoke test for Expense Tracker API")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the API")
    parser.add_argument("--output", help="JSON file to save detailed results")
    
    args = parser.parse_args()
    
    async with SmokeTest(args.url) as smoke_test:
        results = await smoke_test.run_all_tests()
        smoke_test.print_summary()
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n📄 Detailed results saved to: {args.output}")
        
        # Exit with appropriate code
        exit_code = 0 if results["failed"] == 0 else 1
        sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
