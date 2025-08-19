# Kubernetes Deployment Guide

This directory contains comprehensive Kubernetes manifests for deploying the Expense Tracker application in a cloud-native environment.

## 📋 Quick Start

### 1. Prerequisites

- Kubernetes cluster (v1.19+)
- `kubectl` configured and connected
- Persistent Volume support
- LoadBalancer support (cloud provider or MetalLB)

### 2. Update Secrets

**IMPORTANT:** Update the secrets in `secret.yaml` before deploying:

```bash
# Generate base64 encoded values
echo -n "your_secure_mysql_password" | base64
echo -n "your_super_secure_jwt_secret" | base64

# Update k8s/secret.yaml with these values
```

### 3. Deploy

```bash
# Simple deployment
kubectl apply -f k8s/

# Or use the deployment script
./scripts/k8s-deploy.sh

# Environment-specific deployment
kubectl apply -k k8s/overlays/production
```

### 4. Verify

```bash
kubectl get pods -n expense-tracker
kubectl get services -n expense-tracker
```

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │     Ingress     │    │   cert-manager  │
│   (nginx-svc)   │ ←→ │  (optional)     │ ←→ │   (optional)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Nginx Proxy    │    │  App Backend    │    │  MySQL Database │
│   (2 replicas)  │ ←→ │  (3 replicas)   │ ←→ │   (1 replica)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  ConfigMap      │    │  Uploads PVC    │    │  MySQL Data PVC │
│  (nginx.conf)   │    │   (5Gi RWX)     │    │   (10Gi RWO)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📁 File Structure

```
k8s/
├── namespace.yaml           # Namespace definition
├── secret.yaml             # Sensitive configuration
├── configmap.yaml          # Non-sensitive configuration
├── rbac.yaml               # Service account and permissions
├── pvc.yaml                # Persistent volume claims
├── deployment.yaml         # Application deployments
├── service.yaml            # Service definitions
├── ingress.yaml            # Ingress configuration
├── hpa.yaml                # Horizontal pod autoscaler
├── kustomization.yaml      # Kustomize base configuration
├── patches/                # Kustomize patches
│   └── resource-limits.yaml
└── overlays/               # Environment-specific configurations
    ├── development/
    │   ├── kustomization.yaml
    │   ├── deployment-dev.yaml
    │   └── service-dev.yaml
    └── production/
        ├── kustomization.yaml
        ├── deployment-prod.yaml
        ├── service-prod.yaml
        └── ingress-prod.yaml
```

## 🔐 Configuration Management

### Secrets (Sensitive Data)

Located in `secret.yaml` - **Update these before deploying:**

```yaml
# Base64 encoded values
MYSQL_ROOT_PASSWORD: <base64_encoded_password>
MYSQL_PASSWORD: <base64_encoded_password>
SECRET_KEY: <base64_encoded_jwt_secret>
```

**To encode values:**
```bash
echo -n "your_actual_password" | base64
```

### ConfigMaps (Non-sensitive Configuration)

Located in `configmap.yaml`:

```yaml
# Application configuration
MYSQL_HOST: "mysql-service"
MYSQL_PORT: "3306"
MYSQL_USER: "expense_user"
MYSQL_DATABASE: "expense_tracker"
ALGORITHM: "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: "30"
ENVIRONMENT: "production"
LOG_LEVEL: "info"
WORKERS: "4"
```

## 🌍 Environment-Specific Deployments

### Development Environment

**Features:**
- Reduced resource requests/limits
- Single replica for most services
- NodePort service for easy access
- Debug logging enabled

**Deploy:**
```bash
kubectl apply -k k8s/overlays/development
# Or: ./scripts/k8s-deploy.sh development
```

**Access:**
```bash
# If using NodePort
kubectl get service nginx-service -n expense-tracker
# Access via http://node-ip:node-port
```

### Production Environment

**Features:**
- Optimized resource allocation
- Multiple replicas for high availability
- LoadBalancer service
- Production logging
- SSL/TLS configuration

**Deploy:**
```bash
kubectl apply -k k8s/overlays/production
# Or: ./scripts/k8s-deploy.sh production
```

## 🔧 Service Configuration

### Application Service (expense-tracker-service)

- **Type:** ClusterIP
- **Port:** 8000
- **Purpose:** Backend API access

### MySQL Service (mysql-service)

- **Type:** ClusterIP
- **Port:** 3306
- **Purpose:** Database access

### Nginx Service (nginx-service)

- **Type:** LoadBalancer (configurable)
- **Ports:** 80, 443
- **Purpose:** External access and load balancing

### Headless Service (expense-tracker-headless)

- **Type:** ClusterIP (headless)
- **Purpose:** Service discovery for internal communications

## 💾 Persistent Storage

### MySQL Data (mysql-data-pvc)

- **Size:** 10Gi
- **Access Mode:** ReadWriteOnce
- **Purpose:** Database storage

### Uploads Storage (expense-tracker-uploads-pvc)

- **Size:** 5Gi
- **Access Mode:** ReadWriteMany
- **Purpose:** Receipt file storage

### Logs Storage (expense-tracker-logs-pvc)

- **Size:** 2Gi
- **Access Mode:** ReadWriteMany
- **Purpose:** Application logs

## 🚀 Scaling & Performance

