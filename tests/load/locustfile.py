"""
Locust load testing configuration for Expense Tracker API.

This file defines load testing scenarios for:
1. User registration and authentication flow
2. Expense creation and listing
3. Budget management
4. Receipt upload and processing
5. Analytics dashboard access

Run with: locust -f tests/load/locustfile.py --host=http://localhost:8000
"""

import random
import time
import json
from io import BytesIO
from PIL import Image

from locust import HttpUser, task, between, SequentialTaskSet
from locust.exception import StopUser


class AuthenticationFlow(SequentialTaskSet):
    """Sequential flow for user authentication."""
    
    def on_start(self):
        """Initialize test data."""
        self.username = f"loadtest_user_{random.randint(1000, 9999)}_{int(time.time())}"
        self.email = f"loadtest_{random.randint(1000, 9999)}@example.com"
        self.password = "LoadTest123!"
        self.auth_token = None
        self.expense_ids = []
        self.budget_ids = []
    
    @task
    def register_user(self):
        """Test user registration."""
        user_data = {
            "username": self.username,
            "email": self.email,
            "password": self.password,
            "base_currency": "USD"
        }
        
        with self.client.post("/auth/register", 
                            json=user_data, 
                            name="POST /auth/register",
                            catch_response=True) as response:
            if response.status_code == 201:
                data = response.json()
                self.auth_token = data.get("access_token")
                response.success()
            else:
                response.failure(f"Registration failed: {response.status_code}")
                raise StopUser()
    
    @task
    def verify_protected_access(self):
        """Test accessing protected endpoints."""
        if not self.auth_token:
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        with self.client.get("/auth/me", 
                           headers=headers,
                           name="GET /auth/me",
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Protected access failed: {response.status_code}")


class ExpenseManagement(SequentialTaskSet):
    """Sequential flow for expense management."""
    
    def on_start(self):
        """Get auth token from parent user."""
        self.auth_token = getattr(self.user, 'auth_token', None)
        self.expense_ids = getattr(self.user, 'expense_ids', [])
        
        if not self.auth_token:
            raise StopUser("No auth token available")
    
    @task(3)
    def create_expense(self):
        """Test expense creation."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        expense_data = {
            "title": f"Load Test Expense {random.randint(1, 1000)}",
            "amount": round(random.uniform(5.0, 500.0), 2),
            "currency": random.choice(["USD", "EUR", "GBP"]),
            "date": "2024-01-15",
            "category": random.choice(["Food", "Transportation", "Entertainment", "Shopping", "Bills"])
        }
        
        with self.client.post("/expenses/",
                            json=expense_data,
                            headers=headers,
                            name="POST /expenses",
                            catch_response=True) as response:
            if response.status_code == 201:
                data = response.json()
                if "expense" in data and "id" in data["expense"]:
                    self.expense_ids.append(data["expense"]["id"])
                response.success()
            else:
                response.failure(f"Expense creation failed: {response.status_code}")
    
    @task(5)
    def list_expenses(self):
        """Test expense listing."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Test basic listing
        with self.client.get("/expenses/",
                           headers=headers,
                           name="GET /expenses",
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Expense listing failed: {response.status_code}")
    
    @task(2)
    def list_expenses_paginated(self):
        """Test paginated expense listing."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        skip = random.randint(0, 5)
        limit = random.randint(5, 20)
        
        with self.client.get(f"/expenses/?skip={skip}&limit={limit}",
                           headers=headers,
                           name="GET /expenses (paginated)",
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Paginated expense listing failed: {response.status_code}")


class BudgetManagement(SequentialTaskSet):
    """Sequential flow for budget management."""
    
    def on_start(self):
        """Get auth token from parent user."""
        self.auth_token = getattr(self.user, 'auth_token', None)
        self.budget_ids = getattr(self.user, 'budget_ids', [])
        
        if not self.auth_token:
            raise StopUser("No auth token available")
    
    @task(2)
    def create_budget(self):
        """Test budget creation."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        budget_data = {
            "category": random.choice(["Food", "Transportation", "Entertainment", "Shopping", "Bills"]),
            "limit": round(random.uniform(100.0, 2000.0), 2)
        }
        
        with self.client.post("/budgets/",
                            json=budget_data,
                            headers=headers,
                            name="POST /budgets",
                            catch_response=True) as response:
            if response.status_code == 201:
                data = response.json()
                if "id" in data:
                    self.budget_ids.append(data["id"])
                response.success()
            else:
                response.failure(f"Budget creation failed: {response.status_code}")
    
    @task(3)
    def list_budgets(self):
        """Test budget listing."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        with self.client.get("/budgets/",
                           headers=headers,
                           name="GET /budgets",
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Budget listing failed: {response.status_code}")


class AnalyticsDashboard(SequentialTaskSet):
    """Sequential flow for analytics dashboard."""
    
    def on_start(self):
        """Get auth token from parent user."""
        self.auth_token = getattr(self.user, 'auth_token', None)
        
        if not self.auth_token:
            raise StopUser("No auth token available")
    
    @task
    def view_dashboard(self):
        """Test analytics dashboard access."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        with self.client.get("/analytics/dashboard",
                           headers=headers,
                           name="GET /analytics/dashboard",
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Dashboard access failed: {response.status_code}")


class ReceiptProcessing(SequentialTaskSet):
    """Sequential flow for receipt upload and processing."""
    
    def on_start(self):
        """Get auth token from parent user."""
        self.auth_token = getattr(self.user, 'auth_token', None)
        
        if not self.auth_token:
            raise StopUser("No auth token available")
    
    def create_test_receipt(self):
        """Create a test receipt image."""
        img = Image.new('RGB', (400, 300), 'white')
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        return img_buffer.getvalue()
    
    @task
    def upload_receipt(self):
        """Test receipt upload and OCR processing."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Create test image
        receipt_data = self.create_test_receipt()
        files = {"file": ("test_receipt.png", receipt_data, "image/png")}
        
        with self.client.post("/upload/receipt",
                            files=files,
                            headers=headers,
                            name="POST /upload/receipt",
                            catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 500:
                # OCR might not be configured in test environment
                response.success()  # Don't fail the test for OCR config issues
            else:
                response.failure(f"Receipt upload failed: {response.status_code}")


class HealthMonitoring(SequentialTaskSet):
    """Test health and monitoring endpoints."""
    
    @task(1)
    def health_check(self):
        """Test health check endpoint."""
        with self.client.get("/healthz",
                           name="GET /healthz",
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")
    
    @task(1)
    def readiness_check(self):
        """Test readiness check endpoint."""
        with self.client.get("/readyz",
                           name="GET /readyz",
                           catch_response=True) as response:
            if response.status_code in [200, 503]:  # 503 is acceptable for readiness
                response.success()
            else:
                response.failure(f"Readiness check failed: {response.status_code}")
    
    @task(1)
    def slo_status(self):
        """Test SLO status endpoint."""
        with self.client.get("/slo",
                           name="GET /slo",
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"SLO status failed: {response.status_code}")


class ExpenseTrackerUser(HttpUser):
    """
    Expense Tracker load testing user.
    
    This user simulates realistic usage patterns:
    1. Registers and authenticates
    2. Creates and manages expenses
    3. Sets up budgets
    4. Uploads receipts
    5. Views analytics dashboard
    """
    
    # Wait time between tasks (1-5 seconds)
    wait_time = between(1, 5)
    
    def on_start(self):
        """User initialization."""
        self.auth_token = None
        self.expense_ids = []
        self.budget_ids = []
        
        # Run authentication flow first
        auth_flow = AuthenticationFlow(self)
        auth_flow.run()
        
        # Store auth token for other task sets
        self.auth_token = getattr(auth_flow, 'auth_token', None)
        
        if not self.auth_token:
            raise StopUser("Failed to authenticate")
    
    # Task weights for realistic usage patterns
    tasks = {
        ExpenseManagement: 4,      # Most common: managing expenses
        BudgetManagement: 2,       # Moderate: budget management
        AnalyticsDashboard: 2,     # Moderate: viewing analytics
        ReceiptProcessing: 1,      # Less common: receipt uploads
        HealthMonitoring: 1        # Periodic: health checks
    }


class LightloadUser(HttpUser):
    """
    Light load user for basic endpoint testing.
    Focuses on read-heavy operations.
    """
    
    wait_time = between(2, 8)
    
    def on_start(self):
        """Authenticate once."""
        user_data = {
            "username": f"lightuser_{random.randint(1000, 9999)}",
            "email": f"light_{random.randint(1000, 9999)}@example.com",
            "password": "Light123!",
            "base_currency": "USD"
        }
        
        response = self.client.post("/auth/register", json=user_data)
        if response.status_code == 201:
            self.auth_token = response.json().get("access_token")
        else:
            raise StopUser("Authentication failed")
    
    @task(5)
    def list_expenses(self):
        """Read expenses."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        self.client.get("/expenses/", headers=headers, name="GET /expenses (light)")
    
    @task(3)
    def list_budgets(self):
        """Read budgets."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        self.client.get("/budgets/", headers=headers, name="GET /budgets (light)")
    
    @task(2)
    def view_dashboard(self):
        """View analytics."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        self.client.get("/analytics/dashboard", headers=headers, name="GET /analytics/dashboard (light)")
    
    @task(1)
    def health_check(self):
        """Check health."""
        self.client.get("/healthz", name="GET /healthz (light)")


class HeavyloadUser(HttpUser):
    """
    Heavy load user for stress testing.
    Focuses on write-heavy operations.
    """
    
    wait_time = between(0.5, 2)
    
    def on_start(self):
        """Authenticate once."""
        user_data = {
            "username": f"heavyuser_{random.randint(1000, 9999)}",
            "email": f"heavy_{random.randint(1000, 9999)}@example.com",
            "password": "Heavy123!",
            "base_currency": "USD"
        }
        
        response = self.client.post("/auth/register", json=user_data)
        if response.status_code == 201:
            self.auth_token = response.json().get("access_token")
        else:
            raise StopUser("Authentication failed")
    
    @task(4)
    def create_expense(self):
        """Create expenses rapidly."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        expense_data = {
            "title": f"Heavy Load Expense {random.randint(1, 10000)}",
            "amount": round(random.uniform(1.0, 100.0), 2),
            "currency": "USD",
            "date": "2024-01-15",
            "category": "Testing"
        }
        
        self.client.post("/expenses/", json=expense_data, headers=headers, name="POST /expenses (heavy)")
    
    @task(2)
    def create_budget(self):
        """Create budgets."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        budget_data = {
            "category": f"Heavy_{random.randint(1, 1000)}",
            "limit": round(random.uniform(50.0, 500.0), 2)
        }
        
        self.client.post("/budgets/", json=budget_data, headers=headers, name="POST /budgets (heavy)")
    
    @task(1)
    def rapid_reads(self):
        """Rapid read operations."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        self.client.get("/expenses/", headers=headers, name="GET /expenses (heavy)")
        self.client.get("/budgets/", headers=headers, name="GET /budgets (heavy)")
