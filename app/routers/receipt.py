import os
import uuid
import time
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.dependencies.jwt_auth import get_current_user
from app.dependencies.db import get_db
from app.schemas.receipt import (
    ReceiptProcessingResponse, ReceiptExtractionResult, 
    ParsedReceiptData, ReceiptValidationError
)
from app.schemas.common import ErrorResponse
from app.services.receipt_processor import ReceiptProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["Receipt Processing"])

# Configuration
UPLOAD_DIR = Path("uploads/receipts")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.pdf', '.bmp', '.tiff', '.webp'}
ALLOWED_MIME_TYPES = {
    'image/jpeg', 'image/jpg', 'image/png', 'image/bmp', 
    'image/tiff', 'image/webp', 'application/pdf'
}


def validate_file(file: UploadFile) -> Optional[str]:
    """Validate uploaded file format and size."""
    
    # Check file size
    if hasattr(file, 'size') and file.size and file.size > MAX_FILE_SIZE:
        return f"File size ({file.size / 1024 / 1024:.1f}MB) exceeds maximum allowed size ({MAX_FILE_SIZE / 1024 / 1024}MB)"
    
    # Check file extension
    if file.filename:
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            return f"File extension '{file_ext}' not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS)}"
    
    # Check MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        return f"File type '{file.content_type}' not allowed. Supported: {', '.join(ALLOWED_MIME_TYPES)}"
    
    return None


@router.post(
    "/receipt",
    response_model=ReceiptProcessingResponse,
    summary="Process receipt for expense extraction",
    description="Upload a receipt image/PDF and extract expense data using OCR and NLP.",
    responses={
        200: {"description": "Receipt processed successfully"},
        400: {"model": ReceiptValidationError, "description": "Invalid file format or size"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        422: {"description": "File validation error"},
        500: {"model": ErrorResponse, "description": "Processing error"}
    }
)
async def process_receipt(
    file: UploadFile = File(..., description="Receipt image or PDF file"),
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process uploaded receipt and extract expense data."""
    
    try:
        # Validate file
        validation_error = validate_file(file)
        if validation_error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_type": "FILE_VALIDATION_ERROR",
                    "message": validation_error
                }
            )
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_ext = Path(file.filename).suffix.lower() if file.filename else '.jpg'
        unique_filename = f"{file_id}{file_ext}"
        file_path = UPLOAD_DIR / unique_filename
        
        # Save uploaded file
        try:
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
        except Exception as e:
            logger.error(f"Failed to save uploaded file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"code": "FILE_SAVE_ERROR", "message": "Failed to save uploaded file"}
            )
        
        # Process the receipt
        start_time = time.time()
        
        try:
            processing_result = ReceiptProcessor.process_receipt(str(file_path))
        except Exception as e:
            logger.error(f"Receipt processing failed: {e}")
            # Clean up uploaded file on processing failure
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"code": "PROCESSING_ERROR", "message": f"Receipt processing failed: {str(e)}"}
            )
        
        processing_time = time.time() - start_time
        
        if not processing_result.get('success', False):
            # Clean up file on processing failure
            if file_path.exists():
                file_path.unlink()
            
            error_msg = processing_result.get('error', 'Unknown processing error')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"code": "PROCESSING_FAILED", "message": error_msg}
            )
        
        # Prepare response
        extraction_result = ReceiptExtractionResult(
            raw_text=processing_result['raw_text'],
            confidence=processing_result['ocr_confidence'],
            processing_time=processing_result['processing_time']
        )
        
        extracted_data = processing_result['extracted_data']
        parsed_data = ParsedReceiptData(
            amount=extracted_data.get('amount'),
            amount_confidence=extracted_data.get('amount_confidence', 0.0),
            date=extracted_data.get('date'),
            date_confidence=extracted_data.get('date_confidence', 0.0),
            vendor=extracted_data.get('vendor'),
            vendor_confidence=extracted_data.get('vendor_confidence', 0.0),
            category=extracted_data.get('category'),
            category_confidence=extracted_data.get('category_confidence', 0.0),
            overall_confidence=extracted_data.get('overall_confidence', 0.0),
            extraction_notes=extracted_data.get('extraction_notes', [])
        )
        
        # Get file stats
        file_stats = file_path.stat()
        
        # Use a safer way to get relative path
        try:
            relative_path = str(file_path.relative_to(Path.cwd()))
        except ValueError:
            # Fallback if relative_to fails
            relative_path = str(file_path)
        
        response = ReceiptProcessingResponse(
            filename=file.filename or unique_filename,
            file_path=relative_path,
            file_size=file_stats.st_size,
            extraction_result=extraction_result,
            parsed_data=parsed_data,
            suggested_expense=processing_result['suggested_expense'],
            processing_success=True
        )
        
        # Log successful processing
        logger.info(f"Receipt processed successfully for user {current_user}: "
                   f"confidence={extracted_data.get('overall_confidence', 0):.2f}, "
                   f"amount={extracted_data.get('amount')}, "
                   f"vendor={extracted_data.get('vendor')}")
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error in receipt processing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        )


@router.get(
    "/receipt/test",
    summary="Test receipt processing endpoint",
    description="Test endpoint to verify receipt processing functionality is available.",
    responses={
        200: {"description": "Receipt processing is available"},
        500: {"description": "Receipt processing not properly configured"}
    }
)
async def test_receipt_processing():
    """Test endpoint for receipt processing functionality."""
    
    try:
        # Test if required libraries are available
        import pytesseract
        import cv2
        from PIL import Image
        
        # Test if Tesseract is properly installed
        try:
            version = pytesseract.get_tesseract_version()
            return {
                "status": "available",
                "message": "Receipt processing is ready",
                "tesseract_version": str(version),
                "supported_formats": list(ALLOWED_EXTENSIONS),
                "max_file_size_mb": MAX_FILE_SIZE / 1024 / 1024
            }
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "configuration_error",
                    "message": "Tesseract OCR not properly configured",
                    "error": str(e),
                    "installation_help": "Please install Tesseract OCR: https://github.com/tesseract-ocr/tesseract"
                }
            )
            
    except ImportError as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "dependency_error", 
                "message": "Required dependencies not installed",
                "error": str(e),
                "install_command": "pip install pytesseract opencv-python pillow"
            }
        )


@router.delete(
    "/receipt/{file_id}",
    summary="Delete uploaded receipt file",
    description="Delete a previously uploaded receipt file from the server.",
    responses={
        200: {"description": "File deleted successfully"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "File not found"},
        403: {"model": ErrorResponse, "description": "Permission denied"}
    }
)
async def delete_receipt_file(
    file_id: str,
    current_user: str = Depends(get_current_user)
):
    """Delete an uploaded receipt file."""
    
    try:
        # Find file with the given ID
        files = list(UPLOAD_DIR.glob(f"{file_id}.*"))
        
        if not files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "FILE_NOT_FOUND", "message": "Receipt file not found"}
            )
        
        file_path = files[0]
        
        # Delete the file
        file_path.unlink()
        
        logger.info(f"Receipt file deleted by user {current_user}: {file_path.name}")
        
        return {
            "success": True,
            "message": "Receipt file deleted successfully",
            "filename": file_path.name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting receipt file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "DELETE_ERROR", "message": "Failed to delete file"}
        )
