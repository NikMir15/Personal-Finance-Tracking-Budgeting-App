"""
Test OCR receipt processing functionality.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import io
from PIL import Image


class TestReceiptProcessing:
    """Test receipt processing endpoints and functionality."""

    def test_receipt_test_endpoint(self, client: TestClient):
        """Test the receipt processing test endpoint."""
        response = client.get("/upload/receipt/test")
        
        # Should return either success or configuration error
        assert response.status_code in [200, 500]
        
        data = response.json()
        assert "status" in data
        
        if response.status_code == 200:
            assert data["status"] == "available"
            assert "tesseract_version" in data
            assert "supported_formats" in data
        else:
            assert data["status"] in ["configuration_error", "dependency_error"]

    @patch('app.services.receipt_processor.ReceiptProcessor.process_receipt')
    def test_process_receipt_success(self, mock_process, authenticated_client):
        """Test successful receipt processing."""
        client, test_user = authenticated_client
        
        # Mock successful processing result
        mock_process.return_value = {
            'success': True,
            'raw_text': 'STORE NAME\n2024-01-15\nTotal: $25.99',
            'ocr_confidence': 0.85,
            'processing_time': 2.3,
            'extracted_data': {
                'amount': 25.99,
                'amount_confidence': 0.9,
                'date': '2024-01-15',
                'date_confidence': 0.8,
                'vendor': 'STORE NAME',
                'vendor_confidence': 0.7,
                'category': 'Shopping',
                'category_confidence': 0.6,
                'overall_confidence': 0.75,
                'extraction_notes': []
            },
            'suggested_expense': {
                'title': 'STORE NAME',
                'amount': 25.99,
                'currency': 'USD',
                'date': '2024-01-15',
                'category': 'Shopping'
            }
        }
        
        # Create test image
        image = Image.new('RGB', (100, 100), color='white')
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        files = {"file": ("receipt.png", img_buffer, "image/png")}
        response = client.post("/upload/receipt", files=files)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["processing_success"] is True
        assert data["filename"] == "receipt.png"
        assert "extraction_result" in data
        assert "parsed_data" in data
        assert "suggested_expense" in data
        
        # Check extraction result
        extraction = data["extraction_result"]
        assert extraction["raw_text"] == 'STORE NAME\n2024-01-15\nTotal: $25.99'
        assert extraction["confidence"] == 0.85
        
        # Check parsed data
        parsed = data["parsed_data"]
        assert parsed["amount"] == 25.99
        assert parsed["vendor"] == 'STORE NAME'
        assert parsed["category"] == 'Shopping'
        
        # Check suggested expense
        suggested = data["suggested_expense"]
        assert suggested["title"] == 'STORE NAME'
        assert suggested["amount"] == 25.99
        assert suggested["currency"] == 'USD'

    def test_process_receipt_unauthenticated(self, client: TestClient):
        """Test receipt processing without authentication."""
        # Create test image
        image = Image.new('RGB', (100, 100), color='white')
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        files = {"file": ("receipt.png", img_buffer, "image/png")}
        response = client.post("/upload/receipt", files=files)
        
        assert response.status_code == 401

    def test_process_receipt_invalid_file_type(self, authenticated_client):
        """Test receipt processing with invalid file type."""
        client, _ = authenticated_client
        
        # Create text file instead of image
        text_content = "This is not an image"
        files = {"file": ("receipt.txt", io.StringIO(text_content), "text/plain")}
        
        response = client.post("/upload/receipt", files=files)
        
        assert response.status_code == 400
        data = response.json()
        assert "FILE_VALIDATION_ERROR" in data["detail"]["error_type"]

    def test_process_receipt_large_file(self, authenticated_client):
        """Test receipt processing with oversized file."""
        client, _ = authenticated_client
        
        # Create large dummy file (simulate > 10MB)
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB
        files = {"file": ("large_receipt.png", io.BytesIO(large_content), "image/png")}
        
        response = client.post("/upload/receipt", files=files)
        
        assert response.status_code == 400
        data = response.json()
        assert "size" in data["detail"]["message"].lower()

    @patch('app.services.receipt_processor.ReceiptProcessor.process_receipt')
    def test_process_receipt_processing_failure(self, mock_process, authenticated_client):
        """Test receipt processing when OCR fails."""
        client, _ = authenticated_client
        
        # Mock processing failure
        mock_process.return_value = {
            'success': False,
            'error': 'OCR processing failed'
        }
        
        # Create test image
        image = Image.new('RGB', (100, 100), color='white')
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        files = {"file": ("receipt.png", img_buffer, "image/png")}
        response = client.post("/upload/receipt", files=files)
        
        assert response.status_code == 500
        data = response.json()
        assert "PROCESSING_FAILED" in data["detail"]["code"]

    def test_delete_receipt_file(self, authenticated_client):
        """Test deleting a receipt file."""
        client, _ = authenticated_client
        
        # Test deleting non-existent file
        response = client.delete("/upload/receipt/nonexistent-file-id")
        
        assert response.status_code == 404
        data = response.json()
        assert "FILE_NOT_FOUND" in data["detail"]["code"]

    def test_delete_receipt_unauthenticated(self, client: TestClient):
        """Test deleting receipt file without authentication."""
        response = client.delete("/upload/receipt/some-file-id")
        
        assert response.status_code == 401
