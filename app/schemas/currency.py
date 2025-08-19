from datetime import datetime
from typing import List, Dict
from pydantic import BaseModel, Field


class CurrencyRate(BaseModel):
    """Schema for currency exchange rate."""
    base_currency: str = Field(..., min_length=3, max_length=3, description="Base currency code")
    target_currency: str = Field(..., min_length=3, max_length=3, description="Target currency code")
    rate: float = Field(..., gt=0, description="Exchange rate")
    date: datetime = Field(..., description="Rate date")
    source: str = Field(..., description="Rate provider")


class CurrencyInfo(BaseModel):
    """Schema for currency information."""
    code: str = Field(..., min_length=3, max_length=3, description="ISO 4217 currency code")
    name: str = Field(..., description="Currency name")
    symbol: str = Field(..., description="Currency symbol")


class CurrencyListResponse(BaseModel):
    """Response model for available currencies."""
    currencies: List[CurrencyInfo]
    rates: Dict[str, float]  # Current rates relative to USD or user's base currency
    last_updated: datetime
