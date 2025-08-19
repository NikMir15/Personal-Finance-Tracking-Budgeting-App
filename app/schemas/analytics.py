from datetime import date, datetime
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class MonthlySpendItem(BaseModel):
    """Monthly spending summary item."""
    month: str = Field(..., description="Month in YYYY-MM format")
    month_name: str = Field(..., description="Human readable month name")
    total_amount: float = Field(..., description="Total amount spent in base currency")
    expense_count: int = Field(..., description="Number of expenses")
    base_currency: str = Field(..., description="User's base currency")


class CategoryBreakdownItem(BaseModel):
    """Category spending breakdown item."""
    category: str = Field(..., description="Expense category")
    total_amount: float = Field(..., description="Total amount in base currency")
    expense_count: int = Field(..., description="Number of expenses")
    percentage: float = Field(..., description="Percentage of total spending")
    avg_amount: float = Field(..., description="Average expense amount")


class BudgetUtilizationItem(BaseModel):
    """Budget utilization item."""
    category: str = Field(..., description="Budget category")
    budget_limit: float = Field(..., description="Budget limit")
    spent_amount: float = Field(..., description="Amount spent in base currency")
    remaining_amount: float = Field(..., description="Remaining budget")
    utilization_percentage: float = Field(..., description="Percentage of budget used")
    status: str = Field(..., description="Budget status: safe, warning, exceeded")
    days_left_in_month: int = Field(..., description="Days remaining in current month")


class TopExpenseItem(BaseModel):
    """Top expense item."""
    title: str = Field(..., description="Expense title")
    amount: float = Field(..., description="Original amount")
    currency: str = Field(..., description="Original currency")
    base_amount: float = Field(..., description="Amount in base currency")
    category: str = Field(..., description="Expense category")
    date: str = Field(..., description="Expense date")


class DashboardSummary(BaseModel):
    """Dashboard summary data."""
    # Current month summary
    current_month_spend: float = Field(..., description="Current month total spending")
    current_month_expenses: int = Field(..., description="Number of expenses this month")
    previous_month_spend: float = Field(..., description="Previous month total spending")
    month_over_month_change: Optional[float] = Field(None, description="Month over month change percentage")
    
    # Budget summary
    total_budgets: int = Field(..., description="Number of active budgets")
    budgets_exceeded: int = Field(..., description="Number of budgets exceeded")
    total_budget_amount: float = Field(..., description="Total budget amount")
    total_budget_used: float = Field(..., description="Total amount used across all budgets")
    
    # General stats
    total_expenses: int = Field(..., description="Total number of expenses")
    base_currency: str = Field(..., description="User's base currency")
    last_expense_date: Optional[str] = Field(None, description="Date of last expense")


class AnalyticsDashboard(BaseModel):
    """Complete analytics dashboard data."""
    summary: DashboardSummary
    monthly_spend: List[MonthlySpendItem]
    category_breakdown: List[CategoryBreakdownItem]
    budget_utilization: List[BudgetUtilizationItem]
    top_expenses: List[TopExpenseItem]


class ExpenseExportItem(BaseModel):
    """Expense item for CSV export."""
    date: str
    title: str
    amount: float
    currency: str
    base_amount: Optional[float] = None
    base_currency: Optional[str] = None
    category: str
    
    
class ExpenseExportResponse(BaseModel):
    """Response for expense export."""
    filename: str
    total_records: int
    date_range: str
    base_currency: str
