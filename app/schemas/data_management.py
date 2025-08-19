"""
Pydantic schemas for data management and retention endpoints.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class DataExportRequest(BaseModel):
    """Request model for user data export."""
    format: Literal["json", "csv"] = Field(default="json", description="Export format")
    include_categories: List[str] = Field(
        default=["expenses", "budgets"],
        description="Data categories to include in export"
    )
    date_from: Optional[datetime] = Field(default=None, description="Start date for data export")
    date_to: Optional[datetime] = Field(default=None, description="End date for data export")


class DataExportResponse(BaseModel):
    """Response model for user data export."""
    message: str = Field(description="Export status message")
    filename: str = Field(description="Generated filename for the export")
    content_type: str = Field(description="MIME type of the exported data")
    size_bytes: int = Field(description="Size of the export file in bytes")
    records_count: Dict[str, int] = Field(description="Count of records by category")


class DataPurgeRequest(BaseModel):
    """Request model for user data purging/deletion."""
    categories: List[str] = Field(
        default=[],
        description="Specific data categories to delete (expenses, budgets)"
    )
    date_from: Optional[datetime] = Field(default=None, description="Delete data from this date")
    date_to: Optional[datetime] = Field(default=None, description="Delete data up to this date")
    delete_all: bool = Field(default=False, description="Delete all user data including account")
    hard_delete: bool = Field(default=False, description="Permanently delete account (cannot be recovered)")
    confirm_deletion: bool = Field(
        default=False,
        description="Explicit confirmation required for data deletion"
    )


class DataPurgeResponse(BaseModel):
    """Response model for data purging operations."""
    message: str = Field(description="Purge operation status message")
    deleted_counts: Dict[str, int] = Field(description="Count of deleted records by category")
    deletion_type: Literal["partial", "complete"] = Field(description="Type of deletion performed")
    hard_deletion_scheduled: bool = Field(
        default=False,
        description="Whether hard deletion has been scheduled"
    )


class UserDataSummary(BaseModel):
    """Summary of user's data for retention management."""
    user_id: int = Field(description="User ID")
    account_created: datetime = Field(description="Account creation date")
    expenses: Dict[str, Any] = Field(description="Expense data summary")
    budgets: Dict[str, Any] = Field(description="Budget data summary")


class DataRetentionStats(BaseModel):
    """System-wide data retention statistics for admin use."""
    total_users: int = Field(description="Total number of users")
    inactive_users: int = Field(description="Number of inactive users")
    potentially_inactive_users: int = Field(description="Users with no recent activity")
    old_expenses_1year: int = Field(description="Expenses older than 1 year")
    old_expenses_2years: int = Field(description="Expenses older than 2 years")
    old_budgets: int = Field(description="Expired budgets older than 1 year")
    recommended_actions: List[str] = Field(description="Recommended data retention actions")


class ScheduledDeletion(BaseModel):
    """Model for scheduled user account deletions."""
    user_id: int = Field(description="User ID scheduled for deletion")
    deletion_date: datetime = Field(description="Scheduled deletion date")
    requested_at: datetime = Field(description="When deletion was requested")
    status: Literal["pending", "completed", "cancelled"] = Field(description="Deletion status")


class DataRetentionPolicy(BaseModel):
    """Configuration for data retention policies."""
    name: str = Field(description="Policy name")
    retention_days: int = Field(description="Number of days to retain data")
    applies_to: List[str] = Field(description="Data categories this policy applies to")
    auto_cleanup: bool = Field(default=False, description="Enable automatic cleanup")
    grace_period_days: int = Field(default=30, description="Grace period before hard deletion")


class ComplianceReport(BaseModel):
    """Data compliance and audit report."""
    report_date: datetime = Field(description="Report generation date")
    total_data_requests: int = Field(description="Total number of data requests processed")
    export_requests: int = Field(description="Number of data export requests")
    deletion_requests: int = Field(description="Number of data deletion requests")
    compliance_score: float = Field(description="Overall compliance score (0-100)")
    pending_deletions: int = Field(description="Number of pending hard deletions")
    data_categories: Dict[str, Dict[str, Any]] = Field(description="Data statistics by category")


