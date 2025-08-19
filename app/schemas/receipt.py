from datetime import date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ReceiptExtractionResult(BaseModel):
    """Result of OCR text extraction from receipt."""
    raw_text: str = Field(..., description="Raw extracted text from OCR")
    confidence: float = Field(..., ge=0, le=1, description="Overall extraction confidence (0-1)")
    processing_time: float = Field(..., description="Processing time in seconds")


class ParsedReceiptData(BaseModel):
    """Parsed receipt data with structured information."""
    # Core expense data
    amount: Optional[float] = Field(None, description="Extracted amount")
    amount_confidence: float = Field(0.0, ge=0, le=1, description="Amount extraction confidence")
    
    date: Optional[str] = Field(None, description="Extracted date (YYYY-MM-DD format)")
    date_confidence: float = Field(0.0, ge=0, le=1, description="Date extraction confidence")
    
    vendor: Optional[str] = Field(None, description="Extracted vendor/merchant name")
    vendor_confidence: float = Field(0.0, ge=0, le=1, description="Vendor extraction confidence")
    
    category: Optional[str] = Field(None, description="Suggested category")
    category_confidence: float = Field(0.0, ge=0, le=1, description="Category suggestion confidence")
    
    # Additional extracted data
    items: List[str] = Field(default_factory=list, description="Individual items if detected")
    payment_method: Optional[str] = Field(None, description="Payment method if detected")
    tax_amount: Optional[float] = Field(None, description="Tax amount if detected")
    
    # Metadata
    overall_confidence: float = Field(0.0, ge=0, le=1, description="Overall parsing confidence")
    extraction_notes: List[str] = Field(default_factory=list, description="Notes about extraction process")


class ReceiptProcessingResponse(BaseModel):
    """Complete response for receipt processing."""
    # File information
    filename: str = Field(..., description="Original filename")
    file_path: str = Field(..., description="Stored file path")
    file_size: int = Field(..., description="File size in bytes")
    
    # OCR results
    extraction_result: ReceiptExtractionResult
    
    # Parsed data
    parsed_data: ParsedReceiptData
    
    # Pre-filled expense form data
    suggested_expense: Dict[str, Any] = Field(..., description="Pre-filled expense form data")
    
    # Processing metadata
    processing_success: bool = Field(..., description="Whether processing was successful")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")


class ReceiptValidationError(BaseModel):
    """Error response for invalid receipt uploads."""
    error_type: str = Field(..., description="Type of validation error")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class ReceiptProcessingLog(BaseModel):
    """Log entry for receipt processing operations."""
    user_id: str = Field(..., description="User who uploaded the receipt")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    processing_time: float = Field(..., description="Total processing time")
    ocr_confidence: float = Field(..., description="OCR confidence score")
    parsing_confidence: float = Field(..., description="Overall parsing confidence")
    extracted_amount: Optional[float] = Field(None, description="Extracted amount")
    extracted_vendor: Optional[str] = Field(None, description="Extracted vendor")
    success: bool = Field(..., description="Whether processing was successful")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    timestamp: str = Field(..., description="Processing timestamp")
