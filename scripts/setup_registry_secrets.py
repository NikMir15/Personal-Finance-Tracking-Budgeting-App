#!/usr/bin/env python3
"""
Script to help configure repository secrets for Docker deployment.
Provides guidance and validation for different container registries.
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


def check_github_cli() -> bool:
    """Check if GitHub CLI is available."""
    try:
        subprocess.run(["gh", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_repo_info() -> Optional[Dict[str, str]]:
    """Get repository information."""
    remote_url = run_command(["git", "remote", "get-url", "origin"])
    if not remote_url or "github.com" not in remote_url:
        return None
    
    if remote_url.startswith("git@github.com:"):
        repo_part = remote_url.replace("git@github.com:", "").replace(".git", "")
    elif remote_url.startswith("https://github.com/"):
        repo_part = remote_url.replace("https://github.com/", "").replace(".git", "")
    else:
        return None
    
    try:
        owner, repo = repo_part.split("/")
        return {"owner": owner, "repo": repo, "full_name": f"{owner}/{repo}"}
    except ValueError:
        return None


def list_current_secrets() -> List[str]:
    """List current repository secrets."""
    if not check_github_cli():
        return []
    
    try:
        output = run_command(["gh", "secret", "list"])
        if output:
            secrets = []
            for line in output.split('\n'):
                if line.strip():
                    secret_name = line.split('\t')[0] if '\t' in line else line.split()[0]
                    secrets.append(secret_name)
            return secrets
    except:
        pass
    
    return []


def set_secret(name: str, value: str) -> bool:
    """Set a repository secret using GitHub CLI."""
    if not check_github_cli():
        print("❌ GitHub CLI is required to set secrets")
        return False
    
    try:
        # Use echo to pipe the value to gh secret set
        process = subprocess.Popen(
            ["gh", "secret", "set", name],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=value)
        
        if process.returncode == 0:
            print(f"✅ Secret '{name}' set successfully")
            return True
        else:
            print(f"❌ Failed to set secret '{name}': {stderr}")
            return False
    except Exception as e:
        print(f"❌ Error setting secret '{name}': {e}")
        return False


def setup_docker_hub():
    """Set up Docker Hub secrets."""
    print("\n🐳 Docker Hub Configuration")
    print("=" * 40)
    
    print("Required secrets for Docker Hub deployment:")
    print("1. DOCKERHUB_USERNAME - Your Docker Hub username")
    print("2. DOCKERHUB_TOKEN - Docker Hub access token")
    print("3. CONTAINER_REGISTRY - Set to 'docker.io'")
    print("4. IMAGE_NAME - Your image name (e.g., 'expense-tracker')")
    
    username = input("\nEnter Docker Hub username: ").strip()
    if not username:
        print("❌ Username is required")
        return False
    
    print("\n📝 To create a Docker Hub access token:")
    print("1. Go to https://hub.docker.com/settings/security")
    print("2. Click 'New Access Token'")
    print("3. Give it a name and select 'Read, Write, Delete' permissions")
    print("4. Copy the token")
    
    token = input("\nEnter Docker Hub access token: ").strip()
    if not token:
        print("❌ Token is required")
        return False
    
    image_name = input("Enter image name (default: expense-tracker): ").strip()
    if not image_name:
        image_name = "expense-tracker"
    
    # Set secrets
    success = True
    success &= set_secret("DOCKERHUB_USERNAME", username)
    success &= set_secret("DOCKERHUB_TOKEN", token)
    success &= set_secret("CONTAINER_REGISTRY", "docker.io")
    success &= set_secret("IMAGE_NAME", image_name)
    
    if success:
        print(f"\n✅ Docker Hub configuration complete!")
        print(f"Images will be pushed to: {username}/{image_name}")
    
    return success


def setup_github_registry():
    """Set up GitHub Container Registry secrets."""
    print("\n📦 GitHub Container Registry Configuration")
    print("=" * 45)
    
    repo_info = get_repo_info()
    if not repo_info:
        print("❌ Unable to determine repository information")
        return False
    
    print("GitHub Container Registry uses automatic authentication.")
    print("Only these secrets are needed:")
    
    image_name = input("Enter image name (default: expense-tracker): ").strip()
    if not image_name:
        image_name = "expense-tracker"
    
    # Set secrets
    success = True
    success &= set_secret("CONTAINER_REGISTRY", "ghcr.io")
    success &= set_secret("IMAGE_NAME", image_name)
    
    if success:
        print(f"\n✅ GitHub Container Registry configuration complete!")
        print(f"Images will be pushed to: ghcr.io/{repo_info['owner']}/{image_name}")
        
        print("\n📋 Make sure your repository has the following permissions:")
        print("- Go to Settings > Actions > General")
        print("- Under 'Workflow permissions', ensure 'Read and write permissions' is selected")
        print("- Or add 'packages: write' to your workflow permissions")
    
    return success


def setup_aws_ecr():
    """Set up AWS ECR secrets."""
    print("\n☁️  AWS ECR Configuration")
    print("=" * 30)
    
    print("Required secrets for AWS ECR deployment:")
    print("1. AWS_ACCESS_KEY_ID - AWS access key")
    print("2. AWS_SECRET_ACCESS_KEY - AWS secret key")
    print("3. AWS_REGION - AWS region (e.g., us-east-1)")
    print("4. AWS_ECR_REGISTRY - ECR registry URL")
    print("5. CONTAINER_REGISTRY - Set to 'aws'")
    print("6. IMAGE_NAME - Your image name")
    
    print("\n📝 To set up AWS ECR:")
    print("1. Create an ECR repository in AWS Console")
    print("2. Create IAM user with ECR permissions")
    print("3. Generate access keys for the IAM user")
    
    access_key = input("\nEnter AWS Access Key ID: ").strip()
    if not access_key:
        print("❌ Access Key ID is required")
        return False
    
    secret_key = input("Enter AWS Secret Access Key: ").strip()
    if not secret_key:
        print("❌ Secret Access Key is required")
        return False
    
    region = input("Enter AWS Region (default: us-east-1): ").strip()
    if not region:
        region = "us-east-1"
    
    registry = input("Enter ECR Registry URL (e.g., 123456789012.dkr.ecr.us-east-1.amazonaws.com): ").strip()
    if not registry:
        print("❌ ECR Registry URL is required")
        return False
    
    image_name = input("Enter image name (default: expense-tracker): ").strip()
    if not image_name:
        image_name = "expense-tracker"
    
    # Set secrets
    success = True
    success &= set_secret("AWS_ACCESS_KEY_ID", access_key)
    success &= set_secret("AWS_SECRET_ACCESS_KEY", secret_key)
    success &= set_secret("AWS_REGION", region)
    success &= set_secret("AWS_ECR_REGISTRY", registry)
    success &= set_secret("CONTAINER_REGISTRY", "aws")
    success &= set_secret("IMAGE_NAME", image_name)
    
    if success:
        print(f"\n✅ AWS ECR configuration complete!")
        print(f"Images will be pushed to: {registry}/{image_name}")
    
    return success


def setup_optional_secrets():
    """Set up optional secrets."""
    print("\n⚙️  Optional Configuration")
    print("=" * 30)
    
    print("Optional secrets you can configure:")
    print("1. SLACK_WEBHOOK_URL - For deployment notifications")
    print("2. ALLOW_FORK_DEPLOY - Allow deployment from forks")
    
    setup_slack = input("\nDo you want to set up Slack notifications? (y/N): ").strip().lower()
    if setup_slack == 'y':
        slack_url = input("Enter Slack webhook URL: ").strip()
        if slack_url:
            set_secret("SLACK_WEBHOOK_URL", slack_url)
    
    allow_fork = input("Allow deployment from forks? (y/N): ").strip().lower()
    if allow_fork == 'y':
        set_secret("ALLOW_FORK_DEPLOY", "true")


def main():
    """Main function."""
    print("🔧 Docker Deployment Secrets Setup")
    print("=" * 40)
    
    # Check prerequisites
    repo_info = get_repo_info()
    if not repo_info:
        print("❌ This doesn't appear to be a GitHub repository")
        sys.exit(1)
    
    print(f"📁 Repository: {repo_info['full_name']}")
    
    if not check_github_cli():
        print("\n❌ GitHub CLI is required to set secrets")
        print("Install from: https://cli.github.com/")
        print("Then run: gh auth login")
        sys.exit(1)
    
    # Show current secrets
    current_secrets = list_current_secrets()
    if current_secrets:
        print(f"\n📋 Current secrets: {', '.join(current_secrets)}")
    
    # Choose registry
    print("\n🎯 Choose your container registry:")
    print("1. Docker Hub (docker.io)")
    print("2. GitHub Container Registry (ghcr.io)")
    print("3. AWS ECR")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    success = False
    if choice == "1":
        success = setup_docker_hub()
    elif choice == "2":
        success = setup_github_registry()
    elif choice == "3":
        success = setup_aws_ecr()
    else:
        print("❌ Invalid choice")
        sys.exit(1)
    
    if success:
        setup_optional_secrets()
        
        print(f"\n🎉 Configuration complete!")
        print(f"\n📝 Next steps:")
        print(f"1. Create a version tag: git tag v1.0.0")
        print(f"2. Push the tag: git push origin v1.0.0")
        print(f"3. Watch the deployment: https://github.com/{repo_info['full_name']}/actions")
        
        print(f"\n🔗 Useful links:")
        print(f"- Repository: https://github.com/{repo_info['full_name']}")
        print(f"- Actions: https://github.com/{repo_info['full_name']}/actions")
        print(f"- Settings: https://github.com/{repo_info['full_name']}/settings/secrets/actions")
    else:
        print("❌ Configuration failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