class AuditLogEntry(BaseModel):
    """Audit log entry for data operations."""
    timestamp: datetime = Field(description="Operation timestamp")
    user_id: int = Field(description="User who performed the operation")
    operation: Literal["export", "delete", "purge", "backup", "restore"] = Field(description="Operation type")
    category: str = Field(description="Data category affected")
    details: Dict[str, Any] = Field(description="Operation details")
    ip_address: Optional[str] = Field(default=None, description="Client IP address")
    user_agent: Optional[str] = Field(default=None, description="Client user agent")


class DataMigrationPlan(BaseModel):
    """Plan for data migration operations."""
    migration_id: str = Field(description="Unique migration identifier")
    source_version: str = Field(description="Source data schema version")
    target_version: str = Field(description="Target data schema version")
    affected_tables: List[str] = Field(description="Database tables to be migrated")
    estimated_duration: int = Field(description="Estimated migration time in minutes")
    backup_required: bool = Field(default=True, description="Whether backup is required")
    rollback_plan: Optional[str] = Field(default=None, description="Rollback procedure")


class BackupMetadata(BaseModel):
    """Metadata for database backups."""
    backup_id: str = Field(description="Unique backup identifier")
    creation_date: datetime = Field(description="Backup creation timestamp")
    backup_type: Literal["full", "incremental", "differential"] = Field(description="Type of backup")
    file_path: str = Field(description="Backup file location")
    file_size: int = Field(description="Backup file size in bytes")
    checksum: str = Field(description="File integrity checksum")
    tables_included: List[str] = Field(description="Database tables included in backup")
    retention_until: datetime = Field(description="Backup retention expiry date")
    encryption_enabled: bool = Field(default=False, description="Whether backup is encrypted")


class RestoreRequest(BaseModel):
    """Request model for database restore operations."""
    backup_id: str = Field(description="Backup identifier to restore from")
    target_database: Optional[str] = Field(default=None, description="Target database name")
    restore_options: Dict[str, Any] = Field(
        default={},
        description="Additional restore options"
    )
    verify_integrity: bool = Field(default=True, description="Verify backup integrity before restore")
    confirm_restore: bool = Field(
        default=False,
        description="Explicit confirmation required for restore operation"
    )


class RestoreResponse(BaseModel):
    """Response model for database restore operations."""
    message: str = Field(description="Restore operation status")
    backup_id: str = Field(description="Backup used for restore")
    restore_duration: int = Field(description="Time taken for restore in seconds")
    tables_restored: List[str] = Field(description="Database tables that were restored")
    verification_status: bool = Field(description="Post-restore verification status")
    rollback_available: bool = Field(description="Whether rollback is possible")


class DataQualityMetrics(BaseModel):
    """Data quality assessment metrics."""
    assessment_date: datetime = Field(description="Assessment timestamp")
    total_records: int = Field(description="Total number of records assessed")
    quality_score: float = Field(description="Overall data quality score (0-100)")
    issues_found: Dict[str, int] = Field(description="Count of issues by type")
    completeness_score: float = Field(description="Data completeness percentage")
    accuracy_score: float = Field(description="Data accuracy percentage")
    consistency_score: float = Field(description="Data consistency percentage")
    recommendations: List[str] = Field(description="Data quality improvement recommendations")


class PrivacySettings(BaseModel):
    """User privacy settings and preferences."""
    user_id: int = Field(description="User ID")
    data_retention_preference: int = Field(
        default=365,
        description="User's preferred data retention period in days"
    )
    analytics_consent: bool = Field(default=True, description="Consent for analytics data usage")
    marketing_consent: bool = Field(default=False, description="Consent for marketing communications")
    data_sharing_consent: bool = Field(default=False, description="Consent for data sharing with third parties")
    export_notifications: bool = Field(default=True, description="Receive notifications for data exports")
    deletion_notifications: bool = Field(default=True, description="Receive notifications for data deletions")
    updated_at: datetime = Field(description="Last update timestamp")
