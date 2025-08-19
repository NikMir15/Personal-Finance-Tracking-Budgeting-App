"""
Service Level Objectives (SLO) definitions and monitoring for Expense Tracker.

This module defines and tracks SLOs for:
- Response time targets (p95 < 300ms for GET endpoints)
- Availability targets (99.9% uptime)
- Error rate targets (< 1% error rate)
- Database performance targets
"""

import time
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
import statistics

from app.schemas.health import SLOStatus, PerformanceMetrics


@dataclass
class SLOTarget:
    """Definition of a Service Level Objective."""
    name: str
    description: str
    target_value: float
    unit: str
    measurement_window: str  # e.g., "1h", "24h", "7d"
    alert_threshold: float  # When to alert (e.g., 0.95 for 95% of target)
    critical_threshold: float  # When to mark as critical


@dataclass
class Measurement:
    """A single measurement for SLO tracking."""
    timestamp: datetime
    value: float
    endpoint: Optional[str] = None
    method: Optional[str] = None


class SLOTracker:
    """
    Tracks and monitors Service Level Objectives.
    
    This is a lightweight in-memory tracker suitable for single-instance
    applications. For production, consider using a proper metrics backend
    like Prometheus + Grafana.
    """
    
    def __init__(self):
        # SLO definitions
        self.slos = {
            "response_time_p95": SLOTarget(
                name="Response Time P95",
                description="95th percentile response time for GET /expenses",
                target_value=300.0,  # ms
                unit="ms",
                measurement_window="1h",
                alert_threshold=0.9,  # Alert at 270ms
                critical_threshold=0.8  # Critical at 240ms
            ),
            "response_time_p99": SLOTarget(
                name="Response Time P99",
                description="99th percentile response time for all endpoints",
                target_value=1000.0,  # ms
                unit="ms",
                measurement_window="1h",
                alert_threshold=0.9,
                critical_threshold=0.8
            ),
            "availability": SLOTarget(
                name="Service Availability",
                description="Service uptime percentage",
                target_value=99.9,  # %
                unit="%",
                measurement_window="24h",
                alert_threshold=0.998,  # Alert at 99.8%
                critical_threshold=0.995  # Critical at 99.5%
            ),
            "error_rate": SLOTarget(
                name="Error Rate",
                description="Percentage of requests returning 5xx errors",
                target_value=1.0,  # % (target is < 1%)
                unit="%",
                measurement_window="1h",
                alert_threshold=2.0,  # Alert at 2%
                critical_threshold=5.0  # Critical at 5%
            ),
            "db_connection_time": SLOTarget(
                name="Database Connection Time",
                description="Time to establish database connection",
                target_value=100.0,  # ms
                unit="ms",
                measurement_window="1h",
                alert_threshold=0.8,
                critical_threshold=0.6
            )
        }
        
        # In-memory storage for measurements
        # In production, use a proper time-series database
        self.measurements: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.request_counts: Dict[str, int] = defaultdict(int)
        self.error_counts: Dict[str, int] = defaultdict(int)
        
        # Start time for uptime calculation
        self.start_time = datetime.utcnow()
        self.downtime_periods: List[tuple] = []
    
    def record_request_time(self, endpoint: str, method: str, duration_ms: float):
        """Record a request duration for SLO tracking."""
        measurement = Measurement(
            timestamp=datetime.utcnow(),
            value=duration_ms,
            endpoint=endpoint,
            method=method
        )
        
        key = f"{method}_{endpoint}"
        self.measurements[f"response_time_{key}"].append(measurement)
        self.measurements["response_time_all"].append(measurement)
        self.request_counts[key] += 1
        
    def record_error(self, endpoint: str, method: str, status_code: int):
        """Record an error for SLO tracking."""
        if 500 <= status_code < 600:
            key = f"{method}_{endpoint}"
            self.error_counts[key] += 1
            
            measurement = Measurement(
                timestamp=datetime.utcnow(),
                value=1,  # Error occurred
                endpoint=endpoint,
                method=method
            )
            self.measurements[f"errors_{key}"].append(measurement)
    
    def record_downtime(self, start_time: datetime, end_time: datetime):
        """Record a downtime period."""
        self.downtime_periods.append((start_time, end_time))
    
    def get_percentile(self, measurements: List[Measurement], percentile: float) -> float:
        """Calculate percentile from measurements."""
        if not measurements:
            return 0.0
        
        values = [m.value for m in measurements]
        return statistics.quantiles(values, n=100)[int(percentile) - 1] if len(values) > 1 else values[0]
    
    def filter_measurements_by_window(self, measurements: deque, window: str) -> List[Measurement]:
        """Filter measurements by time window."""
        now = datetime.utcnow()
        
        # Parse window (simplified - only support hours for now)
        if window.endswith('h'):
            hours = int(window[:-1])
            cutoff = now - timedelta(hours=hours)
        elif window.endswith('d'):
            days = int(window[:-1])
            cutoff = now - timedelta(days=days)
        else:
            # Default to 1 hour
            cutoff = now - timedelta(hours=1)
        
        return [m for m in measurements if m.timestamp >= cutoff]
    
    def get_slo_status(self, slo_name: str) -> SLOStatus:
        """Get current status of an SLO."""
        if slo_name not in self.slos:
            return SLOStatus(
                name=slo_name,
                target=0.0,
                current=0.0,
                status="unknown",
                window="unknown",
                details="SLO not found"
            )
        
        slo = self.slos[slo_name]
        
        if slo_name == "response_time_p95":
            measurements = self.filter_measurements_by_window(
                self.measurements["response_time_GET_/expenses/"],
                slo.measurement_window
            )
            current_value = self.get_percentile(measurements, 95)
            
        elif slo_name == "response_time_p99":
            measurements = self.filter_measurements_by_window(
                self.measurements["response_time_all"],
                slo.measurement_window
            )
            current_value = self.get_percentile(measurements, 99)
            
        elif slo_name == "availability":
            current_value = self.calculate_availability(slo.measurement_window)
            
        elif slo_name == "error_rate":
            current_value = self.calculate_error_rate(slo.measurement_window)
            
        else:
            current_value = 0.0
        
        # Determine status
        if slo_name in ["error_rate"]:
            # For error rate, higher is worse
            if current_value <= slo.target_value:
                status = "ok"
            elif current_value <= slo.critical_threshold:
                status = "warning"
            else:
                status = "critical"
        else:
            # For other metrics, meeting target is good
            if current_value <= slo.target_value:
                status = "ok"
            elif current_value <= slo.target_value / slo.alert_threshold:
                status = "warning"
            else:
                status = "critical"
        
        return SLOStatus(
            name=slo.name,
            target=slo.target_value,
            current=round(current_value, 2),
            status=status,
            window=slo.measurement_window,
            details=f"Target: {slo.target_value}{slo.unit}, Current: {current_value:.2f}{slo.unit}"
        )
    
    def calculate_availability(self, window: str) -> float:
        """Calculate service availability percentage."""
        now = datetime.utcnow()
        
        # Parse window
        if window.endswith('h'):
            hours = int(window[:-1])
            window_start = now - timedelta(hours=hours)
        elif window.endswith('d'):
            days = int(window[:-1])
            window_start = now - timedelta(days=days)
        else:
            window_start = now - timedelta(hours=1)
        
        total_time = (now - max(window_start, self.start_time)).total_seconds()
        downtime = 0
        
        for start, end in self.downtime_periods:
            if end > window_start:
                actual_start = max(start, window_start)
                actual_end = min(end, now)
                downtime += (actual_end - actual_start).total_seconds()
        
        if total_time == 0:
            return 100.0
        
        availability = ((total_time - downtime) / total_time) * 100
        return max(0.0, min(100.0, availability))
    
    def calculate_error_rate(self, window: str) -> float:
        """Calculate error rate percentage."""
        # This is a simplified calculation
        # In production, you'd want more sophisticated error tracking
        total_requests = sum(self.request_counts.values())
        total_errors = sum(self.error_counts.values())
        
        if total_requests == 0:
            return 0.0
        
        return (total_errors / total_requests) * 100
    
    def get_all_slo_status(self) -> List[SLOStatus]:
        """Get status of all SLOs."""
        return [self.get_slo_status(slo_name) for slo_name in self.slos.keys()]
    
    def get_performance_metrics(self, endpoint: str = None) -> List[PerformanceMetrics]:
        """Get performance metrics for endpoints."""
        metrics = []
        
        if endpoint:
            keys = [k for k in self.measurements.keys() if endpoint in k and "response_time" in k]
        else:
            keys = [k for k in self.measurements.keys() if "response_time" in k]
        
        for key in keys:
            measurements = list(self.measurements[key])
            if not measurements:
                continue
            
            # Extract endpoint and method from key
            parts = key.split('_')
            if len(parts) >= 3:
                method = parts[2]
                endpoint_path = '_'.join(parts[3:])
            else:
                method = "GET"
                endpoint_path = key
            
            values = [m.value for m in measurements]
            
            # Calculate percentiles
            p50 = self.get_percentile(measurements, 50)
            p95 = self.get_percentile(measurements, 95)
            p99 = self.get_percentile(measurements, 99)
            
            # Calculate success rate (simplified)
            total_requests = len(measurements)
            error_key = key.replace("response_time", "errors")
            error_count = len(self.measurements.get(error_key, []))
            success_rate = ((total_requests - error_count) / total_requests * 100) if total_requests > 0 else 100.0
            
            metrics.append(PerformanceMetrics(
                endpoint=endpoint_path,
                method=method,
                p50_ms=round(p50, 2),
                p95_ms=round(p95, 2),
                p99_ms=round(p99, 2),
                success_rate=round(success_rate, 2),
                total_requests=total_requests,
                error_count=error_count,
                avg_rps=total_requests / 3600  # Assuming 1 hour window
            ))
        
        return metrics


# Global SLO tracker instance
slo_tracker = SLOTracker()
