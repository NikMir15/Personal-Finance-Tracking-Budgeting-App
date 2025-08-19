import re
import os
import cv2
import time
import logging
from datetime import datetime, date
from typing import Optional, List, Tuple, Dict, Any
from pathlib import Path
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReceiptProcessor:
    """Service for processing receipt images and extracting expense data."""
    
    # Common vendor patterns (case-insensitive)
    VENDOR_PATTERNS = [
        r'(?:store|shop|market|restaurant|cafe|coffee|pizza|burger|gas|fuel|pharmacy|hotel)',
        r'(?:walmart|target|amazon|starbucks|mcdonalds|subway|shell|exxon|cvs|walgreens)',
        r'(?:grocery|food|dining|retail|service)',
    ]
    
    # Amount patterns
    AMOUNT_PATTERNS = [
        r'(?:total|amount|due|pay|charge)[:\s]*\$?(\d+\.?\d{0,2})',
        r'\$(\d+\.\d{2})',
        r'(\d+\.\d{2})\s*(?:usd|dollars?)',
        r'(?:^|\s)(\d{1,4}\.\d{2})(?:\s|$)',
    ]
    
    # Date patterns
    DATE_PATTERNS = [
        r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        r'(\d{2,4}[-/]\d{1,2}[-/]\d{1,2})',
        r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2}),?\s+(\d{2,4})',
        r'(\d{1,2})\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{2,4})',
    ]
    
    # Category keywords mapping
    CATEGORY_KEYWORDS = {
        'Food': ['restaurant', 'cafe', 'coffee', 'pizza', 'burger', 'food', 'dining', 'lunch', 'dinner', 'breakfast'],
        'Transport': ['gas', 'fuel', 'uber', 'lyft', 'taxi', 'parking', 'metro', 'bus', 'train'],
        'Shopping': ['walmart', 'target', 'amazon', 'store', 'shop', 'retail', 'clothing', 'electronics'],
        'Healthcare': ['pharmacy', 'cvs', 'walgreens', 'hospital', 'clinic', 'medical', 'health'],
        'Entertainment': ['movie', 'cinema', 'theater', 'game', 'entertainment', 'ticket'],
        'Bills': ['utility', 'electric', 'water', 'phone', 'internet', 'insurance'],
        'Other': []
    }
    
    @staticmethod
    def preprocess_image(image_path: str) -> np.ndarray:
        """Preprocess image for better OCR results."""
        try:
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                # Try with PIL if OpenCV fails
                pil_img = Image.open(image_path)
                img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply noise reduction
            denoised = cv2.medianBlur(gray, 3)
            
            # Enhance contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(denoised)
            
            # Apply threshold for better text detection
            _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            return thresh
            
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            # Fallback: return original image
            return cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    
    @staticmethod
    def extract_text_from_image(image_path: str) -> Tuple[str, float]:
        """Extract text from image using OCR."""
        try:
            start_time = time.time()
            
            # Preprocess image
            processed_img = ReceiptProcessor.preprocess_image(image_path)
            
            # Configure Tesseract
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,/$:-/\n '
            
            # Extract text
            text = pytesseract.image_to_string(processed_img, config=custom_config)
            
            # Get confidence score
            data = pytesseract.image_to_data(processed_img, output_type=pytesseract.Output.DICT)
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            processing_time = time.time() - start_time
            
            logger.info(f"OCR completed in {processing_time:.2f}s with confidence {avg_confidence:.1f}%")
            
            return text.strip(), avg_confidence / 100.0
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return "", 0.0
    
    @staticmethod
    def extract_amount(text: str) -> Tuple[Optional[float], float]:
        """Extract monetary amount from text."""
        try:
            amounts = []
            confidences = []
            
            for pattern in ReceiptProcessor.AMOUNT_PATTERNS:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    try:
                        amount_str = match.group(1)
                        amount = float(amount_str)
                        if 0.01 <= amount <= 10000:  # Reasonable range
                            amounts.append(amount)
                            # Higher confidence for patterns with keywords
                            conf = 0.9 if 'total' in pattern.lower() else 0.7
                            confidences.append(conf)
                    except (ValueError, IndexError):
                        continue
            
            if amounts:
                # Return the most likely amount (highest value, assuming it's the total)
                max_amount = max(amounts)
                max_idx = amounts.index(max_amount)
                return max_amount, confidences[max_idx]
            
            return None, 0.0
            
        except Exception as e:
            logger.error(f"Amount extraction failed: {e}")
            return None, 0.0
    
    @staticmethod
    def extract_date(text: str) -> Tuple[Optional[str], float]:
        """Extract date from text."""
        try:
            dates = []
            confidences = []
            
            for pattern in ReceiptProcessor.DATE_PATTERNS:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    try:
                        date_str = match.group(1) if match.groups() else match.group(0)
                        
                        # Try to parse the date
                        parsed_date = ReceiptProcessor._parse_date_string(date_str)
                        if parsed_date:
                            dates.append(parsed_date.strftime('%Y-%m-%d'))
                            confidences.append(0.8)
                    except Exception:
                        continue
            
            if dates:
                # Return the most recent date (likely to be the receipt date)
                return max(dates), max(confidences)
            
            return None, 0.0
            
        except Exception as e:
            logger.error(f"Date extraction failed: {e}")
            return None, 0.0
    
    @staticmethod
    def _parse_date_string(date_str: str) -> Optional[date]:
        """Parse various date string formats."""
        date_formats = [
            '%m/%d/%Y', '%m-%d-%Y', '%m/%d/%y', '%m-%d-%y',
            '%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d-%m-%y',
            '%Y/%m/%d', '%Y-%m-%d',
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None
    
    @staticmethod
    def extract_vendor(text: str) -> Tuple[Optional[str], float]:
        """Extract vendor/merchant name from text."""
        try:
            lines = text.split('\n')
            vendors = []
            confidences = []
            
            # Look for vendor patterns in the first few lines (header area)
            for i, line in enumerate(lines[:5]):
                line = line.strip()
                if len(line) < 3 or len(line) > 50:
                    continue
                
                # Check against known vendor patterns
                for pattern in ReceiptProcessor.VENDOR_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        vendors.append(line)
                        confidences.append(0.9)
                        break
                else:
                    # If no pattern matches, consider lines with proper capitalization
                    if line.istitle() and not re.search(r'\d', line):
                        vendors.append(line)
                        confidences.append(0.6)
            
            if vendors:
                # Return the first (topmost) vendor found
                return vendors[0], confidences[0]
            
            # Fallback: return the first non-empty line
            for line in lines[:3]:
                line = line.strip()
                if 3 <= len(line) <= 50 and not re.search(r'^\d+$', line):
                    return line, 0.3
            
            return None, 0.0
            
        except Exception as e:
            logger.error(f"Vendor extraction failed: {e}")
            return None, 0.0
    
    @staticmethod
    def suggest_category(text: str, vendor: Optional[str] = None) -> Tuple[Optional[str], float]:
        """Suggest expense category based on text content."""
        try:
            search_text = f"{text} {vendor or ''}".lower()
            
            category_scores = {}
            
            for category, keywords in ReceiptProcessor.CATEGORY_KEYWORDS.items():
                if category == 'Other':
                    continue
                    
                score = 0
                for keyword in keywords:
                    if keyword.lower() in search_text:
                        score += 1
                
                if score > 0:
                    category_scores[category] = score
            
            if category_scores:
                best_category = max(category_scores.items(), key=lambda x: x[1])
                confidence = min(0.9, best_category[1] * 0.3)
                return best_category[0], confidence
            
            return 'Other', 0.2
            
        except Exception as e:
            logger.error(f"Category suggestion failed: {e}")
            return 'Other', 0.1
    
    @staticmethod
    def process_receipt(image_path: str) -> Dict[str, Any]:
        """Main method to process a receipt image and extract all data."""
        try:
            start_time = time.time()
            
            # Extract text using OCR
            raw_text, ocr_confidence = ReceiptProcessor.extract_text_from_image(image_path)
            
            if not raw_text:
                return {
                    'success': False,
                    'error': 'No text could be extracted from the image',
                    'confidence': 0.0
                }
            
            # Extract structured data
            amount, amount_conf = ReceiptProcessor.extract_amount(raw_text)
            date_str, date_conf = ReceiptProcessor.extract_date(raw_text)
            vendor, vendor_conf = ReceiptProcessor.extract_vendor(raw_text)
            category, category_conf = ReceiptProcessor.suggest_category(raw_text, vendor)
            
            # Calculate overall confidence
            confidences = [ocr_confidence, amount_conf, date_conf, vendor_conf]
            overall_confidence = sum(c for c in confidences if c > 0) / len([c for c in confidences if c > 0]) if any(confidences) else 0.0
            
            processing_time = time.time() - start_time
            
            # Prepare suggested expense data
            suggested_expense = {
                'title': vendor or 'Receipt Expense',
                'amount': amount or 0.0,
                'currency': 'USD',
                'date': date_str or datetime.now().strftime('%Y-%m-%d'),
                'category': category or 'Other'
            }
            
            extraction_notes = []
            if ocr_confidence < 0.7:
                extraction_notes.append("Low OCR confidence - manual review recommended")
            if not amount:
                extraction_notes.append("Amount not detected - please enter manually")
            if not date_str:
                extraction_notes.append("Date not detected - using current date")
            
            return {
                'success': True,
                'raw_text': raw_text,
                'ocr_confidence': ocr_confidence,
                'processing_time': processing_time,
                'extracted_data': {
                    'amount': amount,
                    'amount_confidence': amount_conf,
                    'date': date_str,
                    'date_confidence': date_conf,
                    'vendor': vendor,
                    'vendor_confidence': vendor_conf,
                    'category': category,
                    'category_confidence': category_conf,
                    'overall_confidence': overall_confidence,
                    'extraction_notes': extraction_notes
                },
                'suggested_expense': suggested_expense
            }
            
        except Exception as e:
            logger.error(f"Receipt processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'confidence': 0.0
            }
