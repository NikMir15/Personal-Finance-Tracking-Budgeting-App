#!/usr/bin/env python3
"""
Security vulnerability scanning script for Expense Tracker.

This script runs multiple security scans:
- pip-audit: Check for known vulnerabilities in dependencies
- bandit: Static security analysis of Python code
- safety: Check dependencies against PyUp.io database
- Custom security configuration validation
"""

import subprocess
import sys
import json
import os
from typing import Dict, List, Any
from pathlib import Path
import argparse


class SecurityScanner:
    """Comprehensive security scanning for the application."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.results = {
            "timestamp": "",
            "scans": {},
            "summary": {
                "total_issues": 0,
                "high_severity": 0,
                "medium_severity": 0,
                "low_severity": 0,
                "passed_scans": 0,
                "failed_scans": 0
            }
        }
    
    def run_pip_audit(self) -> Dict[str, Any]:
        """Run pip-audit to check for known vulnerabilities."""
        print("🔍 Running pip-audit scan...")
        
        try:
            # Run pip-audit with JSON output
            result = subprocess.run([
                sys.executable, "-m", "pip_audit",
                "--format", "json",
                "--requirement", "requirements.txt"
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                print("✅ pip-audit: No vulnerabilities found")
                return {
                    "status": "passed",
                    "vulnerabilities": [],
                    "message": "No known vulnerabilities detected"
                }
            else:
                try:
                    vulns = json.loads(result.stdout) if result.stdout else []
                    print(f"❌ pip-audit: {len(vulns)} vulnerabilities found")
                    
                    return {
                        "status": "failed",
                        "vulnerabilities": vulns,
                        "message": f"Found {len(vulns)} vulnerabilities"
                    }
                except json.JSONDecodeError:
                    return {
                        "status": "error",
                        "vulnerabilities": [],
                        "message": f"pip-audit failed: {result.stderr}"
                    }
                
        except FileNotFoundError:
            return {
                "status": "error",
                "vulnerabilities": [],
                "message": "pip-audit not installed. Run: pip install pip-audit"
            }
    
    def run_bandit(self) -> Dict[str, Any]:
        """Run bandit static security analysis."""
        print("🔍 Running bandit scan...")
        
        try:
            # Run bandit with JSON output
            result = subprocess.run([
                sys.executable, "-m", "bandit",
                "-r", "app/",
                "-f", "json",
                "-ll"  # Only show medium and high severity
            ], capture_output=True, text=True, cwd=self.project_root)
            
            try:
                bandit_output = json.loads(result.stdout) if result.stdout else {}
                issues = bandit_output.get("results", [])
                
                if not issues:
                    print("✅ bandit: No security issues found")
                    return {
                        "status": "passed",
                        "issues": [],
                        "message": "No security issues detected"
                    }
                else:
                    high_issues = [i for i in issues if i.get("issue_severity") == "HIGH"]
                    medium_issues = [i for i in issues if i.get("issue_severity") == "MEDIUM"]
                    
                    print(f"❌ bandit: {len(issues)} issues found ({len(high_issues)} high, {len(medium_issues)} medium)")
                    
                    return {
                        "status": "failed" if high_issues else "warning",
                        "issues": issues,
                        "message": f"Found {len(issues)} security issues",
                        "summary": {
                            "total": len(issues),
                            "high": len(high_issues),
                            "medium": len(medium_issues)
                        }
                    }
                    
            except json.JSONDecodeError:
                return {
                    "status": "error",
                    "issues": [],
                    "message": f"Bandit output parsing failed: {result.stderr}"
                }
                
        except FileNotFoundError:
            return {
                "status": "error", 
                "issues": [],
                "message": "bandit not installed. Run: pip install bandit"
            }
    
    def run_safety(self) -> Dict[str, Any]:
        """Run safety check for known security vulnerabilities."""
        print("🔍 Running safety scan...")
        
        try:
            # Run safety with JSON output
            result = subprocess.run([
                sys.executable, "-m", "safety",
                "check",
                "--json",
                "--requirement", "requirements.txt"
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                print("✅ safety: No known vulnerabilities found")
                return {
                    "status": "passed",
                    "vulnerabilities": [],
                    "message": "No known vulnerabilities in dependencies"
                }
            else:
                try:
                    vulns = json.loads(result.stdout) if result.stdout else []
                    print(f"❌ safety: {len(vulns)} vulnerabilities found")
                    
                    return {
                        "status": "failed",
                        "vulnerabilities": vulns,
                        "message": f"Found {len(vulns)} known vulnerabilities"
                    }
                except json.JSONDecodeError:
                    return {
                        "status": "error",
                        "vulnerabilities": [],
                        "message": f"Safety check failed: {result.stderr}"
                    }
                    
        except FileNotFoundError:
            return {
                "status": "error",
                "vulnerabilities": [],
                "message": "safety not installed. Run: pip install safety"
            }
    
    def validate_security_config(self) -> Dict[str, Any]:
        """Validate security configuration."""
        print("🔍 Validating security configuration...")
        
        issues = []
        
        # Check environment variables
        env_checks = [
            ("SECRET_KEY", "JWT secret key should be set"),
            ("CORS_ORIGINS", "CORS origins should be configured"),
            ("ENVIRONMENT", "Environment should be set"),
        ]
        
        for env_var, message in env_checks:
            if not os.getenv(env_var):
                issues.append({
                    "type": "missing_env_var",
                    "variable": env_var,
                    "message": message,
                    "severity": "medium"
                })
        
        # Check for development settings in production
        if os.getenv("ENVIRONMENT") == "production":
            if os.getenv("SECRET_KEY") == "development-secret-key-change-in-production":
                issues.append({
                    "type": "insecure_config",
                    "setting": "SECRET_KEY",
                    "message": "Using default secret key in production",
                    "severity": "high"
                })
            
            if not os.getenv("HTTPS_ONLY", "false").lower() == "true":
                issues.append({
                    "type": "insecure_config",
                    "setting": "HTTPS_ONLY", 
                    "message": "HTTPS not enforced in production",
                    "severity": "high"
                })
        
        # Check file permissions (basic check)
        sensitive_files = [
            ".env",
            "app/config/security.py"
        ]
        
        for file_path in sensitive_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                try:
                    # Check if file is readable by others (Unix-like systems)
                    import stat
                    mode = full_path.stat().st_mode
                    if mode & stat.S_IROTH:
                        issues.append({
                            "type": "file_permissions",
                            "file": file_path,
                            "message": f"File {file_path} is readable by others",
                            "severity": "medium"
                        })
                except:
                    pass  # Skip on Windows or other issues
        
        if not issues:
            print("✅ Security config: All checks passed")
            return {
                "status": "passed",
                "issues": [],
                "message": "Security configuration is valid"
            }
        else:
            high_issues = [i for i in issues if i.get("severity") == "high"]
            print(f"❌ Security config: {len(issues)} issues found ({len(high_issues)} high)")
            
            return {
                "status": "failed" if high_issues else "warning",
                "issues": issues,
                "message": f"Found {len(issues)} configuration issues"
            }
    
    def run_all_scans(self) -> Dict[str, Any]:
        """Run all security scans and return comprehensive results."""
        from datetime import datetime
        
        print("🚀 Starting comprehensive security scan...")
        print("=" * 50)
        
        self.results["timestamp"] = datetime.utcnow().isoformat()
        
        # Run all scans
        scans = {
            "pip_audit": self.run_pip_audit,
            "bandit": self.run_bandit,
            "safety": self.run_safety,
            "config_validation": self.validate_security_config
        }
        
        for scan_name, scan_func in scans.items():
            print(f"\n[{scan_name.upper()}]")
            try:
                self.results["scans"][scan_name] = scan_func()
                
                if self.results["scans"][scan_name]["status"] == "passed":
                    self.results["summary"]["passed_scans"] += 1
                else:
                    self.results["summary"]["failed_scans"] += 1
                    
            except Exception as e:
                print(f"❌ {scan_name}: Scan failed with error: {e}")
                self.results["scans"][scan_name] = {
                    "status": "error",
                    "message": f"Scan failed: {str(e)}"
                }
                self.results["summary"]["failed_scans"] += 1
        
        # Calculate summary
        self._calculate_summary()
        
        return self.results
    
    def _calculate_summary(self):
        """Calculate summary statistics."""
        total_issues = 0
        high_severity = 0
        medium_severity = 0
        low_severity = 0
        
        for scan_name, scan_result in self.results["scans"].items():
            if scan_name == "pip_audit":
                vulns = scan_result.get("vulnerabilities", [])
                total_issues += len(vulns)
                # pip-audit vulnerabilities are generally high severity
                high_severity += len(vulns)
                
            elif scan_name == "bandit":
                issues = scan_result.get("issues", [])
                total_issues += len(issues)
                for issue in issues:
                    severity = issue.get("issue_severity", "").lower()
                    if severity == "high":
                        high_severity += 1
                    elif severity == "medium":
                        medium_severity += 1
                    else:
                        low_severity += 1
                        
            elif scan_name == "safety":
                vulns = scan_result.get("vulnerabilities", [])
                total_issues += len(vulns)
                # Safety vulnerabilities are generally high severity
                high_severity += len(vulns)
                
            elif scan_name == "config_validation":
                issues = scan_result.get("issues", [])
                total_issues += len(issues)
                for issue in issues:
                    severity = issue.get("severity", "").lower()
                    if severity == "high":
                        high_severity += 1
                    elif severity == "medium":
                        medium_severity += 1
                    else:
                        low_severity += 1
        
        self.results["summary"].update({
            "total_issues": total_issues,
            "high_severity": high_severity,
            "medium_severity": medium_severity,
            "low_severity": low_severity
        })
    
    def print_summary(self):
        """Print comprehensive scan summary."""
        print("\n" + "=" * 50)
        print("🛡️  SECURITY SCAN SUMMARY")
        print("=" * 50)
        
        summary = self.results["summary"]
        
        print(f"Total Scans: {summary['passed_scans'] + summary['failed_scans']}")
        print(f"✅ Passed: {summary['passed_scans']}")
        print(f"❌ Failed: {summary['failed_scans']}")
        
        print(f"\nSecurity Issues Found:")
        print(f"🔴 High Severity: {summary['high_severity']}")
        print(f"🟡 Medium Severity: {summary['medium_severity']}")
        print(f"🔵 Low Severity: {summary['low_severity']}")
        print(f"📊 Total Issues: {summary['total_issues']}")
        
        # Overall security grade
        if summary["total_issues"] == 0:
            grade = "A+"
            status = "🎉 EXCELLENT SECURITY POSTURE"
        elif summary["high_severity"] == 0 and summary["total_issues"] <= 3:
            grade = "A"
            status = "✅ GOOD SECURITY POSTURE"
        elif summary["high_severity"] <= 2:
            grade = "B"
            status = "⚠️  NEEDS ATTENTION"
        else:
            grade = "C"
            status = "❌ CRITICAL SECURITY ISSUES"
        
        print(f"\nOverall Security Grade: {grade}")
        print(f"Status: {status}")
        
        # Recommendations
        if summary["high_severity"] > 0:
            print(f"\n🚨 URGENT: Address {summary['high_severity']} high-severity issues immediately")
        
        if summary["medium_severity"] > 0:
            print(f"⚠️  IMPORTANT: Review {summary['medium_severity']} medium-severity issues")
        
        if summary["total_issues"] == 0:
            print("🔒 All security scans passed! Application follows security best practices.")


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description="Security vulnerability scanner")
    parser.add_argument("--output", help="JSON file to save results")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    
    args = parser.parse_args()
    
    scanner = SecurityScanner(args.project_root)
    results = scanner.run_all_scans()
    scanner.print_summary()
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n📄 Detailed results saved to: {args.output}")
    
    # Exit with appropriate code
    exit_code = 0 if results["summary"]["high_severity"] == 0 else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
