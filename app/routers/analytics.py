from datetime import datetime, timedelta
from typing import List, Optional
import csv
import io
from calendar import monthrange

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_, desc

from app.dependencies.jwt_auth import get_current_user
from app.dependencies.db import get_db
from app.schemas.analytics import (
    AnalyticsDashboard, DashboardSummary, MonthlySpendItem, 
    CategoryBreakdownItem, BudgetUtilizationItem, TopExpenseItem,
    ExpenseExportResponse
)
from app.schemas.common import ErrorResponse
from app.models.expense import Expense as ExpenseModel
from app.models.budget import Budget as BudgetModel
from app.models.user import User as UserModel
from app.services.currency_service import CurrencyService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/dashboard",
    response_model=AnalyticsDashboard,
    summary="Get analytics dashboard data",
    description="Get comprehensive analytics data including monthly spend, category breakdown, and budget utilization.",
    responses={
        200: {"description": "Analytics data retrieved successfully"},
        401: {"model": ErrorResponse, "description": "Authentication required"}
    }
)
async def get_analytics_dashboard(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive analytics dashboard data."""
    
    # Ensure exchange rates are up to date
    await CurrencyService.ensure_rates_updated(db)
    
    # Get user's base currency
    user = db.query(UserModel).filter(UserModel.username == current_user).first()
    user_base_currency = user.base_currency if user and user.base_currency else "USD"
    
    # Get all user expenses
    expenses = db.query(ExpenseModel).filter(ExpenseModel.user_id == current_user).all()
    budgets = db.query(BudgetModel).filter(BudgetModel.user_id == current_user).all()
    
    # Convert all expenses to base currency
    converted_expenses = []
    for exp in expenses:
        base_amount = CurrencyService.convert_amount(
            db, exp.amount, exp.currency, user_base_currency
        )
        if base_amount is None:
            base_amount = exp.amount  # Fallback
        
        converted_expenses.append({
            'expense': exp,
            'base_amount': base_amount
        })
    
    # Calculate summary data
    summary = await _calculate_dashboard_summary(converted_expenses, budgets, user_base_currency)
    
    # Calculate monthly spend (last 6 months)
    monthly_spend = _calculate_monthly_spend(converted_expenses, user_base_currency)
    
    # Calculate category breakdown
    category_breakdown = _calculate_category_breakdown(converted_expenses, user_base_currency)
    
    # Calculate budget utilization
    budget_utilization = _calculate_budget_utilization(converted_expenses, budgets, user_base_currency)
    
    # Get top expenses this month
    top_expenses = _get_top_expenses_this_month(converted_expenses, user_base_currency)
    
    return AnalyticsDashboard(
        summary=summary,
        monthly_spend=monthly_spend,
        category_breakdown=category_breakdown,
        budget_utilization=budget_utilization,
        top_expenses=top_expenses
    )


@router.get(
    "/export/csv",
    summary="Export expenses to CSV",
    description="Export all user expenses to CSV format with currency conversion.",
    responses={
        200: {"description": "CSV file generated successfully"},
        401: {"model": ErrorResponse, "description": "Authentication required"}
    }
)
async def export_expenses_csv(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export expenses to CSV format."""
    
    # Ensure exchange rates are up to date
    await CurrencyService.ensure_rates_updated(db)
    
    # Get user's base currency
    user = db.query(UserModel).filter(UserModel.username == current_user).first()
    user_base_currency = user.base_currency if user and user.base_currency else "USD"
    
    # Build query
    query = db.query(ExpenseModel).filter(ExpenseModel.user_id == current_user)
    
    # Apply date filters if provided
    date_range_str = "All dates"
    if start_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        query = query.filter(ExpenseModel.date >= start_dt)
        date_range_str = f"From {start_date}"
        
    if end_date:
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        query = query.filter(ExpenseModel.date <= end_dt)
        if start_date:
            date_range_str = f"{start_date} to {end_date}"
        else:
            date_range_str = f"Until {end_date}"
    
    expenses = query.order_by(desc(ExpenseModel.date)).all()
    
    # Create CSV content
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Date', 'Title', 'Amount', 'Currency', 
        f'Base Amount ({user_base_currency})', 'Category'
    ])
    
    # Write data
    for expense in expenses:
        base_amount = CurrencyService.convert_amount(
            db, expense.amount, expense.currency, user_base_currency
        )
        if base_amount is None:
            base_amount = expense.amount
            
        writer.writerow([
            expense.date.strftime('%Y-%m-%d'),
            expense.title,
            f"{expense.amount:.2f}",
            expense.currency,
            f"{base_amount:.2f}",
            expense.category
        ])
    
    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"expenses_export_{timestamp}.csv"
    
    # Prepare response
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# Helper functions

