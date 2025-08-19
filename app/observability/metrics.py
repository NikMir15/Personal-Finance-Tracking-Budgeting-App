"""
Prometheus metrics for the Expense Tracker application.

This module provides:
- HTTP request metrics (count, duration, errors)
- Database operation metrics
- Business metrics (users, expenses, budgets)
- Application health metrics
- Custom metrics for specific features
"""

import time
from typing import Dict, Optional, Callable
from functools import wraps
from contextlib import contextmanager

from prometheus_client import (
    Counter, Histogram, Gauge, Info, CollectorRegistry, 
    CONTENT_TYPE_LATEST, generate_latest
)
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.observability.logging_config import get_logger

logger = get_logger("metrics")

# Create a custom registry for our application metrics
registry = CollectorRegistry()

# === HTTP Metrics ===
http_requests_total = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status_code'],
    registry=registry
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint', 'status_code'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
    registry=registry
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'Number of HTTP requests currently being processed',
    ['method', 'endpoint'],
    registry=registry
)

# === Error Metrics ===
errors_total = Counter(
    'errors_total',
    'Total number of errors',
    ['error_type', 'component', 'endpoint'],
    registry=registry
)

# === Database Metrics ===
database_operations_total = Counter(
    'database_operations_total',
    'Total number of database operations',
    ['operation', 'table', 'status'],
    registry=registry
)

