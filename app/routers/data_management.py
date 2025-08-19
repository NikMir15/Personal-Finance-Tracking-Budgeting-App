"""
Data Management and Retention API endpoints.

This module provides endpoints for:
- User data export (GDPR compliance)
- User data deletion/purging (right to be forgotten)
- Data retention management
- Admin data cleanup utilities
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import zipfile
import io
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.database import get_db
from app.models.user import User
from app.models.expense import Expense
from app.models.budget import Budget
from app.dependencies.jwt_auth import get_current_user
from app.dependencies.admin import get_admin_user
from app.schemas.data_management import (
    DataExportRequest,
    DataExportResponse,
    DataPurgeRequest,
    DataPurgeResponse,
    DataRetentionStats,
    UserDataSummary
)

router = APIRouter(prefix="/data", tags=["data-management"])


@router.post("/export", response_model=DataExportResponse)
async def export_user_data(
    request: DataExportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export all user data in a machine-readable format.
    
    This endpoint supports GDPR Article 20 (Right to data portability).
    Users can export their complete data history.
    """
    try:
        # Collect user data
        user_data = {
            "user_profile": {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email,
                "full_name": current_user.full_name,
                "created_at": current_user.created_at.isoformat(),
                "is_active": current_user.is_active
            },
            "expenses": [],
            "budgets": [],
            "export_metadata": {
                "export_date": datetime.now().isoformat(),
                "format_version": "1.0",
                "includes": request.include_categories
            }
        }
        
        # Export expenses if requested
        if "expenses" in request.include_categories:
            expenses_query = db.query(Expense).filter(Expense.user_id == current_user.id)
            
            # Apply date filter if specified
            if request.date_from:
                expenses_query = expenses_query.filter(Expense.date >= request.date_from)
            if request.date_to:
                expenses_query = expenses_query.filter(Expense.date <= request.date_to)
            
            expenses = expenses_query.all()
            user_data["expenses"] = [
                {
                    "id": expense.id,
                    "amount": float(expense.amount),
                    "currency": expense.currency,
                    "description": expense.description,
                    "category": expense.category,
                    "date": expense.date.isoformat(),
                    "created_at": expense.created_at.isoformat()
                }
                for expense in expenses
            ]
        
        # Export budgets if requested
        if "budgets" in request.include_categories:
            budgets_query = db.query(Budget).filter(Budget.user_id == current_user.id)
            
            if request.date_from:
                budgets_query = budgets_query.filter(Budget.start_date >= request.date_from)
            if request.date_to:
                budgets_query = budgets_query.filter(Budget.end_date <= request.date_to)
            
            budgets = budgets_query.all()
            user_data["budgets"] = [
                {
                    "id": budget.id,
                    "category": budget.category,
                    "limit": float(budget.limit),
                    "start_date": budget.start_date.isoformat(),
                    "end_date": budget.end_date.isoformat(),
                    "created_at": budget.created_at.isoformat()
                }
                for budget in budgets
            ]
        
        # Generate export based on format
        if request.format == "json":
            export_content = json.dumps(user_data, indent=2)
            content_type = "application/json"
            filename = f"user_data_export_{current_user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        elif request.format == "csv":
            # For CSV, we'll create a ZIP file with separate CSV files
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # User profile CSV
                if user_data["user_profile"]:
                    profile_csv = "field,value\n"
                    for key, value in user_data["user_profile"].items():
                        profile_csv += f"{key},{value}\n"
                    zip_file.writestr("user_profile.csv", profile_csv)
                
                # Expenses CSV
                if user_data["expenses"]:
                    expenses_csv = "id,amount,currency,description,category,date,created_at\n"
                    for expense in user_data["expenses"]:
                        expenses_csv += f"{expense['id']},{expense['amount']},{expense['currency']},\"{expense['description']}\",{expense['category']},{expense['date']},{expense['created_at']}\n"
                    zip_file.writestr("expenses.csv", expenses_csv)
                
                # Budgets CSV
                if user_data["budgets"]:
                    budgets_csv = "id,category,limit,start_date,end_date,created_at\n"
                    for budget in user_data["budgets"]:
                        budgets_csv += f"{budget['id']},{budget['category']},{budget['limit']},{budget['start_date']},{budget['end_date']},{budget['created_at']}\n"
                    zip_file.writestr("budgets.csv", budgets_csv)
                
                # Add metadata
                metadata_json = json.dumps(user_data["export_metadata"], indent=2)
                zip_file.writestr("export_metadata.json", metadata_json)
            
            export_content = zip_buffer.getvalue()
            content_type = "application/zip"
            filename = f"user_data_export_{current_user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        
        return DataExportResponse(
            message="Data export generated successfully",
            filename=filename,
            content_type=content_type,
            size_bytes=len(export_content),
            records_count={
                "expenses": len(user_data.get("expenses", [])),
                "budgets": len(user_data.get("budgets", []))
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.delete("/purge", response_model=DataPurgeResponse)
async def purge_user_data(
    request: DataPurgeRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete user data according to retention policies or user request.
    
    This endpoint supports GDPR Article 17 (Right to erasure).
    Users can request complete data deletion or selective purging.
    """
    if not request.confirm_deletion:
        raise HTTPException(
            status_code=400,
            detail="Data deletion must be explicitly confirmed"
        )
    
    try:
        deleted_counts = {
            "expenses": 0,
            "budgets": 0,
            "user_account": 0
        }
        
        # Delete expenses if requested
        if "expenses" in request.categories or request.delete_all:
            expenses_query = db.query(Expense).filter(Expense.user_id == current_user.id)
            
            # Apply date filters for partial deletion
            if request.date_from and not request.delete_all:
                expenses_query = expenses_query.filter(Expense.date >= request.date_from)
            if request.date_to and not request.delete_all:
                expenses_query = expenses_query.filter(Expense.date <= request.date_to)
            
            deleted_counts["expenses"] = expenses_query.count()
            expenses_query.delete(synchronize_session=False)
        
        # Delete budgets if requested
        if "budgets" in request.categories or request.delete_all:
            budgets_query = db.query(Budget).filter(Budget.user_id == current_user.id)
            
            if request.date_from and not request.delete_all:
                budgets_query = budgets_query.filter(Budget.start_date >= request.date_from)
            if request.date_to and not request.delete_all:
                budgets_query = budgets_query.filter(Budget.end_date <= request.date_to)
            
            deleted_counts["budgets"] = budgets_query.count()
            budgets_query.delete(synchronize_session=False)
        
        # Delete user account if complete deletion requested
        if request.delete_all:
            # Mark user as inactive first (soft delete)
            current_user.is_active = False
            current_user.email = f"deleted_{current_user.id}@deleted.local"
            current_user.username = f"deleted_user_{current_user.id}"
            
            # Schedule hard deletion for later (compliance requirement)
            if request.hard_delete:
                background_tasks.add_task(
                    _schedule_user_hard_deletion,
                    user_id=current_user.id,
                    deletion_date=datetime.now() + timedelta(days=30)  # 30-day grace period
                )
            
            deleted_counts["user_account"] = 1
        
        db.commit()
        
        return DataPurgeResponse(
            message="Data purged successfully" if not request.delete_all else "Account deletion initiated",
            deleted_counts=deleted_counts,
            deletion_type="partial" if not request.delete_all else "complete",
            hard_deletion_scheduled=request.hard_delete and request.delete_all
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Data purge failed: {str(e)}")


@router.get("/summary", response_model=UserDataSummary)
async def get_user_data_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a summary of user's data for retention management."""
    try:
        # Get expense statistics
        expense_stats = db.query(
            func.count(Expense.id).label('total_count'),
            func.min(Expense.date).label('earliest_date'),
            func.max(Expense.date).label('latest_date'),
            func.sum(Expense.amount).label('total_amount')
        ).filter(Expense.user_id == current_user.id).first()
        
        # Get budget statistics
        budget_stats = db.query(
            func.count(Budget.id).label('total_count'),
            func.min(Budget.start_date).label('earliest_date'),
            func.max(Budget.end_date).label('latest_date')
        ).filter(Budget.user_id == current_user.id).first()
        
        # Get expenses by category
        expenses_by_category = db.query(
            Expense.category,
            func.count(Expense.id).label('count'),
            func.sum(Expense.amount).label('total')
        ).filter(Expense.user_id == current_user.id).group_by(Expense.category).all()
        
        return UserDataSummary(
            user_id=current_user.id,
            account_created=current_user.created_at,
            expenses={
                "total_count": expense_stats.total_count or 0,
                "date_range": {
                    "earliest": expense_stats.earliest_date,
                    "latest": expense_stats.latest_date
                },
                "total_amount": float(expense_stats.total_amount or 0),
                "by_category": {
                    cat.category: {
                        "count": cat.count,
                        "total": float(cat.total)
                    }
                    for cat in expenses_by_category
                }
            },
            budgets={
                "total_count": budget_stats.total_count or 0,
                "date_range": {
                    "earliest": budget_stats.earliest_date,
                    "latest": budget_stats.latest_date
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get data summary: {str(e)}")


@router.get("/retention-stats", response_model=DataRetentionStats)
async def get_data_retention_stats(
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get system-wide data retention statistics (admin only)."""
    try:
        # Calculate retention periods
        now = datetime.now()
        one_year_ago = now - timedelta(days=365)
        two_years_ago = now - timedelta(days=730)
        
        # Count data by age
        total_users = db.query(func.count(User.id)).scalar()
        inactive_users = db.query(func.count(User.id)).filter(User.is_active == False).scalar()
        
        old_expenses = db.query(func.count(Expense.id)).filter(Expense.date < one_year_ago).scalar()
        very_old_expenses = db.query(func.count(Expense.id)).filter(Expense.date < two_years_ago).scalar()
        
        old_budgets = db.query(func.count(Budget.id)).filter(Budget.end_date < one_year_ago).scalar()
        
        # Users with no recent activity
        inactive_threshold = now - timedelta(days=180)
        users_with_recent_expenses = db.query(func.count(func.distinct(Expense.user_id))).filter(
            Expense.created_at >= inactive_threshold
        ).scalar()
        
        potentially_inactive_users = total_users - users_with_recent_expenses
        
        return DataRetentionStats(
            total_users=total_users,
            inactive_users=inactive_users,
            potentially_inactive_users=potentially_inactive_users,
            old_expenses_1year=old_expenses,
            old_expenses_2years=very_old_expenses,
            old_budgets=old_budgets,
            recommended_actions=[
                f"Consider archiving {very_old_expenses} expenses older than 2 years",
                f"Review {inactive_users} inactive user accounts",
                f"Contact {potentially_inactive_users} users with no recent activity",
                f"Clean up {old_budgets} expired budgets"
            ]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get retention stats: {str(e)}")


@router.post("/admin/cleanup")
async def admin_data_cleanup(
    retention_days: int = 365,
    dry_run: bool = True,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Admin endpoint for automated data cleanup based on retention policies.
    
    Args:
        retention_days: Number of days to retain data
        dry_run: If True, only report what would be deleted without actually deleting
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        # Find data to be cleaned up
        old_expenses = db.query(Expense).filter(Expense.date < cutoff_date)
        old_budgets = db.query(Budget).filter(Budget.end_date < cutoff_date)
        inactive_users = db.query(User).filter(
            and_(
                User.is_active == False,
                User.created_at < cutoff_date
            )
        )
        
        cleanup_summary = {
            "retention_policy": f"{retention_days} days",
            "cutoff_date": cutoff_date.isoformat(),
            "dry_run": dry_run,
            "items_to_cleanup": {
                "expenses": old_expenses.count(),
                "budgets": old_budgets.count(),
                "inactive_users": inactive_users.count()
            }
        }
        
        if not dry_run:
            # Perform actual cleanup
            expenses_deleted = old_expenses.delete(synchronize_session=False)
            budgets_deleted = old_budgets.delete(synchronize_session=False)
            users_deleted = inactive_users.delete(synchronize_session=False)
            
            db.commit()
            
            cleanup_summary["cleanup_performed"] = {
                "expenses_deleted": expenses_deleted,
                "budgets_deleted": budgets_deleted,
                "users_deleted": users_deleted,
                "timestamp": datetime.now().isoformat()
            }
        
        return cleanup_summary
        
    except Exception as e:
        if not dry_run:
            db.rollback()
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


async def _schedule_user_hard_deletion(user_id: int, deletion_date: datetime):
    """Background task to schedule hard deletion of user account."""
    # This would typically integrate with a job queue system like Celery
    # For now, we'll just log the scheduled deletion
    import logging
    logging.info(f"User {user_id} scheduled for hard deletion on {deletion_date}")
    
    # In a real implementation, you would:
    # 1. Store the deletion request in a queue/table
    # 2. Use a background job to process deletions
    # 3. Send confirmation emails to users
    # 4. Maintain audit logs of all deletions
