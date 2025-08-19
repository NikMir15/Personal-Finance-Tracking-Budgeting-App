# 🚀 Docker Deployment Guide

This guide covers deploying the Expense Tracker application using Docker and the automated CI/CD pipeline.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Repository Secrets Setup](#repository-secrets-setup)
- [Supported Registries](#supported-registries)
- [Deployment Workflows](#deployment-workflows)
- [Production Deployment](#production-deployment)
- [Monitoring & Maintenance](#monitoring--maintenance)
- [Troubleshooting](#troubleshooting)

## 🏃 Quick Start

### Local Development with Docker

```bash
# Build and run locally
make docker-build
make docker-run

# Or use docker-compose
docker-compose up --build
```

### Production Deployment

1. **Tag your release:**
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. **Monitor deployment:**
   - Check GitHub Actions for build status
   - Verify image in your container registry
   - Deploy using production compose file

## 🔐 Repository Secrets Setup

Configure these secrets in your GitHub repository settings (`Settings > Secrets and variables > Actions`):

### Required Secrets

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `IMAGE_NAME` | Base image name | `expense-tracker` |
| `CONTAINER_REGISTRY` | Target registry | `docker.io`, `ghcr.io`, or `aws` |

### Docker Hub Deployment

```bash
# Required secrets for Docker Hub
DOCKERHUB_USERNAME=your_dockerhub_username
DOCKERHUB_TOKEN=your_dockerhub_access_token
```

### GitHub Container Registry

```bash
# GitHub token is automatically provided
# Just set the registry
CONTAINER_REGISTRY=ghcr.io
```

### AWS ECR Deployment

```bash
# Required secrets for AWS ECR
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
AWS_ECR_REGISTRY=123456789012.dkr.ecr.us-east-1.amazonaws.com
```

### Optional Secrets

| Secret Name | Description | Default |
|-------------|-------------|---------|
| `SLACK_WEBHOOK_URL` | Slack notifications | None |
| `ALLOW_FORK_DEPLOY` | Allow deployment from forks | `false` |

## 🏗️ Supported Registries

### 1. Docker Hub (`docker.io`)

**Setup:**
1. Create Docker Hub account
2. Generate access token
3. Set repository secrets:
   - `DOCKERHUB_USERNAME`
   - `DOCKERHUB_TOKEN`
   - `CONTAINER_REGISTRY=docker.io`

**Image Format:** `username/expense-tracker:tag`

### 2. GitHub Container Registry (`ghcr.io`)

**Setup:**
1. Set repository secret:
   - `CONTAINER_REGISTRY=ghcr.io`
2. Ensure GitHub Actions has `packages: write` permission

**Image Format:** `ghcr.io/owner/expense-tracker:tag`

### 3. AWS ECR (`aws`)

**Setup:**
1. Create ECR repository
2. Set up IAM user with ECR permissions
3. Set repository secrets:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_REGION`
   - `AWS_ECR_REGISTRY`
   - `CONTAINER_REGISTRY=aws`

**Image Format:** `account.dkr.ecr.region.amazonaws.com/expense-tracker:tag`

## 🔄 Deployment Workflows

### Automatic Deployment (Recommended)

Triggered automatically when you push version tags:

```bash
# Create and push a version tag
git tag v1.2.3
git push origin v1.2.3

# Workflow will:
# 1. Build multi-arch image (amd64, arm64)
# 2. Run security scans
# 3. Push to configured registry
# 4. Test deployed image
# 5. Send notifications
```

### Manual Deployment

Trigger deployment manually via GitHub Actions UI:

1. Go to Actions tab in your repository
2. Select "Docker Build & Deploy" workflow
3. Click "Run workflow"
4. Choose tag and registry
5. Click "Run workflow"

### Supported Tag Formats

- **Semantic versions:** `v1.0.0`, `v2.1.3` → Creates `latest`, `v1.0.0`, `v1.0` tags
- **Pre-releases:** `v1.0.0-beta.1` → Creates only the specific tag
- **Custom tags:** `feature-xyz` → Creates only the specific tag

## 🎯 Production Deployment

### 1. Environment Setup

Create production environment file:

```bash
# Copy and customize
cp env.example .env.prod

# Required production variables
MYSQL_HOST=your_mysql_host
MYSQL_USER=expense_user
MYSQL_PASSWORD=secure_password
MYSQL_DATABASE=expense_tracker
SECRET_KEY=your_super_secure_secret_key
```

### 2. SSL Certificates

For HTTPS support, place SSL certificates in `nginx/ssl/`:

```bash
nginx/ssl/
├── cert.pem    # SSL certificate
└── key.pem     # Private key
```

### 3. Deploy with Docker Compose

```bash
# Pull latest image
docker pull your-registry/expense-tracker:latest

# Deploy with production config
IMAGE_NAME=your-registry/expense-tracker:latest \
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps
```

### 4. Production Checklist

- [ ] SSL certificates configured
- [ ] Database backups scheduled
- [ ] Log rotation configured
- [ ] Monitoring alerts set up
- [ ] Resource limits configured
- [ ] Security updates scheduled

## 📊 Monitoring & Maintenance

### Health Checks

The application includes built-in health checks:

```bash
# Application health
curl http://localhost:8000/docs

# Nginx health
curl http://localhost/health

# Docker health status
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### Logs

```bash
# Application logs
docker-compose logs -f app

# Database logs
docker-compose logs -f mysql

# Nginx logs
docker-compose logs -f nginx

# All services
docker-compose logs -f
```

### Updates

```bash
# Update to new version
docker pull your-registry/expense-tracker:v1.2.3

# Update docker-compose
IMAGE_NAME=your-registry/expense-tracker:v1.2.3 \
docker-compose -f docker-compose.prod.yml up -d

# Clean up old images
docker image prune -a
```

### Backup

```bash
# Database backup
docker exec expense-tracker-mysql-prod mysqldump \
  -u root -p${MYSQL_ROOT_PASSWORD} \
  ${MYSQL_DATABASE} > backup_$(date +%Y%m%d_%H%M%S).sql

# Upload files backup
tar -czf uploads_backup_$(date +%Y%m%d_%H%M%S).tar.gz uploads/
```

## 🛡️ Security Features

### Container Security

- **Non-root user:** Application runs as `appuser`
- **Read-only filesystem:** Application files are read-only
- **Resource limits:** CPU and memory limits configured
- **Security scanning:** Trivy vulnerability scanning in CI

### Network Security

- **Rate limiting:** API endpoint rate limiting via Nginx
- **SSL/TLS:** HTTPS support with strong ciphers
- **Security headers:** HSTS, XSS protection, etc.
- **Internal network:** Isolated Docker network

### Application Security

- **Environment isolation:** Separate prod/dev configurations
- **Secret management:** Secrets via environment variables
- **Input validation:** Pydantic validation on all inputs
- **SQL injection protection:** SQLAlchemy ORM

## 🔧 Troubleshooting

### Common Issues

**1. Build Fails with "No space left on device"**
```bash
# Clean up Docker resources
docker system prune -a
docker volume prune
```

**2. Container Won't Start**
```bash
# Check logs
docker logs expense-tracker-app

# Check environment variables
docker exec expense-tracker-app env | grep MYSQL
```

**3. Database Connection Issues**
```bash
# Test MySQL connectivity
docker exec expense-tracker-mysql mysql -u root -p -e "SHOW DATABASES;"

# Check network connectivity
docker exec expense-tracker-app ping mysql
```

**4. Permission Issues**
```bash
# Fix upload directory permissions
sudo chown -R 1000:1000 uploads/
```

### Performance Tuning

**1. Increase Worker Processes**
```yaml
# In docker-compose.yml
environment:
  - WORKERS=8
```

**2. Database Optimization**
```yaml
# In docker-compose.yml mysql service
command: 
  - --innodb-buffer-pool-size=512M
  - --max-connections=200
```

**3. Nginx Caching**
```nginx
# In nginx.conf
location /static/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### Debug Mode

For debugging production issues:

```bash
# Enable debug logging
docker-compose -f docker-compose.prod.yml \
  -e LOG_LEVEL=debug up -d

# Access container shell
docker exec -it expense-tracker-app bash

# Run application in development mode
docker-compose -f docker-compose.yml up
```

## 📞 Support

For deployment support:

1. **Check logs:** Application and container logs
2. **Review documentation:** This guide and README.md
3. **GitHub Issues:** Report bugs and ask questions
4. **CI/CD Status:** Check GitHub Actions for build issues

## 🎯 Best Practices

1. **Always use tagged releases** for production
2. **Test deployments** in staging environment first
3. **Monitor resource usage** and scale as needed
4. **Keep secrets secure** and rotate regularly
5. **Backup data regularly** and test restore procedures
6. **Update base images** regularly for security patches
7. **Use specific image tags** instead of `latest` in production

---

Happy Deploying! 🚀