database_operation_duration_seconds = Histogram(
    'database_operation_duration_seconds',
    'Database operation duration in seconds',
    ['operation', 'table'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=registry
)

database_connections_active = Gauge(
    'database_connections_active',
    'Number of active database connections',
    registry=registry
)

# === Business Metrics ===
users_total = Gauge(
    'users_total',
    'Total number of registered users',
    registry=registry
)

users_active_daily = Gauge(
    'users_active_daily',
    'Number of users active in the last 24 hours',
    registry=registry
)

expenses_total = Gauge(
    'expenses_total',
    'Total number of expenses recorded',
    registry=registry
)

expenses_amount_total = Gauge(
    'expenses_amount_total',
    'Total amount of all expenses',
    ['currency'],
    registry=registry
)

budgets_total = Gauge(
    'budgets_total',
    'Total number of budgets',
    registry=registry
)

# === Application Metrics ===
app_info = Info(
    'app_info',
    'Application information',
    registry=registry
)

app_start_time = Gauge(
    'app_start_time_seconds',
    'Application start time in unix timestamp',
    registry=registry
)

# === Feature-specific Metrics ===
receipt_uploads_total = Counter(
    'receipt_uploads_total',
    'Total number of receipt uploads',
    ['status', 'file_type'],
    registry=registry
)

receipt_processing_duration_seconds = Histogram(
    'receipt_processing_duration_seconds',
    'Receipt processing duration in seconds',
    ['processing_step'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
    registry=registry
)

auth_attempts_total = Counter(
    'auth_attempts_total',
    'Total number of authentication attempts',
    ['method', 'status'],
    registry=registry
)

rate_limit_hits_total = Counter(
    'rate_limit_hits_total',
    'Total number of rate limit hits',
    ['endpoint', 'limit_type'],
    registry=registry
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP metrics."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        # Skip metrics collection for the metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
        
        method = request.method
        path = self._normalize_path(request.url.path)
        
        # Track request in progress
        http_requests_in_progress.labels(method=method, endpoint=path).inc()
        
        start_time = time.time()
        status_code = "500"  # Default to 500 in case of error
        
        try:
            response = await call_next(request)
            status_code = str(response.status_code)
            return response
        except Exception as e:
            # Log error and track metrics
            errors_total.labels(
                error_type=type(e).__name__,
                component="http",
                endpoint=path
            ).inc()
            
            logger.error(
                "HTTP request failed",
                method=method,
                path=path,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise
        finally:
            # Calculate duration and update metrics
            duration = time.time() - start_time
            
            http_requests_total.labels(
                method=method,
                endpoint=path,
                status_code=status_code
            ).inc()
            
            http_request_duration_seconds.labels(
                method=method,
                endpoint=path,
                status_code=status_code
            ).observe(duration)
            
            http_requests_in_progress.labels(method=method, endpoint=path).dec()
    
    def _normalize_path(self, path: str) -> str:
        """Normalize URL paths to reduce cardinality."""
        # Remove trailing slashes
        path = path.rstrip('/')
        if not path:
            path = '/'
        
        # Replace UUIDs and IDs with placeholders
        import re
        
        # UUID pattern
        path = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '/{id}',
            path,
            flags=re.IGNORECASE
        )
        
        # Numeric IDs
        path = re.sub(r'/\d+', '/{id}', path)
        
        # Common dynamic segments
        path = re.sub(r'/[^/]+\.(jpg|jpeg|png|gif|pdf|csv|json|xml)$', '/{file}', path, flags=re.IGNORECASE)
        
        return path


@contextmanager
def database_operation_timer(operation: str, table: str):
    """Context manager to time database operations."""
    start_time = time.time()
    status = "success"
    
    try:
        yield
    except Exception as e:
        status = "error"
        errors_total.labels(
            error_type=type(e).__name__,
            component="database",
            endpoint=f"{operation}_{table}"
        ).inc()
        raise
    finally:
        duration = time.time() - start_time
        
        database_operations_total.labels(
            operation=operation.upper(),
            table=table,
            status=status
        ).inc()
        
        database_operation_duration_seconds.labels(
            operation=operation.upper(),
            table=table
        ).observe(duration)


def track_business_metric(metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
    """Track a business metric."""
    if labels is None:
        labels = {}
    
    # This is a simplified implementation
    # In a real system, you might want to use a more sophisticated metric registry
    logger.info(
        "Business metric recorded",
        metric_name=metric_name,
        value=value,
        labels=labels
    )


def timer(metric: Histogram, labels: Optional[Dict[str, str]] = None):
    """Decorator to time function execution."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with metric.labels(**(labels or {})).time():
                return func(*args, **kwargs)
        return wrapper
    return decorator


def counter(metric: Counter, labels: Optional[Dict[str, str]] = None):
    """Decorator to count function calls."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                metric.labels(**(labels or {})).inc()
                return result
            except Exception as e:
                error_labels = (labels or {}).copy()
                error_labels['status'] = 'error'
                error_labels['error_type'] = type(e).__name__
                metric.labels(**error_labels).inc()
                raise
        return wrapper
    return decorator


def initialize_app_metrics():
    """Initialize application metrics with startup values."""
    import os
    import time
    from datetime import datetime
    
    # Set application info
    app_info.info({
        'version': os.getenv('APP_VERSION', '1.0.0'),
        'environment': os.getenv('ENVIRONMENT', 'development'),
        'build_date': datetime.now().isoformat(),
        'python_version': f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"
    })
    
    # Set start time
    app_start_time.set(time.time())
    
    logger.info("Application metrics initialized")


def update_business_metrics(db_session):
    """Update business metrics from database."""
    try:
        from app.models.user import User
        from app.models.expense import Expense
        from app.models.budget import Budget
        from sqlalchemy import func, and_
        from datetime import datetime, timedelta
        
        # User metrics
        total_users = db_session.query(func.count(User.id)).scalar() or 0
        users_total.set(total_users)
        
        # Active users (simplified - in a real system, you'd track login times)
        # For now, we'll use a placeholder
        users_active_daily.set(max(1, total_users // 10))  # Assume 10% daily active
        
        # Expense metrics
        total_expenses = db_session.query(func.count(Expense.id)).scalar() or 0
        expenses_total.set(total_expenses)
        
        # Expense amounts by currency
        expense_amounts = db_session.query(
            Expense.currency,
            func.sum(Expense.amount)
        ).group_by(Expense.currency).all()
        
        for currency, total_amount in expense_amounts:
            expenses_amount_total.labels(currency=currency).set(float(total_amount or 0))
        
        # Budget metrics
        total_budgets = db_session.query(func.count(Budget.id)).scalar() or 0
        budgets_total.set(total_budgets)
        
        logger.info(
            "Business metrics updated",
            total_users=total_users,
            total_expenses=total_expenses,
            total_budgets=total_budgets
        )
        
    except Exception as e:
        logger.error(
            "Failed to update business metrics",
            error_type=type(e).__name__,
            error_message=str(e)
        )


def get_metrics_response() -> Response:
    """Generate Prometheus metrics response."""
    try:
        metrics_data = generate_latest(registry)
        return Response(
            content=metrics_data,
            media_type=CONTENT_TYPE_LATEST,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    except Exception as e:
        logger.error(
            "Failed to generate metrics",
            error_type=type(e).__name__,
            error_message=str(e)
        )
        return Response(
            content="# Error generating metrics\n",
            media_type="text/plain",
            status_code=500
        )
