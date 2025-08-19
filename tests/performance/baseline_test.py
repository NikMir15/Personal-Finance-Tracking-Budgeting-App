#!/usr/bin/env python3
"""
Performance baseline testing for Expense Tracker API.

This script establishes performance baselines using Python's asyncio
and aiohttp for concurrent request testing. Provides similar functionality
to hey/autocannon but works cross-platform.

Tests:
- Single endpoint RPS (Requests Per Second)
- Response time percentiles
- Concurrent user scenarios
- Database connection pool performance
"""

import asyncio
import aiohttp
import time
import statistics
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import argparse


@dataclass
class RequestResult:
    """Result of a single HTTP request."""
    duration_ms: float
    status_code: int
    success: bool
    error: Optional[str] = None


@dataclass
class TestResult:
    """Results of a performance test."""
    endpoint: str
    method: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    test_duration_seconds: float
    requests_per_second: float
    
    # Response time statistics (in milliseconds)
    min_response_time: float
    max_response_time: float
    mean_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    
    # Error information
    error_rate: float
    status_code_distribution: Dict[int, int]
    errors: List[str]


class PerformanceTester:
    """Performance testing client."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.auth_token: Optional[str] = None
    
    async def authenticate(self, session: aiohttp.ClientSession) -> bool:
        """Authenticate and get access token."""
        user_data = {
            "username": f"perftest_user_{int(time.time())}",
            "email": f"perftest_{int(time.time())}@example.com",
            "password": "PerfTest123!",
            "base_currency": "USD"
        }
        
        try:
            async with session.post(f"{self.base_url}/auth/register", json=user_data) as response:
                if response.status == 201:
                    data = await response.json()
                    self.auth_token = data.get("access_token")
                    return True
                return False
        except Exception:
            return False
    
    async def make_request(self, 
                          session: aiohttp.ClientSession,
                          method: str,
                          endpoint: str,
                          **kwargs) -> RequestResult:
        """Make a single HTTP request and measure performance."""
        start_time = time.time()
        
        try:
            headers = kwargs.get('headers', {})
            if self.auth_token and 'Authorization' not in headers:
                headers['Authorization'] = f"Bearer {self.auth_token}"
                kwargs['headers'] = headers
            
            async with session.request(method, f"{self.base_url}{endpoint}", **kwargs) as response:
                await response.read()  # Ensure we read the full response
                
                duration_ms = (time.time() - start_time) * 1000
                return RequestResult(
                    duration_ms=duration_ms,
                    status_code=response.status,
                    success=200 <= response.status < 400
                )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return RequestResult(
                duration_ms=duration_ms,
                status_code=0,
                success=False,
                error=str(e)
            )
    
    async def concurrent_test(self,
                             method: str,
                             endpoint: str,
                             concurrent_users: int,
                             requests_per_user: int,
                             **request_kwargs) -> TestResult:
        """Run concurrent performance test."""
        print(f"Testing {method} {endpoint} with {concurrent_users} concurrent users, {requests_per_user} requests each")
        
        # Create session with appropriate settings
        connector = aiohttp.TCPConnector(
            limit=concurrent_users * 2,  # Connection pool size
            limit_per_host=concurrent_users * 2,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Authenticate if needed
            if not await self.authenticate(session):
                raise Exception("Authentication failed")
            
            # Create tasks for concurrent execution
            tasks = []
            for user in range(concurrent_users):
                for request in range(requests_per_user):
                    task = self.make_request(session, method, endpoint, **request_kwargs)
                    tasks.append(task)
            
            # Execute all requests concurrently
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # Process results
            valid_results = [r for r in results if isinstance(r, RequestResult)]
            
            return self.analyze_results(
                endpoint=endpoint,
                method=method,
                results=valid_results,
                test_duration=end_time - start_time
            )
    
    def analyze_results(self,
                       endpoint: str,
                       method: str,
                       results: List[RequestResult],
                       test_duration: float) -> TestResult:
        """Analyze performance test results."""
        total_requests = len(results)
        successful_requests = sum(1 for r in results if r.success)
        failed_requests = total_requests - successful_requests
        
        # Response time statistics
        durations = [r.duration_ms for r in results]
        
        if durations:
            min_time = min(durations)
            max_time = max(durations)
            mean_time = statistics.mean(durations)
            
            # Calculate percentiles
            sorted_durations = sorted(durations)
            p50 = sorted_durations[int(0.50 * len(sorted_durations))]
            p95 = sorted_durations[int(0.95 * len(sorted_durations))]
            p99 = sorted_durations[int(0.99 * len(sorted_durations))]
        else:
            min_time = max_time = mean_time = p50 = p95 = p99 = 0
        
        # Status code distribution
        status_codes = {}
        errors = []
        
        for result in results:
            status_codes[result.status_code] = status_codes.get(result.status_code, 0) + 1
            if result.error:
                errors.append(result.error)
        
        # Calculate RPS
        rps = total_requests / test_duration if test_duration > 0 else 0
        error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0
        
        return TestResult(
            endpoint=endpoint,
            method=method,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            test_duration_seconds=test_duration,
            requests_per_second=rps,
            min_response_time=min_time,
            max_response_time=max_time,
            mean_response_time=mean_time,
            p50_response_time=p50,
            p95_response_time=p95,
            p99_response_time=p99,
            error_rate=error_rate,
            status_code_distribution=status_codes,
            errors=errors[:10]  # Limit error list
        )
    
    def print_results(self, result: TestResult):
        """Print formatted test results."""
        print(f"\n{'='*60}")
        print(f"Performance Test Results: {result.method} {result.endpoint}")
        print(f"{'='*60}")
        
        print(f"Requests:          {result.total_requests:,}")
        print(f"Successful:        {result.successful_requests:,}")
        print(f"Failed:            {result.failed_requests:,}")
        print(f"Test Duration:     {result.test_duration_seconds:.2f}s")
        print(f"Requests/sec:      {result.requests_per_second:.2f}")
        print(f"Error Rate:        {result.error_rate:.2f}%")
        
        print(f"\nResponse Times (ms):")
        print(f"  Min:             {result.min_response_time:.2f}")
        print(f"  Mean:            {result.mean_response_time:.2f}")
        print(f"  P50:             {result.p50_response_time:.2f}")
        print(f"  P95:             {result.p95_response_time:.2f}")
        print(f"  P99:             {result.p99_response_time:.2f}")
        print(f"  Max:             {result.max_response_time:.2f}")
        
        if result.status_code_distribution:
            print(f"\nStatus Codes:")
            for code, count in sorted(result.status_code_distribution.items()):
                percentage = (count / result.total_requests * 100)
                print(f"  {code}:             {count:,} ({percentage:.1f}%)")
        
        if result.errors:
            print(f"\nSample Errors:")
            for error in result.errors:
                print(f"  • {error}")
        
        # SLO Compliance Check
        print(f"\nSLO Compliance:")
        
        # Check p95 < 300ms for GET endpoints
        if result.method == "GET" and "/expenses" in result.endpoint:
            p95_target = 300.0
            p95_status = "✅ PASS" if result.p95_response_time <= p95_target else "❌ FAIL"
            print(f"  P95 < 300ms:      {p95_status} ({result.p95_response_time:.2f}ms)")
        
        # Check error rate < 1%
        error_target = 1.0
        error_status = "✅ PASS" if result.error_rate <= error_target else "❌ FAIL"
        print(f"  Error Rate < 1%:   {error_status} ({result.error_rate:.2f}%)")
        
        # Check minimum throughput
        min_rps = 10.0  # Minimum 10 RPS
        rps_status = "✅ PASS" if result.requests_per_second >= min_rps else "❌ FAIL"
        print(f"  Min 10 RPS:       {rps_status} ({result.requests_per_second:.2f} RPS)")


async def run_baseline_tests(base_url: str, output_file: Optional[str] = None):
    """Run comprehensive baseline performance tests."""
    tester = PerformanceTester(base_url)
    
    # Test scenarios
    test_scenarios = [
        # Endpoint testing with different load levels
        {
            "name": "Health Check - Light Load",
            "method": "GET",
            "endpoint": "/healthz",
            "concurrent_users": 5,
            "requests_per_user": 20
        },
        {
            "name": "Health Check - Heavy Load",
            "method": "GET",
            "endpoint": "/healthz",
            "concurrent_users": 50,
            "requests_per_user": 10
        },
        {
            "name": "Expenses List - Light Load",
            "method": "GET",
            "endpoint": "/expenses/",
            "concurrent_users": 5,
            "requests_per_user": 20
        },
        {
            "name": "Expenses List - Heavy Load",
            "method": "GET",
            "endpoint": "/expenses/",
            "concurrent_users": 25,
            "requests_per_user": 10
        },
        {
            "name": "Budgets List - Baseline",
            "method": "GET",
            "endpoint": "/budgets/",
            "concurrent_users": 10,
            "requests_per_user": 15
        },
        {
            "name": "Analytics Dashboard - Baseline",
            "method": "GET",
            "endpoint": "/analytics/dashboard",
            "concurrent_users": 8,
            "requests_per_user": 10
        },
        {
            "name": "SLO Monitoring - Baseline",
            "method": "GET",
            "endpoint": "/slo",
            "concurrent_users": 5,
            "requests_per_user": 10
        }
    ]
    
    results = []
    
    print(f"🚀 Starting Performance Baseline Tests")
    print(f"Target: {base_url}")
    print(f"Total Scenarios: {len(test_scenarios)}")
    print("=" * 60)
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n[{i}/{len(test_scenarios)}] Running: {scenario['name']}")
        
        try:
            result = await tester.concurrent_test(
                method=scenario["method"],
                endpoint=scenario["endpoint"],
                concurrent_users=scenario["concurrent_users"],
                requests_per_user=scenario["requests_per_user"]
            )
            
            tester.print_results(result)
            results.append(result)
            
            # Brief pause between tests
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
    
    # Summary
    print(f"\n{'='*60}")
    print("PERFORMANCE BASELINE SUMMARY")
    print(f"{'='*60}")
    
    total_requests = sum(r.total_requests for r in results)
    avg_rps = statistics.mean([r.requests_per_second for r in results])
    avg_p95 = statistics.mean([r.p95_response_time for r in results])
    
    print(f"Total Requests:    {total_requests:,}")
    print(f"Average RPS:       {avg_rps:.2f}")
    print(f"Average P95:       {avg_p95:.2f}ms")
    
    # SLO Summary
    slo_passes = 0
    for result in results:
        if result.error_rate <= 1.0 and result.requests_per_second >= 10.0:
            if result.method == "GET" and "/expenses" in result.endpoint:
                if result.p95_response_time <= 300.0:
                    slo_passes += 1
            else:
                slo_passes += 1
    
    slo_rate = (slo_passes / len(results) * 100) if results else 0
    print(f"SLO Compliance:    {slo_rate:.1f}% ({slo_passes}/{len(results)} tests)")
    
    # Save results to file
    if output_file:
        report_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "base_url": base_url,
            "summary": {
                "total_requests": total_requests,
                "average_rps": avg_rps,
                "average_p95_ms": avg_p95,
                "slo_compliance_rate": slo_rate
            },
            "results": [
                {
                    "endpoint": r.endpoint,
                    "method": r.method,
                    "requests_per_second": r.requests_per_second,
                    "p95_response_time": r.p95_response_time,
                    "error_rate": r.error_rate,
                    "total_requests": r.total_requests
                }
                for r in results
            ]
        }
        
        with open(output_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: {output_file}")


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description="Performance baseline testing for Expense Tracker API")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the API")
    parser.add_argument("--output", help="JSON file to save results")
    
    args = parser.parse_args()
    
    # Run the async test
    asyncio.run(run_baseline_tests(args.url, args.output))


if __name__ == "__main__":
    main()
