# Multi-Currency Support Implementation

## Overview

This implementation adds comprehensive multi-currency support to the expense tracker application, allowing users to:

- **Record expenses in different currencies** (ISO 4217 format)
- **Set a personal base currency** for unified reporting
- **Automatic currency conversion** using live exchange rates
- **View all amounts in base currency** for consistent analysis

## Features Implemented

### 1. **Currency Field in Expenses**
- Added `currency` field to `Expense` model (ISO 4217 3-letter codes)
- Default currency: USD
- Supports all major world currencies

### 2. **User Base Currency**
- Added optional `base_currency` field to `User` model
- Users can set their preferred currency for reporting
- All calculations and displays use this base currency

### 3. **Exchange Rate Management**
- **`CurrencyRate` model** stores daily exchange rates with caching
- **Automatic rate fetching** from ExchangeRate-API (free service)
- **24-hour caching** to minimize API calls and improve performance
- **Fallback mechanisms** for missing rates (via EUR as intermediate)

### 4. **Currency Service**
- **`CurrencyService`** handles all currency operations:
  - Fetches latest rates from external API
  - Caches rates in database
  - Converts amounts between currencies
  - Provides common currency lists

### 5. **API Enhancements**
- **Expense API** now returns expenses with converted base amounts
- **Currency API** endpoint to get available currencies and rates
- **Conversion endpoint** for real-time currency conversion
- **Automatic rate updates** ensure data freshness

### 6. **UI Updates**
- **Currency selection dropdown** in expense creation form
- **Multi-currency expense table** showing original and base amounts
- **Dashboard** displays all amounts in user's base currency
- **Currency symbols** for better UX (€, £, ¥, etc.)

## Technical Implementation

### Database Schema Changes

```sql
-- Expenses table
ALTER TABLE expenses ADD COLUMN currency VARCHAR(3) DEFAULT 'USD';

-- Users table  
ALTER TABLE users ADD COLUMN base_currency VARCHAR(3) DEFAULT 'USD';

-- New currency_rates table
CREATE TABLE currency_rates (
    id VARCHAR(36) PRIMARY KEY,
    base_currency VARCHAR(3) NOT NULL,
    target_currency VARCHAR(3) NOT NULL,
    rate FLOAT NOT NULL,
    date DATETIME NOT NULL,
    source VARCHAR(50) DEFAULT 'ExchangeRate-API',
    INDEX idx_currency_date (base_currency, target_currency, date),
    INDEX idx_date_currencies (date, base_currency, target_currency)
);
```

### Key API Endpoints

```bash
# Get available currencies and rates
GET /currencies/

# Convert between currencies
POST /currencies/convert
{
    "amount": 100,
    "from_currency": "EUR", 
    "to_currency": "USD"
}

# Create expense with currency
POST /expenses/
{
    "title": "Lunch in Paris",
    "amount": 25.50,
    "currency": "EUR",
    "date": "2024-01-15",
    "category": "Food"
}
```

### Exchange Rate Provider

- **Service**: ExchangeRate-API (https://exchangerate-api.com/)
- **Free tier**: 1,500 requests/month
- **Base currency**: EUR (most rates available)
- **Update frequency**: Daily (cached for 24 hours)
- **Fallback**: Cross-rate calculation via EUR

## Migration Instructions

### 1. **Install Dependencies**
```bash
pip install httpx
```

### 2. **Run Migration Script**
```bash
python migration_add_currency_support.py
```

### 3. **Start Application**
```bash
python run.py
```

## Usage Examples

### Adding Multi-Currency Expenses

1. **Select currency** from dropdown when creating expense
2. **Amount stored** in original currency
3. **Automatic conversion** to user's base currency
4. **Dashboard shows** all amounts in base currency for consistency

### Currency Conversion

- **Real-time rates** fetched from external API
- **Cached daily** to improve performance
- **Budget comparisons** use converted amounts
- **Charts and reports** show unified currency data

### Supported Currencies

- USD 🇺🇸, EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵
- AUD 🇦🇺, CAD 🇨🇦, CHF 🇨🇭, CNY 🇨🇳  
- SEK 🇸🇪, NOK 🇳🇴, INR 🇮🇳, KRW 🇰🇷
- And many more...

## Benefits

1. **🌍 Global Usage**: Support for international users
2. **📊 Unified Reporting**: All data in consistent base currency  
3. **⚡ Performance**: Smart caching reduces API calls
4. **🔄 Real-time**: Up-to-date exchange rates
5. **🛡️ Reliability**: Fallback mechanisms for missing rates
6. **💰 Cost-effective**: Free API tier for most usage

## Future Enhancements

- **Historical rates** for accurate past conversions
- **Multiple rate providers** for redundancy
- **Currency trend charts** 
- **Rate alerts** for significant changes
- **Offline fallback** rates for reliability

---

The multi-currency foundation is now complete and ready for production use! 🎉
