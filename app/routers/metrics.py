"""
Metrics endpoint for Prometheus monitoring.

This router provides the /metrics endpoint for Prometheus scraping
and additional monitoring endpoints for observability.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.admin import get_admin_user
from app.models.user import User
from app.observability.metrics import get_metrics_response, update_business_metrics
from app.observability.logging_config import get_logger

router = APIRouter(prefix="/monitoring", tags=["monitoring"])
logger = get_logger("metrics_api")


@router.get("/metrics")
async def get_prometheus_metrics():
    """
    Prometheus metrics endpoint.
    
    This endpoint provides metrics in Prometheus format for scraping.
    No authentication required as it should be accessible to monitoring systems.
    """
    try:
        logger.info("Metrics endpoint accessed")
        return get_metrics_response()
    except Exception as e:
        logger.error(
            "Failed to generate metrics response",
            error_type=type(e).__name__,
            error_message=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate metrics"
        )


@router.get("/health/metrics")
async def get_metrics_health():
    """
    Health check for the metrics system.
    
    Returns basic information about the metrics collection status.
    """
    try:
        from app.observability.metrics import registry
        from prometheus_client import CollectorRegistry
        
        # Get basic metrics info
        metric_families = list(registry.collect())
        total_metrics = len(metric_families)
        
        # Calculate total samples
        total_samples = 0
        for family in metric_families:
            total_samples += len(family.samples)
        
        return {
            "status": "healthy",
            "metrics_available": True,
            "total_metric_families": total_metrics,
            "total_samples": total_samples,
            "registry_type": "custom"
        }
    except Exception as e:
        logger.error(
            "Metrics health check failed",
            error_type=type(e).__name__,
            error_message=str(e)
        )
        return {
            "status": "unhealthy",
            "metrics_available": False,
            "error": str(e)
        }


@router.post("/metrics/refresh")
async def refresh_business_metrics(
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Manually refresh business metrics from database.
    
    This endpoint allows administrators to trigger a manual update
    of business metrics (user counts, expense totals, etc.).
    """
    try:
        logger.info(
            "Manual metrics refresh triggered",
            admin_user=admin_user.username
        )
        
        update_business_metrics(db)
        
        return {
            "status": "success",
            "message": "Business metrics refreshed successfully",
            "refreshed_by": admin_user.username
        }
    except Exception as e:
        logger.error(
            "Failed to refresh business metrics",
            error_type=type(e).__name__,
            error_message=str(e),
            admin_user=admin_user.username
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh business metrics"
        )


@router.get("/debug/metrics")
async def get_metrics_debug_info(
    admin_user: User = Depends(get_admin_user)
):
    """
    Get detailed metrics debug information (admin only).
    
    Returns detailed information about the metrics system
    for debugging and monitoring purposes.
    """
    try:
        from app.observability.metrics import registry
        import os
        import psutil
        import time
        
        # Get system information
        process = psutil.Process()
        
        # Get metrics information
        metric_families = list(registry.collect())
        
        metrics_info = []
        for family in metric_families:
            family_info = {
                "name": family.name,
                "help": family.help,
                "type": family.type,
                "samples_count": len(family.samples)
            }
            
            # Add sample values for small metrics
            if len(family.samples) <= 10:
                family_info["samples"] = [
                    {
                        "name": sample.name,
                        "labels": dict(sample.labels),
                        "value": sample.value
                    }
                    for sample in family.samples
                ]
            
            metrics_info.append(family_info)
        
        debug_info = {
            "system_info": {
                "process_id": os.getpid(),
                "memory_usage_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                "cpu_percent": process.cpu_percent(),
                "uptime_seconds": round(time.time() - process.create_time(), 2),
                "thread_count": process.num_threads()
            },
            "metrics_info": {
                "total_metric_families": len(metric_families),
                "total_samples": sum(len(f.samples) for f in metric_families),
                "registry_type": "prometheus_client.CollectorRegistry"
            },
            "environment": {
                "app_version": os.getenv('APP_VERSION', '1.0.0'),
                "environment": os.getenv('ENVIRONMENT', 'development'),
                "sentry_enabled": bool(os.getenv('SENTRY_DSN')),
                "log_level": os.getenv('LOG_LEVEL', 'INFO')
            },
            "metrics_families": metrics_info
        }
        
        logger.info(
            "Metrics debug info requested",
            admin_user=admin_user.username,
            total_metrics=len(metric_families)
        )
        
        return debug_info
        
    except Exception as e:
        logger.error(
            "Failed to get metrics debug info",
            error_type=type(e).__name__,
            error_message=str(e),
            admin_user=admin_user.username
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get metrics debug information"
        )