### Horizontal Pod Autoscaler (HPA)

**Application Pods:**
- **Min Replicas:** 2
- **Max Replicas:** 10
- **CPU Target:** 70%
- **Memory Target:** 80%

**Nginx Pods:**
- **Min Replicas:** 1
- **Max Replicas:** 5
- **CPU Target:** 60%

### Resource Allocation

**Application Container:**
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

**MySQL Container:**
```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "500m"
```

## 🌐 Ingress & SSL

### Basic Ingress

For simple HTTP access:

```yaml
# k8s/ingress.yaml - Simple configuration
rules:
- http:
    paths:
    - path: /
      pathType: Prefix
      backend:
        service:
          name: nginx-service
          port:
            number: 80
```

### Production Ingress with SSL

For HTTPS with custom domain:

```yaml
# k8s/overlays/production/ingress-prod.yaml
spec:
  tls:
  - hosts:
    - expense-tracker.yourdomain.com
    secretName: expense-tracker-tls
  rules:
  - host: expense-tracker.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: nginx-service
            port:
              number: 80
```

### SSL Certificate Management

**Using cert-manager (recommended):**

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.12.0/cert-manager.yaml

# Create ClusterIssuer
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

## 🔍 Monitoring & Debugging

### Check Pod Status

```bash
kubectl get pods -n expense-tracker -o wide
kubectl describe pod <pod-name> -n expense-tracker
```

### View Logs

```bash
# Application logs
kubectl logs -n expense-tracker -l app=expense-tracker,component=backend -f

# Database logs
kubectl logs -n expense-tracker -l app=expense-tracker,component=database -f

# Nginx logs
kubectl logs -n expense-tracker -l app=expense-tracker,component=proxy -f
```

### Debug Services

```bash
# Check service endpoints
kubectl get endpoints -n expense-tracker

# Test internal connectivity
kubectl run debug --image=busybox --rm -it --restart=Never -- /bin/sh
# Inside the pod:
# nslookup mysql-service.expense-tracker.svc.cluster.local
# wget -qO- http://expense-tracker-service.expense-tracker.svc.cluster.local:8000/docs
```

### Database Access

```bash
# Connect to MySQL
kubectl exec -it -n expense-tracker deployment/mysql -- mysql -u root -p

# Port forward for external access
kubectl port-forward -n expense-tracker service/mysql-service 3306:3306
```

## 🏢 Cloud Provider Specifics

### AWS EKS

**LoadBalancer Annotations:**
```yaml
annotations:
  service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
  service.beta.kubernetes.io/aws-load-balancer-ssl-cert: "arn:aws:acm:region:account:certificate/cert-id"
```

**Storage Class:**
```yaml
storageClassName: gp3
```

### Google GKE

**LoadBalancer Annotations:**
```yaml
annotations:
  cloud.google.com/load-balancer-type: "External"
```

**Storage Class:**
```yaml
storageClassName: standard-rwo
```

### Azure AKS

**LoadBalancer Annotations:**
```yaml
annotations:
  service.beta.kubernetes.io/azure-load-balancer-internal: "false"
```

**Storage Class:**
```yaml
storageClassName: managed-premium
```

## 🔧 Customization

### Update Image Version

```bash
# Using kubectl
kubectl set image deployment/expense-tracker-app expense-tracker=expense-tracker:v1.2.0 -n expense-tracker

# Using kustomize
# Edit kustomization.yaml:
images:
- name: expense-tracker
  newTag: v1.2.0
```

### Modify Resource Limits

Edit `patches/resource-limits.yaml` or environment-specific deployment files.

### Add Environment Variables

Add to `configmap.yaml` or `secret.yaml` depending on sensitivity.

## 🆘 Troubleshooting

### Pod Startup Issues

```bash
# Check events
kubectl get events -n expense-tracker --sort-by='.lastTimestamp'

# Check pod status
kubectl describe pod <pod-name> -n expense-tracker

# Check resource constraints
kubectl top pods -n expense-tracker
```

### Service Discovery Issues

```bash
# Check DNS resolution
kubectl run debug --image=busybox --rm -it --restart=Never -- nslookup mysql-service.expense-tracker.svc.cluster.local

# Check service endpoints
kubectl get endpoints mysql-service -n expense-tracker
```

### Storage Issues

```bash
# Check PVC status
kubectl get pvc -n expense-tracker

# Check storage class
kubectl get storageclass

# Check persistent volumes
kubectl get pv
```

### Network Issues

```bash
# Check ingress status
kubectl get ingress -n expense-tracker
kubectl describe ingress expense-tracker-ingress -n expense-tracker

# Check load balancer
kubectl get service nginx-service -n expense-tracker
```

## 📚 Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Kustomize Documentation](https://kustomize.io/)
- [cert-manager Documentation](https://cert-manager.io/docs/)
- [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/)

## 🎯 Production Checklist

- [ ] Update all secrets with secure values
- [ ] Configure proper domain names in ingress
- [ ] Set up SSL certificates
- [ ] Configure backup for persistent volumes
- [ ] Set up monitoring and alerting
- [ ] Configure resource limits appropriately
- [ ] Test disaster recovery procedures
- [ ] Set up log aggregation
- [ ] Configure network policies (if required)
- [ ] Review security policies and RBAC
