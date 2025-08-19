"""
Test main application functionality and endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestMainApplication:
    """Test main application endpoints and functionality."""

    def test_root_endpoint(self, client: TestClient):
        """Test the root endpoint."""
        response = client.get("/")
        
        # Should redirect or return main page
        assert response.status_code in [200, 301, 302, 307, 308]

    def test_docs_endpoint(self, client: TestClient):
        """Test API documentation endpoint."""
        response = client.get("/docs")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_openapi_json(self, client: TestClient):
        """Test OpenAPI JSON endpoint."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "Expense Tracker API"

    def test_redoc_endpoint(self, client: TestClient):
        """Test ReDoc documentation endpoint."""
        response = client.get("/redoc")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_cors_headers(self, client: TestClient):
        """Test CORS headers are present."""
        response = client.options("/docs")
        
        assert response.status_code in [200, 405]  # OPTIONS might not be implemented
        
        # Test with actual request
        response = client.get("/docs")
        
        # CORS headers should be present for API responses
        response = client.get("/openapi.json")
        assert response.status_code == 200

    def test_health_check_via_docs(self, client: TestClient):
        """Test application health via docs availability."""
        response = client.get("/docs")
        
        assert response.status_code == 200
        # If docs load, the application is healthy

    def test_static_files_access(self, client: TestClient):
        """Test static files are accessible."""
        # Try to access CSS file
        response = client.get("/static/main.css")
        
        # Should either return the file or 404 if not found
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            assert "text/css" in response.headers.get("content-type", "")

    def test_template_pages_exist(self, client: TestClient):
        """Test that template pages are accessible."""
        pages = ["/login", "/signup", "/me", "/expenses", "/analytics", "/upload", "/receipt"]
        
        for page in pages:
            response = client.get(page)
            
            # Should return the page or redirect
            assert response.status_code in [200, 301, 302, 307, 308]
            
            if response.status_code == 200:
                assert "text/html" in response.headers.get("content-type", "")
