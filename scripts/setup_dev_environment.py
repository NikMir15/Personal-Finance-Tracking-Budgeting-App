#!/usr/bin/env python3
"""
Development environment setup script.
Automates the setup process for new developers or CI environments.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, check=True, capture_output=False):
    """Run a shell command."""
    print(f"🔧 Running: {cmd}")
    result = subprocess.run(cmd, shell=True, check=check, capture_output=capture_output, text=True)
    if capture_output:
        return result.stdout.strip()
    return result.returncode == 0


def check_python_version():
    """Check Python version."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ is required")
        sys.exit(1)
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")


def check_pip():
    """Check pip availability."""
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], check=True, capture_output=True)
        print("✅ pip is available")
        return True
    except subprocess.CalledProcessError:
        print("❌ pip is not available")
        return False


def setup_virtual_environment():
    """Set up virtual environment if it doesn't exist."""
    venv_path = Path("venv")
    if venv_path.exists():
        print("✅ Virtual environment already exists")
        return True
    
    print("🔧 Creating virtual environment...")
    success = run_command(f"{sys.executable} -m venv venv")
    if success:
        print("✅ Virtual environment created")
        return True
    else:
        print("❌ Failed to create virtual environment")
        return False


def install_dependencies():
    """Install all dependencies."""
    # Determine pip command based on OS
    if os.name == 'nt':  # Windows
        pip_cmd = "venv\\Scripts\\pip"
    else:  # Unix/Linux/macOS
        pip_cmd = "venv/bin/pip"
    
    # Upgrade pip first
    print("🔧 Upgrading pip...")
    run_command(f"{pip_cmd} install --upgrade pip")
    
    # Install production dependencies
    print("🔧 Installing production dependencies...")
    run_command(f"{pip_cmd} install -r requirements.txt")
    
    # Install development dependencies
    print("🔧 Installing development dependencies...")
    run_command(f"{pip_cmd} install -r requirements-test.txt")
    
    print("✅ Dependencies installed")


def setup_environment_file():
    """Set up .env file from template."""
    env_file = Path(".env")
    env_example = Path("env.example")
    
    if env_file.exists():
        print("✅ .env file already exists")
        return
    
    if env_example.exists():
        print("🔧 Creating .env file from template...")
        # Copy template and modify for development
        with open(env_example) as f:
            content = f.read()
        
        # Set development defaults
        content = content.replace(
            "MYSQL_PASSWORD=your_mysql_user_password_here",
            "MYSQL_PASSWORD=dev_password"
        )
        content = content.replace(
            "SECRET_KEY=your_secure_secret_key_here",
            "SECRET_KEY=dev_secret_key_change_in_production"
        )
        
        with open(env_file, "w") as f:
            f.write(content)
        
        print("✅ .env file created with development defaults")
        print("⚠️  Please review and update .env file with your actual values")
    else:
        print("⚠️  env.example not found, you'll need to create .env manually")


def check_docker():
    """Check if Docker is available."""
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
        print("✅ Docker is available")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  Docker not found (optional for development)")
        return False


def setup_git_hooks():
    """Set up git pre-commit hooks."""
    git_hooks_dir = Path(".git/hooks")
    if not git_hooks_dir.exists():
        print("⚠️  Not a git repository, skipping git hooks setup")
        return
    
    pre_commit_hook = git_hooks_dir / "pre-commit"
    
    if pre_commit_hook.exists():
        print("✅ Git pre-commit hook already exists")
        return
    
    hook_content = """#!/bin/bash
# Pre-commit hook for Expense Tracker
echo "🔍 Running pre-commit checks..."

# Run quick linting
make quick-lint
if [ $? -ne 0 ]; then
    echo "❌ Linting failed. Fix issues before committing."
    exit 1
fi

# Run quick tests
make quick-test
if [ $? -ne 0 ]; then
    echo "❌ Tests failed. Fix issues before committing."
    exit 1
fi

echo "✅ Pre-commit checks passed!"
"""
    
    with open(pre_commit_hook, "w") as f:
        f.write(hook_content)
    
    # Make executable
    os.chmod(pre_commit_hook, 0o755)
    print("✅ Git pre-commit hooks installed")


def test_installation():
    """Test the installation."""
    print("🧪 Testing installation...")
    
    # Test imports
    test_script = """
import sys
sys.path.insert(0, '.')

try:
    from app.main import app
    print("✅ FastAPI app imports successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

try:
    import pytest
    print("✅ pytest is available")
except ImportError:
    print("❌ pytest not available")
    
try:
    import ruff
    print("✅ ruff is available")
except ImportError:
    print("❌ ruff not available")

print("✅ Installation test passed!")
"""
    
    # Determine python command
    if os.name == 'nt':  # Windows
        python_cmd = "venv\\Scripts\\python"
    else:  # Unix/Linux/macOS
        python_cmd = "venv/bin/python"
    
    # Write test script to temp file and run it
    with open("temp_test.py", "w") as f:
        f.write(test_script)
    
    try:
        result = run_command(f"{python_cmd} temp_test.py")
        os.remove("temp_test.py")
        return result
    except:
        os.remove("temp_test.py")
        return False


def main():
    """Main setup function."""
    print("🚀 Expense Tracker - Development Environment Setup")
    print("=" * 50)
    
    # Check prerequisites
    print("\n📋 Checking prerequisites...")
    check_python_version()
    
    if not check_pip():
        sys.exit(1)
    
    # Setup steps
    print("\n🔧 Setting up development environment...")
    
    if not setup_virtual_environment():
        sys.exit(1)
    
    install_dependencies()
    setup_environment_file()
    check_docker()
    setup_git_hooks()
    
    # Test installation
    print("\n🧪 Testing installation...")
    if test_installation():
        print("\n🎉 Development environment setup complete!")
        print("\n📝 Next steps:")
        print("   1. Review and update .env file with your database credentials")
        print("   2. Set up MySQL database (see README.md)")
        print("   3. Run 'make setup-db' to initialize the database")
        print("   4. Run 'make run-dev' to start the development server")
        print("   5. Run 'make test' to ensure everything is working")
        print("\n💡 Available commands:")
        print("   make help          - Show all available commands")
        print("   make check-all     - Run all quality checks")
        print("   make ci-local      - Simulate CI pipeline locally")
    else:
        print("❌ Installation test failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
