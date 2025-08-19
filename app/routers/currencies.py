from typing import Dict, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies.jwt_auth import get_current_user
from app.dependencies.db import get_db
from app.schemas.currency import CurrencyListResponse, CurrencyInfo
from app.schemas.common import ErrorResponse
from app.services.currency_service import CurrencyService

router = APIRouter(prefix="/currencies", tags=["Currencies"])

# Currency information with symbols
CURRENCY_INFO = {
    'USD': CurrencyInfo(code='USD', name='US Dollar', symbol='$'),
    'EUR': CurrencyInfo(code='EUR', name='Euro', symbol='€'),
    'GBP': CurrencyInfo(code='GBP', name='British Pound', symbol='£'),
    'JPY': CurrencyInfo(code='JPY', name='Japanese Yen', symbol='¥'),
    'AUD': CurrencyInfo(code='AUD', name='Australian Dollar', symbol='A$'),
    'CAD': CurrencyInfo(code='CAD', name='Canadian Dollar', symbol='C$'),
    'CHF': CurrencyInfo(code='CHF', name='Swiss Franc', symbol='CHF'),
    'CNY': CurrencyInfo(code='CNY', name='Chinese Yuan', symbol='¥'),
    'SEK': CurrencyInfo(code='SEK', name='Swedish Krona', symbol='kr'),
    'NZD': CurrencyInfo(code='NZD', name='New Zealand Dollar', symbol='NZ$'),
    'HKD': CurrencyInfo(code='HKD', name='Hong Kong Dollar', symbol='HK$'),
    'SGD': CurrencyInfo(code='SGD', name='Singapore Dollar', symbol='S$'),
    'NOK': CurrencyInfo(code='NOK', name='Norwegian Krone', symbol='kr'),
    'MXN': CurrencyInfo(code='MXN', name='Mexican Peso', symbol='$'),
    'INR': CurrencyInfo(code='INR', name='Indian Rupee', symbol='₹'),
    'KRW': CurrencyInfo(code='KRW', name='South Korean Won', symbol='₩'),
}


@router.get(
    "/",
    response_model=CurrencyListResponse,
    summary="Get available currencies",
    description="Get list of supported currencies with current exchange rates relative to USD.",
    responses={
        200: {"description": "Currencies and rates retrieved successfully"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        500: {"model": ErrorResponse, "description": "Failed to fetch exchange rates"}
    }
)
async def get_currencies(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get available currencies with current exchange rates."""
    # Ensure rates are updated
    await CurrencyService.ensure_rates_updated(db)
    
    # Get rates relative to USD (most common base)
    rates = {}
    for currency_code in CurrencyService.COMMON_CURRENCIES:
        if currency_code == 'USD':
            rates[currency_code] = 1.0
        else:
            rate = CurrencyService.get_exchange_rate(db, 'USD', currency_code)
            if rate is not None:
                rates[currency_code] = rate
            else:
                rates[currency_code] = 1.0  # Fallback
    
    # Get currencies info
    currencies = [
        CURRENCY_INFO.get(code, CurrencyInfo(code=code, name=code, symbol=code))
        for code in CurrencyService.COMMON_CURRENCIES
    ]
    
    return CurrencyListResponse(
        currencies=currencies,
        rates=rates,
        last_updated=datetime.utcnow()
    )


@router.post(
    "/convert",
    summary="Convert amount between currencies", 
    description="Convert an amount from one currency to another using current exchange rates.",
    responses={
        200: {"description": "Conversion successful"},
        400: {"model": ErrorResponse, "description": "Invalid currency codes or amount"},
        401: {"model": ErrorResponse, "description": "Authentication required"}
    }
)
async def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Convert amount between currencies."""
    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_AMOUNT", "message": "Amount must be positive"}
        )
    
    if len(from_currency) != 3 or len(to_currency) != 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_CURRENCY", "message": "Currency codes must be 3 characters"}
        )
    
    # Ensure rates are updated
    await CurrencyService.ensure_rates_updated(db)
    
    converted_amount = CurrencyService.convert_amount(
        db, amount, from_currency.upper(), to_currency.upper()
    )
    
    if converted_amount is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "CONVERSION_FAILED", "message": f"Cannot convert from {from_currency} to {to_currency}"}
        )
    
    rate = CurrencyService.get_exchange_rate(db, from_currency.upper(), to_currency.upper())
    
    return {
        "original_amount": amount,
        "from_currency": from_currency.upper(),
        "converted_amount": round(converted_amount, 2),
        "to_currency": to_currency.upper(),
        "exchange_rate": rate,
        "timestamp": datetime.utcnow()
    }
