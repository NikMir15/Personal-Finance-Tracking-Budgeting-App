import httpx
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.models.currency_rate import CurrencyRate
from app.dependencies.db import get_db


class CurrencyService:
    """Service for handling currency conversions and exchange rate fetching."""
    
    # Common currencies for the dropdown
    COMMON_CURRENCIES = [
        'USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'CNY', 
        'SEK', 'NZD', 'HKD', 'SGD', 'NOK', 'MXN', 'INR', 'KRW'
    ]
    
    # ECB provides EUR-based rates for free
    ECB_API_URL = "https://api.exchangerate-api.com/v4/latest/EUR"
    
    @staticmethod
    async def fetch_latest_rates(base_currency: str = "EUR") -> Dict[str, float]:
        """Fetch latest exchange rates from ECB API."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"https://api.exchangerate-api.com/v4/latest/{base_currency}")
                response.raise_for_status()
                data = response.json()
                return data.get("rates", {})
        except Exception as e:
            print(f"Error fetching exchange rates: {e}")
            return {}
    
    @staticmethod
    async def update_rates_cache(db: Session, base_currency: str = "EUR") -> bool:
        """Update the currency rates cache with latest data."""
        try:
            rates = await CurrencyService.fetch_latest_rates(base_currency)
            if not rates:
                return False
            
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Delete old rates for today to avoid duplicates
            db.query(CurrencyRate).filter(
                and_(
                    CurrencyRate.base_currency == base_currency,
                    CurrencyRate.date >= today
                )
            ).delete()
            
            # Add new rates
            for target_currency, rate in rates.items():
                if target_currency != base_currency:  # Don't store base to itself
                    currency_rate = CurrencyRate(
                        base_currency=base_currency,
                        target_currency=target_currency,
                        rate=rate,
                        date=today,
                        source="ExchangeRate-API"
                    )
                    db.add(currency_rate)
            
            # Add base currency to itself (rate = 1.0)
            base_rate = CurrencyRate(
                base_currency=base_currency,
                target_currency=base_currency,
                rate=1.0,
                date=today,
                source="ExchangeRate-API"
            )
            db.add(base_rate)
            
            db.commit()
            print(f"Updated {len(rates)} exchange rates for {base_currency}")
            return True
            
        except Exception as e:
            print(f"Error updating rates cache: {e}")
            db.rollback()
            return False
    
    @staticmethod
    def get_exchange_rate(db: Session, from_currency: str, to_currency: str, 
                         date: Optional[datetime] = None) -> Optional[float]:
        """Get exchange rate between two currencies."""
        if from_currency == to_currency:
            return 1.0
        
        if date is None:
            date = datetime.utcnow()
        
        # Look for direct rate
        rate_record = db.query(CurrencyRate).filter(
            and_(
                CurrencyRate.base_currency == from_currency,
                CurrencyRate.target_currency == to_currency,
                CurrencyRate.date <= date
            )
        ).order_by(desc(CurrencyRate.date)).first()
        
        if rate_record:
            return rate_record.rate
        
        # Try reverse rate (1/rate)
        reverse_rate = db.query(CurrencyRate).filter(
            and_(
                CurrencyRate.base_currency == to_currency,
                CurrencyRate.target_currency == from_currency,
                CurrencyRate.date <= date
            )
        ).order_by(desc(CurrencyRate.date)).first()
        
        if reverse_rate and reverse_rate.rate != 0:
            return 1.0 / reverse_rate.rate
        
        # Try via EUR as intermediate currency
        eur_from = db.query(CurrencyRate).filter(
            and_(
                CurrencyRate.base_currency == "EUR",
                CurrencyRate.target_currency == from_currency,
                CurrencyRate.date <= date
            )
        ).order_by(desc(CurrencyRate.date)).first()
        
        eur_to = db.query(CurrencyRate).filter(
            and_(
                CurrencyRate.base_currency == "EUR",
                CurrencyRate.target_currency == to_currency,
                CurrencyRate.date <= date
            )
        ).order_by(desc(CurrencyRate.date)).first()
        
        if eur_from and eur_to and eur_from.rate != 0:
            return eur_to.rate / eur_from.rate
        
        return None
    
    @staticmethod
    def convert_amount(db: Session, amount: float, from_currency: str, 
                      to_currency: str, date: Optional[datetime] = None) -> Optional[float]:
        """Convert amount from one currency to another."""
        try:
            rate = CurrencyService.get_exchange_rate(db, from_currency, to_currency, date)
            if rate is not None:
                return amount * rate
            return None
        except Exception as e:
            print(f"Warning: Currency conversion failed: {e}")
            # Return None to indicate conversion failed
            return None
    
    @staticmethod
    def should_update_rates(db: Session) -> bool:
        """Check if rates need to be updated (older than 24 hours)."""
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_rate = db.query(CurrencyRate).filter(
            CurrencyRate.date > yesterday
        ).first()
        return recent_rate is None
    
    @staticmethod
    async def ensure_rates_updated(db: Session) -> bool:
        """Ensure exchange rates are up to date."""
        try:
            if CurrencyService.should_update_rates(db):
                return await CurrencyService.update_rates_cache(db)
            return True
        except Exception as e:
            print(f"Warning: Failed to update exchange rates: {e}")
            # Continue without rates update - don't break the application
            return False