@router.get("/alerts/rules")
async def get_alert_rules(
    admin_user: User = Depends(get_admin_user)
):
    """
    Get recommended Prometheus alerting rules.
    
    Returns a set of recommended alerting rules that can be
    configured in Prometheus for monitoring this application.
    """
    
    alert_rules = {
        "groups": [
            {
                "name": "expense_tracker_alerts",
                "rules": [
                    {
                        "alert": "HighErrorRate",
                        "expr": "rate(http_requests_total{status_code=~\"5..\"}[5m]) > 0.1",
                        "for": "5m",
                        "labels": {
                            "severity": "critical"
                        },
                        "annotations": {
                            "summary": "High error rate detected",
                            "description": "Error rate is {{ $value }} errors per second"
                        }
                    },
                    {
                        "alert": "HighResponseTime",
                        "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2",
                        "for": "10m",
                        "labels": {
                            "severity": "warning"
                        },
                        "annotations": {
                            "summary": "High response time detected",
                            "description": "95th percentile response time is {{ $value }} seconds"
                        }
                    },
                    {
                        "alert": "DatabaseConnectionsHigh",
                        "expr": "database_connections_active > 80",
                        "for": "5m",
                        "labels": {
                            "severity": "warning"
                        },
                        "annotations": {
                            "summary": "High database connection usage",
                            "description": "Database connections: {{ $value }}"
                        }
                    },
                    {
                        "alert": "ApplicationDown",
                        "expr": "up{job=\"expense_tracker\"} == 0",
                        "for": "1m",
                        "labels": {
                            "severity": "critical"
                        },
                        "annotations": {
                            "summary": "Application is down",
                            "description": "Expense Tracker application is not responding"
                        }
                    },
                    {
                        "alert": "MemoryUsageHigh",
                        "expr": "process_resident_memory_bytes / 1024 / 1024 > 512",
                        "for": "10m",
                        "labels": {
                            "severity": "warning"
                        },
                        "annotations": {
                            "summary": "High memory usage",
                            "description": "Memory usage is {{ $value }}MB"
                        }
                    }
                ]
            }
        ]
    }
    
    logger.info(
        "Alert rules requested",
        admin_user=admin_user.username
    )
    
    return alert_rules


@router.get("/dashboards/grafana")
async def get_grafana_dashboard(
    admin_user: User = Depends(get_admin_user)
):
    """
    Get Grafana dashboard configuration.
    
    Returns a Grafana dashboard JSON configuration for monitoring
    the Expense Tracker application.
    """
    
    dashboard_config = {
        "dashboard": {
            "id": None,
            "title": "Expense Tracker Monitoring",
            "tags": ["expense-tracker", "fastapi"],
            "timezone": "browser",
            "panels": [
                {
                    "id": 1,
                    "title": "Request Rate",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "rate(http_requests_total[5m])",
                            "legendFormat": "{{method}} {{endpoint}}"
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
                },
                {
                    "id": 2,
                    "title": "Response Time",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
                            "legendFormat": "95th percentile"
                        },
                        {
                            "expr": "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))",
                            "legendFormat": "50th percentile"
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
                },
                {
                    "id": 3,
                    "title": "Error Rate",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "rate(http_requests_total{status_code=~\"4..\"}[5m])",
                            "legendFormat": "4xx errors"
                        },
                        {
                            "expr": "rate(http_requests_total{status_code=~\"5..\"}[5m])",
                            "legendFormat": "5xx errors"
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
                },
                {
                    "id": 4,
                    "title": "Business Metrics",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": "users_total",
                            "legendFormat": "Total Users"
                        },
                        {
                            "expr": "expenses_total",
                            "legendFormat": "Total Expenses"
                        },
                        {
                            "expr": "budgets_total",
                            "legendFormat": "Total Budgets"
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
                }
            ],
            "time": {
                "from": "now-1h",
                "to": "now"
            },
            "refresh": "30s"
        },
        "overwrite": True
    }
    
    logger.info(
        "Grafana dashboard config requested",
        admin_user=admin_user.username
    )
    
    return dashboard_config