async def _calculate_dashboard_summary(converted_expenses, budgets, base_currency):
    """Calculate dashboard summary statistics."""
    now = datetime.now()
    current_month = now.month
    current_year = now.year
    
    # Filter current month expenses
    current_month_expenses = [
        ce for ce in converted_expenses 
        if ce['expense'].date.month == current_month and ce['expense'].date.year == current_year
    ]
    
    # Filter previous month expenses
    prev_month = current_month - 1 if current_month > 1 else 12
    prev_year = current_year if current_month > 1 else current_year - 1
    prev_month_expenses = [
        ce for ce in converted_expenses 
        if ce['expense'].date.month == prev_month and ce['expense'].date.year == prev_year
    ]
    
    # Calculate totals
    current_month_spend = sum(ce['base_amount'] for ce in current_month_expenses)
    previous_month_spend = sum(ce['base_amount'] for ce in prev_month_expenses)
    
    # Calculate month-over-month change
    mom_change = None
    if previous_month_spend > 0:
        mom_change = ((current_month_spend - previous_month_spend) / previous_month_spend) * 100
    
    # Budget calculations
    total_budget_amount = sum(budget.limit for budget in budgets)
    
    # Calculate budget usage
    total_budget_used = 0
    budgets_exceeded = 0
    
    for budget in budgets:
        category_expenses = [
            ce for ce in current_month_expenses 
            if ce['expense'].category == budget.category
        ]
        category_spent = sum(ce['base_amount'] for ce in category_expenses)
        total_budget_used += min(category_spent, budget.limit)
        
        if category_spent > budget.limit:
            budgets_exceeded += 1
    
    # Last expense date
    last_expense_date = None
    if converted_expenses:
        latest_expense = max(converted_expenses, key=lambda ce: ce['expense'].date)
        last_expense_date = latest_expense['expense'].date.strftime('%Y-%m-%d')
    
    return DashboardSummary(
        current_month_spend=current_month_spend,
        current_month_expenses=len(current_month_expenses),
        previous_month_spend=previous_month_spend,
        month_over_month_change=mom_change,
        total_budgets=len(budgets),
        budgets_exceeded=budgets_exceeded,
        total_budget_amount=total_budget_amount,
        total_budget_used=total_budget_used,
        total_expenses=len(converted_expenses),
        base_currency=base_currency,
        last_expense_date=last_expense_date
    )


def _calculate_monthly_spend(converted_expenses, base_currency):
    """Calculate monthly spending for last 6 months."""
    monthly_data = {}
    
    for ce in converted_expenses:
        month_key = ce['expense'].date.strftime('%Y-%m')
        if month_key not in monthly_data:
            monthly_data[month_key] = {
                'total_amount': 0,
                'expense_count': 0
            }
        monthly_data[month_key]['total_amount'] += ce['base_amount']
        monthly_data[month_key]['expense_count'] += 1
    
    # Get last 6 months
    result = []
    for i in range(5, -1, -1):
        date = datetime.now() - timedelta(days=30 * i)
        month_key = date.strftime('%Y-%m')
        month_name = date.strftime('%B %Y')
        
        data = monthly_data.get(month_key, {'total_amount': 0, 'expense_count': 0})
        
        result.append(MonthlySpendItem(
            month=month_key,
            month_name=month_name,
            total_amount=data['total_amount'],
            expense_count=data['expense_count'],
            base_currency=base_currency
        ))
    
    return result


