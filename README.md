# Expense Tracker - FastAPI with MySQL

[![CI/CD Pipeline](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME/workflows/CI/CD%20Pipeline/badge.svg)](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME/actions)
[![Code Quality](https://img.shields.io/badge/code%20quality-ruff%20%7C%20black%20%7C%20flake8-blue)](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME/actions)
[![Test Coverage](https://img.shields.io/badge/coverage-80%25%2B-brightgreen)](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME/actions)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green)](https://fastapi.tiangolo.com/)

A FastAPI-based expense tracking application with MySQL backend database, featuring OCR receipt processing, comprehensive testing, and automated CI/CD.

## Prerequisites

- Python 3.8+
- MySQL Server 8.0+
- pip (Python package manager)

## Setup Instructions

### 1. Clone and Setup Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate the environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. MySQL Database Setup

#### Option A: Using Docker (Recommended)
```bash
# Start MySQL container
docker run --name mysql-expense-tracker \
  -e MYSQL_ROOT_PASSWORD=your_password \
  -e MYSQL_DATABASE=expense_tracker \
  -p 3306:3306 \
  -d mysql:8.0
```

#### Option B: Local MySQL Installation
1. Install MySQL Server on your system
2. Create a database named `expense_tracker`
3. Create a user with appropriate permissions

### 4. Environment Configuration

#### Generate a Secure Secret Key

First, generate a secure secret key for JWT authentication:

```bash
# Generate a secure 32-byte secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### Create Environment File

Copy the example environment file and configure it:

```bash
# Copy the example file
cp env.example .env

# Edit the .env file with your actual values
```

The `.env` file should contain:

```env
# MySQL Database Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=expense_user
MYSQL_PASSWORD=your_mysql_user_password_here
MYSQL_ROOT_PASSWORD=your_mysql_root_password_here
MYSQL_DATABASE=expense_tracker

# JWT Configuration
# Use the secure key generated above
SECRET_KEY=your_secure_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Security Notes:**
- Never commit your `.env` file to version control
- Use a strong, unique password for MySQL
- Generate a cryptographically secure secret key for JWT
- The `.env` file is already included in `.gitignore`

### 5. Initialize Database

```bash
python setup_database.py
```

This script will:
- Create the database if it doesn't exist
- Create all necessary tables
- Set up the schema for the application

### 6. Run the Application

#### Option A: Local Development
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Option B: Using Docker (Recommended for Production)
```bash
# Make sure your .env file is configured
docker-compose up --build
```

The application will be available at:
- **API Documentation**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc
- **Main Application**: http://localhost:8000

## Project Structure

```
major/
├── app/
│   ├── core/           # Security and core functionality
│   ├── dependencies/   # Database and JWT dependencies
│   ├── models/         # SQLAlchemy models
│   ├── routers/        # API routes
│   ├── schemas/        # Pydantic schemas
│   ├── templates/      # HTML templates
│   ├── database.py     # Database configuration
│   └── main.py         # FastAPI application
├── uploads/            # File uploads directory
├── config.py           # Configuration settings
├── setup_database.py   # Database initialization script
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Features

- **User Authentication**: JWT-based authentication system
- **Expense Management**: Add, view, and manage expenses
- **Budget Tracking**: Set and monitor budget limits by category
- **OCR Receipt Processing**: Intelligent receipt scanning with text extraction
- **File Uploads**: Upload and manage expense-related files
- **RESTful API**: Complete REST API with automatic documentation
- **MySQL Backend**: Robust MySQL database for data persistence
- **Automated CI/CD**: GitHub Actions pipeline with testing and deployment
- **Code Quality**: Automated linting with ruff, flake8, black, and isort
- **Security Scanning**: Bandit and safety checks for vulnerabilities
- **Test Coverage**: Comprehensive test suite with coverage reporting

## API Endpoints

- `POST /auth/signup` - User registration
- `POST /auth/login` - User authentication
- `GET /auth/me` - Get current user info
- `POST /expenses/` - Create new expense
- `GET /expenses/` - List user expenses
- `POST /budgets/` - Create budget
- `GET /budgets/` - List user budgets
- `POST /uploads/image` - Upload image files

## Security Features

### Environment Variable Configuration
- All sensitive configuration is stored in environment variables
- No hard-coded secrets in the codebase
- Uses `python-dotenv` for environment variable management
- `.env` file is excluded from version control via `.gitignore`

### JWT Authentication
- Secure JWT token generation using cryptographically secure secret keys
- Configurable token expiration times
- Password hashing using bcrypt
- Secure session management

### Database Security
- MySQL credentials stored in environment variables
- URL encoding for special characters in passwords
- Connection pooling with automatic reconnection
- Prepared statements via SQLAlchemy ORM

## Development

The application uses:
- **FastAPI** for the web framework
- **SQLAlchemy** for database ORM
- **MySQL** for data storage
- **JWT** for authentication
- **Pydantic** for data validation
- **Jinja2** for templating

## CI/CD Pipeline

This project includes a comprehensive CI/CD pipeline using GitHub Actions that runs on every push and pull request.

### Pipeline Overview

The CI/CD pipeline consists of multiple parallel jobs:

1. **Code Linting** - Code quality checks
2. **Unit Tests** - Comprehensive test suite with coverage
3. **Security Scan** - Security vulnerability scanning
4. **Docker Build & Test** - Container build and structure tests
5. **Integration Tests** - End-to-end API testing
6. **Performance Tests** - Basic performance validation

### Linting & Code Quality

The pipeline enforces code quality using multiple tools:

- **Ruff**: Fast Python linter for catching errors and style issues
- **Flake8**: Additional linting for complexity and PEP 8 compliance
- **Black**: Code formatting enforcement
- **isort**: Import sorting validation

```bash
# Run linting locally
pip install ruff flake8 black isort
ruff check app/
flake8 app/
black --check app/
isort --check-only app/
```

### Testing

Comprehensive test suite with multiple test types:

- **Unit Tests**: Individual component testing
- **Integration Tests**: API endpoint testing  
- **Authentication Tests**: Login/signup functionality
- **Receipt Processing Tests**: OCR functionality
- **Database Tests**: Data persistence validation

```bash
# Run tests locally
pip install pytest pytest-cov pytest-asyncio
pytest tests/ --cov=app --cov-report=html
```

### Test Coverage Requirements

- **Minimum Coverage**: 80%
- **Coverage Reports**: HTML, XML, and terminal output
- **Coverage Artifacts**: Uploaded to GitHub Actions for review

### Security Scanning

Automated security checks using:

- **Bandit**: Security linter for Python code
- **Safety**: Dependency vulnerability scanning

```bash
# Run security scans locally
pip install bandit safety
bandit -r app/
safety check
```

### Docker Testing

Container build and validation:

- **Multi-stage builds** for optimized images
- **Container structure tests** for validation
- **Health checks** and startup verification
- **Security scanning** of container images

### Performance Testing

Basic performance validation:

- **Response time checks** for critical endpoints
- **Load testing** with multiple concurrent requests
- **Memory and CPU monitoring** during tests

### Caching Strategy

The pipeline uses intelligent caching to speed up builds:

- **Pip dependencies** cached based on requirements.txt hash
- **Docker layer caching** for faster image builds
- **Separate cache keys** for different job types

### Artifacts & Reports

Generated artifacts include:

- **Coverage reports** (HTML and XML)
- **Security scan results** (JSON format)
- **Test results** with detailed output
- **Performance metrics** and benchmarks

### Branch Protection

Recommended branch protection rules:

- **Require status checks** from CI pipeline
- **Require up-to-date branches** before merging
- **Require pull request reviews** for main branch
- **Dismiss stale reviews** when new commits are pushed

### Local Development Setup

To run the same checks locally:

```bash
# Install all development dependencies
pip install -r requirements.txt -r requirements-test.txt

# Run the full local test suite
make test-all  # or run individual commands below

# Linting
ruff check app/
black --check app/
isort --check-only app/
flake8 app/

# Testing  
pytest tests/ --cov=app --cov-report=html

# Security
bandit -r app/
safety check

# Docker
docker build -t expense-tracker .
docker run --rm expense-tracker python -c "import app; print('OK')"
```

### CI/CD Configuration Files

- `.github/workflows/ci.yml` - Main CI/CD pipeline
- `pyproject.toml` - Tool configuration (ruff, black, isort, pytest)
- `requirements-test.txt` - Testing dependencies
- `tests/conftest.py` - Pytest configuration and fixtures

### Environment Variables for CI

The CI pipeline uses these environment variables:

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=test_password
MYSQL_DATABASE=expense_tracker_test
SECRET_KEY=test_secret_key_for_ci_testing_only
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Monitoring & Notifications

- **GitHub status checks** show pass/fail status
- **Detailed logs** for debugging failures
- **Artifact downloads** for coverage and security reports
- **Badge status** visible in README

## Docker Deployment (CD Pipeline)

The project includes a comprehensive Docker deployment pipeline that automatically builds and publishes container images.

### Automatic Deployment

The Docker deployment workflow triggers on version tags:

```bash
# Create and push a version tag to trigger deployment
git tag v1.0.0
git push origin v1.0.0
```

### Supported Container Registries

1. **Docker Hub** (`docker.io`)
2. **GitHub Container Registry** (`ghcr.io`) 
3. **AWS Elastic Container Registry** (`aws`)

### Registry Configuration

Configure deployment by setting repository secrets:

**Docker Hub:**
```bash
DOCKERHUB_USERNAME=your_username
DOCKERHUB_TOKEN=your_access_token
CONTAINER_REGISTRY=docker.io
IMAGE_NAME=expense-tracker
```

**GitHub Container Registry:**
```bash
CONTAINER_REGISTRY=ghcr.io
IMAGE_NAME=expense-tracker
# GITHUB_TOKEN is automatically provided
```

**AWS ECR:**
```bash
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
AWS_ECR_REGISTRY=123456789012.dkr.ecr.us-east-1.amazonaws.com
CONTAINER_REGISTRY=aws
IMAGE_NAME=expense-tracker
```

### Docker Features

- **Multi-architecture builds** (amd64, arm64)
- **Multi-stage builds** for optimized images
- **Security scanning** with Trivy
- **SBOM generation** for supply chain security
- **Health checks** and container testing
- **Production-ready** Nginx reverse proxy

### Production Deployment

```bash
# Pull and deploy latest image
docker pull your-registry/expense-tracker:latest
IMAGE_NAME=your-registry/expense-tracker:latest make docker-prod

# Or use docker-compose directly
IMAGE_NAME=your-registry/expense-tracker:latest \
docker-compose -f docker-compose.prod.yml up -d
```

### Docker Commands

Available make commands for Docker operations:

```bash
make docker-build     # Build Docker image
make docker-test      # Test Docker image
make docker-run       # Run single container
make docker-dev       # Development environment
make docker-prod      # Production environment
make docker-logs      # View container logs
make docker-health    # Check container health
make docker-backup    # Backup volumes
make docker-restore   # Restore from backup
```

### Container Security

- **Non-root execution** for security
- **Vulnerability scanning** in CI/CD
- **Security headers** via Nginx
- **Resource limits** and health checks
- **Read-only filesystems** where possible

See [DEPLOYMENT.md](DEPLOYMENT.md) for comprehensive deployment documentation.

## Kubernetes Deployment

The project includes comprehensive Kubernetes manifests for cloud-native deployment with proper externalization of configuration and secrets.

### Quick Deployment

Deploy to Kubernetes with a single command:

```bash
# Deploy with default configuration
kubectl apply -f k8s/

# Or use the deployment script
./scripts/k8s-deploy.sh
```

### Kubernetes Architecture

The deployment consists of:

- **Application Pods** (3 replicas) - FastAPI backend with OCR processing
- **MySQL Database** (1 replica) - Persistent data storage  
- **Nginx Proxy** (2 replicas) - Load balancing and SSL termination
- **Persistent Volumes** - Data persistence for database and uploads
- **Horizontal Pod Autoscaler** - Automatic scaling based on CPU/memory

### Configuration Management

**Secrets** (sensitive data):
```yaml
# k8s/secret.yaml
- MYSQL_ROOT_PASSWORD
- MYSQL_PASSWORD  
- SECRET_KEY
```

**ConfigMaps** (non-sensitive configuration):
```yaml
# k8s/configmap.yaml
- MYSQL_HOST=mysql-service
- MYSQL_PORT=3306
- MYSQL_USER=expense_user
- MYSQL_DATABASE=expense_tracker
- ALGORITHM=HS256
- ACCESS_TOKEN_EXPIRE_MINUTES=30
- ENVIRONMENT=production
- LOG_LEVEL=info
- WORKERS=4
```

### Environment-Specific Deployments

The project supports multiple environments using Kustomize overlays:

**Development:**
```bash
kubectl apply -k k8s/overlays/development
# Or: ./scripts/k8s-deploy.sh development
```

**Production:**
```bash
kubectl apply -k k8s/overlays/production  
# Or: ./scripts/k8s-deploy.sh production
```

### Service Architecture

```
Internet
    ↓
[LoadBalancer/Ingress]
    ↓
[Nginx Service] ←→ [Nginx Pods] (2 replicas)
    ↓
[App Service] ←→ [App Pods] (3 replicas)
    ↓
[MySQL Service] ←→ [MySQL Pod] (1 replica)
    ↓
[Persistent Volume]
```

### Networking

- **nginx-service** (LoadBalancer) - External access on port 80/443
- **expense-tracker-service** (ClusterIP) - Backend API on port 8000
- **mysql-service** (ClusterIP) - Database on port 3306

### Persistent Storage

- **mysql-data-pvc** (10Gi) - Database storage
- **expense-tracker-uploads-pvc** (5Gi) - Receipt uploads  
- **expense-tracker-logs-pvc** (2Gi) - Application logs

### Security Features

- **RBAC** with minimal permissions
- **Non-root containers** for security
- **Resource limits** and requests
- **Network policies** (optional)
- **Pod security standards** compliance

### Monitoring & Scaling

**Horizontal Pod Autoscaler:**
- **CPU threshold:** 70% 
- **Memory threshold:** 80%
- **Min replicas:** 2
- **Max replicas:** 10

**Health Checks:**
- **Liveness probes** on `/docs` endpoint
- **Readiness probes** for traffic routing
- **MySQL health checks** via `mysqladmin ping`

### Access & Management

**Check deployment status:**
```bash
./scripts/k8s-deploy.sh status
```

**View logs:**
```bash
./scripts/k8s-deploy.sh logs
# Or direct kubectl:
kubectl logs -n expense-tracker -l app=expense-tracker,component=backend
```

**Scale deployment:**
```bash
kubectl scale deployment expense-tracker-app --replicas=5 -n expense-tracker
```

**Update image:**
```bash
./scripts/k8s-deploy.sh update v1.2.0
# Or direct kubectl:
kubectl set image deployment/expense-tracker-app expense-tracker=expense-tracker:v1.2.0 -n expense-tracker
```

### Prerequisites

- **Kubernetes cluster** (1.19+)
- **kubectl** configured and connected
- **Persistent Volume** support (for database)
- **LoadBalancer** support (cloud provider or MetalLB)
- **Ingress Controller** (optional, for domain-based routing)

### Cloud Provider Setup

**AWS EKS:**
```bash
# Install AWS Load Balancer Controller
kubectl apply -k "github.com/aws/eks-charts/stable/aws-load-balancer-controller//crds?ref=master"

# Update service annotations for ALB
# See k8s/overlays/production/service-prod.yaml
```

**Google GKE:**
```bash
# GKE automatically provides LoadBalancer support
# Update ingress for Google-managed certificates
```

**Azure AKS:**
```bash
# Install nginx-ingress controller
helm install nginx-ingress ingress-nginx/ingress-nginx
```

### Configuration Steps

1. **Update secrets** in `k8s/secret.yaml`:
   ```bash
   # Encode your passwords
   echo -n "your_secure_password" | base64
   ```

2. **Customize domain** in `k8s/ingress.yaml`:
   ```yaml
   spec:
     rules:
     - host: expense-tracker.yourdomain.com
   ```

3. **Deploy:**
   ```bash
   kubectl apply -f k8s/
   ```

4. **Verify deployment:**
   ```bash
   kubectl get pods -n expense-tracker
   kubectl get services -n expense-tracker
   ```

### Troubleshooting

**Pod not starting:**
```bash
kubectl describe pod -n expense-tracker -l app=expense-tracker
kubectl logs -n expense-tracker -l app=expense-tracker
```

**Database connection issues:**
```bash
kubectl exec -it -n expense-tracker deployment/mysql -- mysql -u root -p
```

**Service not accessible:**
```bash
kubectl get service nginx-service -n expense-tracker
kubectl describe service nginx-service -n expense-tracker
```

The Kubernetes deployment provides a production-ready, scalable, and maintainable platform for running the expense tracker application in any cloud environment! ☸️

## Troubleshooting

### Common Issues

**Application won't start:**
- Ensure your `.env` file exists and contains all required variables
- Check that MySQL is running and accessible
- Verify database credentials in your `.env` file

**Database connection errors:**
- Ensure MySQL server is running
- Check that the database exists: `python setup_database.py`
- Verify MySQL credentials in your `.env` file
- For Docker: ensure the MySQL container is healthy

**JWT authentication issues:**
- Generate a new secure secret key: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- Update your `.env` file with the new SECRET_KEY
- Restart the application after changing the secret key 
