#!/usr/bin/env python3
"""
Script to check GitHub Actions CI status for the current repository.
Useful for monitoring CI pipeline health and getting quick status updates.
"""

import json
import os
import subprocess
import sys
from typing import Dict, List, Optional


def run_command(cmd: List[str]) -> Optional[str]:
    """Run a shell command and return output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {' '.join(cmd)}")
        print(f"Error: {e.stderr}")
        return None


def get_repo_info() -> Optional[Dict[str, str]]:
    """Get repository information from git."""
    # Get remote URL
    remote_url = run_command(["git", "remote", "get-url", "origin"])
    if not remote_url:
        return None
    
    # Parse GitHub repo from URL
    if "github.com" not in remote_url:
        print("❌ Not a GitHub repository")
        return None
    
    # Extract owner/repo from URL
    if remote_url.startswith("git@github.com:"):
        repo_part = remote_url.replace("git@github.com:", "").replace(".git", "")
    elif remote_url.startswith("https://github.com/"):
        repo_part = remote_url.replace("https://github.com/", "").replace(".git", "")
    else:
        print("❌ Unable to parse GitHub repository URL")
        return None
    
    try:
        owner, repo = repo_part.split("/")
        return {"owner": owner, "repo": repo}
    except ValueError:
        print("❌ Invalid repository format")
        return None


def get_current_branch() -> Optional[str]:
    """Get current git branch."""
    return run_command(["git", "branch", "--show-current"])


def check_github_cli() -> bool:
    """Check if GitHub CLI is available."""
    try:
        subprocess.run(["gh", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_workflow_status(owner: str, repo: str, branch: str) -> Optional[Dict]:
    """Get workflow status using GitHub CLI."""
    if not check_github_cli():
        print("ℹ️  GitHub CLI not available. Install with: https://cli.github.com/")
        return None
    
    cmd = [
        "gh", "run", "list",
        "--repo", f"{owner}/{repo}",
        "--branch", branch,
        "--limit", "5",
        "--json", "status,conclusion,workflowName,createdAt,url,headBranch"
    ]
    
    output = run_command(cmd)
    if not output:
        return None
    
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        print("❌ Failed to parse GitHub API response")
        return None


def format_status(status: str, conclusion: Optional[str]) -> str:
    """Format workflow status with appropriate emoji."""
    if status == "completed":
        if conclusion == "success":
            return "✅ Success"
        elif conclusion == "failure":
            return "❌ Failed"
        elif conclusion == "cancelled":
            return "🚫 Cancelled"
        else:
            return f"⚠️  {conclusion or 'Unknown'}"
    elif status == "in_progress":
        return "🔄 Running"
    elif status == "queued":
        return "⏳ Queued"
    else:
        return f"❓ {status}"


def main():
    """Main function."""
    print("🔍 Checking CI/CD Pipeline Status")
    print("=" * 40)
    
    # Get repository info
    repo_info = get_repo_info()
    if not repo_info:
        print("❌ Unable to determine repository information")
        sys.exit(1)
    
    owner = repo_info["owner"]
    repo = repo_info["repo"]
    
    # Get current branch
    branch = get_current_branch()
    if not branch:
        print("❌ Unable to determine current branch")
        sys.exit(1)
    
    print(f"📁 Repository: {owner}/{repo}")
    print(f"🌿 Branch: {branch}")
    print()
    
    # Get workflow status
    workflows = get_workflow_status(owner, repo, branch)
    if not workflows:
        print("❌ Unable to fetch workflow status")
        print("💡 Make sure you're authenticated with GitHub CLI: gh auth login")
        sys.exit(1)
    
    if not workflows:
        print("ℹ️  No recent workflow runs found")
        return
    
    print(f"📊 Recent Workflow Runs ({len(workflows)} found):")
    print("-" * 50)
    
    for i, workflow in enumerate(workflows, 1):
        status_str = format_status(workflow["status"], workflow.get("conclusion"))
        workflow_name = workflow["workflowName"]
        created_at = workflow["createdAt"][:19].replace("T", " ")
        url = workflow["url"]
        
        print(f"{i}. {status_str}")
        print(f"   📋 Workflow: {workflow_name}")
        print(f"   📅 Started: {created_at}")
        print(f"   🔗 URL: {url}")
        print()
    
    # Summary
    latest = workflows[0] if workflows else None
    if latest:
        latest_status = format_status(latest["status"], latest.get("conclusion"))
        print(f"🎯 Latest Status: {latest_status}")
        
        if latest["status"] == "completed" and latest.get("conclusion") == "success":
            print("🎉 CI/CD Pipeline is healthy!")
        elif latest["status"] == "in_progress":
            print("⏳ CI/CD Pipeline is currently running...")
        else:
            print("⚠️  CI/CD Pipeline needs attention")
    
    print()
    print("💡 Pro Tips:")
    print("   • Run 'make ci-local' to test changes locally before pushing")
    print("   • Use 'make check-all' to run the same checks as CI")
    print("   • Check the Actions tab on GitHub for detailed logs")


if __name__ == "__main__":
    main()