def _calculate_category_breakdown(converted_expenses, base_currency):
    """Calculate category spending breakdown."""
    category_data = {}
    total_amount = sum(ce['base_amount'] for ce in converted_expenses)
    
    for ce in converted_expenses:
        category = ce['expense'].category
        if category not in category_data:
            category_data[category] = {
                'total_amount': 0,
                'expense_count': 0
            }
        category_data[category]['total_amount'] += ce['base_amount']
        category_data[category]['expense_count'] += 1
    
    # Sort by total amount descending
    result = []
    for category, data in sorted(category_data.items(), key=lambda x: x[1]['total_amount'], reverse=True):
        percentage = (data['total_amount'] / total_amount * 100) if total_amount > 0 else 0
        avg_amount = data['total_amount'] / data['expense_count'] if data['expense_count'] > 0 else 0
        
        result.append(CategoryBreakdownItem(
            category=category,
            total_amount=data['total_amount'],
            expense_count=data['expense_count'],
            percentage=percentage,
            avg_amount=avg_amount
        ))
    
    return result


def _calculate_budget_utilization(converted_expenses, budgets, base_currency):
    """Calculate budget utilization for current month."""
    now = datetime.now()
    current_month = now.month
    current_year = now.year
    
    # Filter current month expenses
    current_month_expenses = [
        ce for ce in converted_expenses 
        if ce['expense'].date.month == current_month and ce['expense'].date.year == current_year
    ]
    
    # Days left in current month
    _, days_in_month = monthrange(current_year, current_month)
    days_left = days_in_month - now.day
    
    result = []
    for budget in budgets:
        # Calculate spent amount for this category
        category_expenses = [
            ce for ce in current_month_expenses 
            if ce['expense'].category == budget.category
        ]
        spent_amount = sum(ce['base_amount'] for ce in category_expenses)
        
        remaining_amount = budget.limit - spent_amount
        utilization_percentage = (spent_amount / budget.limit * 100) if budget.limit > 0 else 0
        
        # Determine status
        if utilization_percentage >= 100:
            status = "exceeded"
        elif utilization_percentage >= 80:
            status = "warning"
        else:
            status = "safe"
        
        result.append(BudgetUtilizationItem(
            category=budget.category,
            budget_limit=budget.limit,
            spent_amount=spent_amount,
            remaining_amount=remaining_amount,
            utilization_percentage=utilization_percentage,
            status=status,
            days_left_in_month=days_left
        ))
    
    # Sort by utilization percentage descending
    result.sort(key=lambda x: x.utilization_percentage, reverse=True)
    return result


def _get_top_expenses_this_month(converted_expenses, base_currency):
    """Get top 5 expenses for current month."""
    now = datetime.now()
    current_month = now.month
    current_year = now.year
    
    # Filter current month expenses
    current_month_expenses = [
        ce for ce in converted_expenses 
        if ce['expense'].date.month == current_month and ce['expense'].date.year == current_year
    ]
    
    # Sort by base amount descending and take top 5
    top_expenses = sorted(current_month_expenses, key=lambda ce: ce['base_amount'], reverse=True)[:5]
    
    result = []
    for ce in top_expenses:
        result.append(TopExpenseItem(
            title=ce['expense'].title,
            amount=ce['expense'].amount,
            currency=ce['expense'].currency,
            base_amount=ce['base_amount'],
            category=ce['expense'].category,
            date=ce['expense'].date.strftime('%Y-%m-%d')
        ))
    
    return result
