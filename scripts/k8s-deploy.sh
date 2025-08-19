#!/bin/bash
# Kubernetes Deployment Script for Expense Tracker
# Usage: ./k8s-deploy.sh [environment] [operation]
# Environment: development, production, or default
# Operation: apply, delete, status, logs

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
K8S_DIR="$PROJECT_ROOT/k8s"

# Default values
ENVIRONMENT="${1:-default}"
OPERATION="${2:-apply}"
NAMESPACE="expense-tracker"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check kustomize (optional)
    if command -v kustomize &> /dev/null; then
        log_info "Kustomize found: $(kustomize version --short)"
    else
        log_warning "Kustomize not found. Using kubectl built-in kustomization."
    fi
    
    # Check cluster connection
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

create_namespace() {
    log_info "Creating namespace: $NAMESPACE"
    kubectl apply -f "$K8S_DIR/namespace.yaml" || true
    log_success "Namespace created/updated"
}

apply_secrets() {
    log_info "Applying secrets..."
    log_warning "Make sure to update the secrets in k8s/secret.yaml with your actual values!"
    
    # Check if secrets need to be updated
    if kubectl get secret expense-tracker-secrets -n "$NAMESPACE" &> /dev/null; then
        log_warning "Secrets already exist. Use 'kubectl delete secret expense-tracker-secrets -n $NAMESPACE' to recreate."
    fi
    
    kubectl apply -f "$K8S_DIR/secret.yaml"
    log_success "Secrets applied"
}

apply_manifests() {
    log_info "Applying Kubernetes manifests for environment: $ENVIRONMENT"
    
    case $ENVIRONMENT in
        "development"|"dev")
            if [[ -d "$K8S_DIR/overlays/development" ]]; then
                kubectl apply -k "$K8S_DIR/overlays/development"
            else
                log_warning "Development overlay not found, using base manifests"
                kubectl apply -k "$K8S_DIR"
            fi
            ;;
        "production"|"prod")
            if [[ -d "$K8S_DIR/overlays/production" ]]; then
                kubectl apply -k "$K8S_DIR/overlays/production"
            else
                log_warning "Production overlay not found, using base manifests"
                kubectl apply -k "$K8S_DIR"
            fi
            ;;
        "default"|*)
            kubectl apply -k "$K8S_DIR"
            ;;
    esac
    
    log_success "Manifests applied successfully"
}

delete_manifests() {
    log_info "Deleting Kubernetes manifests for environment: $ENVIRONMENT"
    
    case $ENVIRONMENT in
        "development"|"dev")
            if [[ -d "$K8S_DIR/overlays/development" ]]; then
                kubectl delete -k "$K8S_DIR/overlays/development" --ignore-not-found=true
            else
                kubectl delete -k "$K8S_DIR" --ignore-not-found=true
            fi
            ;;
        "production"|"prod")
            if [[ -d "$K8S_DIR/overlays/production" ]]; then
                kubectl delete -k "$K8S_DIR/overlays/production" --ignore-not-found=true
            else
                kubectl delete -k "$K8S_DIR" --ignore-not-found=true
            fi
            ;;
        "default"|*)
            kubectl delete -k "$K8S_DIR" --ignore-not-found=true
            ;;
    esac
    
    log_success "Manifests deleted"
}

show_status() {
    log_info "Checking deployment status..."
    
    echo
    log_info "Namespace status:"
    kubectl get namespace "$NAMESPACE" || log_warning "Namespace not found"
    
    echo
    log_info "Pod status:"
    kubectl get pods -n "$NAMESPACE" -o wide || log_warning "No pods found"
    
    echo
    log_info "Service status:"
    kubectl get services -n "$NAMESPACE" || log_warning "No services found"
    
    echo
    log_info "Deployment status:"
    kubectl get deployments -n "$NAMESPACE" || log_warning "No deployments found"
    
    echo
    log_info "Ingress status:"
    kubectl get ingress -n "$NAMESPACE" || log_warning "No ingress found"
    
    echo
    log_info "PVC status:"
    kubectl get pvc -n "$NAMESPACE" || log_warning "No PVCs found"
    
    echo
    log_info "HPA status:"
    kubectl get hpa -n "$NAMESPACE" || log_warning "No HPAs found"
}

show_logs() {
    log_info "Showing recent logs..."
    
    echo
    log_info "Application logs:"
    kubectl logs -n "$NAMESPACE" -l app=expense-tracker,component=backend --tail=50 || log_warning "No application logs found"
    
    echo
    log_info "Database logs:"
    kubectl logs -n "$NAMESPACE" -l app=expense-tracker,component=database --tail=20 || log_warning "No database logs found"
    
    echo
    log_info "Proxy logs:"
    kubectl logs -n "$NAMESPACE" -l app=expense-tracker,component=proxy --tail=20 || log_warning "No proxy logs found"
}

wait_for_deployment() {
    log_info "Waiting for deployments to be ready..."
    
    # Wait for application deployment
    kubectl wait --for=condition=available --timeout=300s deployment/expense-tracker-app -n "$NAMESPACE" || true
    
    # Wait for database deployment
    kubectl wait --for=condition=available --timeout=300s deployment/mysql -n "$NAMESPACE" || true
    
    # Wait for proxy deployment
    kubectl wait --for=condition=available --timeout=300s deployment/nginx-proxy -n "$NAMESPACE" || true
    
    log_success "Deployments are ready!"
}

show_access_info() {
    log_info "Access information:"
    
    # Get service information
    SERVICE_TYPE=$(kubectl get service nginx-service -n "$NAMESPACE" -o jsonpath='{.spec.type}' 2>/dev/null || echo "Not found")
    
    case $SERVICE_TYPE in
        "LoadBalancer")
            EXTERNAL_IP=$(kubectl get service nginx-service -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "Pending")
            if [[ "$EXTERNAL_IP" == "Pending" || -z "$EXTERNAL_IP" ]]; then
                EXTERNAL_IP=$(kubectl get service nginx-service -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "Pending")
            fi
            
            if [[ "$EXTERNAL_IP" != "Pending" && -n "$EXTERNAL_IP" ]]; then
                echo "  🌐 Application URL: http://$EXTERNAL_IP"
                echo "  📚 API Documentation: http://$EXTERNAL_IP/docs"
            else
                echo "  ⏳ LoadBalancer IP is pending. Run this script with 'status' to check later."
            fi
            ;;
        "NodePort")
            NODE_PORT=$(kubectl get service nginx-service -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "Unknown")
            NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}' 2>/dev/null || echo "localhost")
            if [[ -z "$NODE_IP" ]]; then
                NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}' 2>/dev/null || echo "localhost")
            fi
            echo "  🌐 Application URL: http://$NODE_IP:$NODE_PORT"
            echo "  📚 API Documentation: http://$NODE_IP:$NODE_PORT/docs"
            ;;
        "ClusterIP")
            echo "  🔒 Service is ClusterIP only. Use port-forward to access:"
            echo "      kubectl port-forward -n $NAMESPACE service/nginx-service 8080:80"
            echo "      Then access: http://localhost:8080"
            ;;
        *)
            echo "  ❓ Service type unknown or service not found"
            ;;
    esac
    
    # Check for ingress
    INGRESS_HOST=$(kubectl get ingress -n "$NAMESPACE" -o jsonpath='{.items[0].spec.rules[0].host}' 2>/dev/null || echo "")
    if [[ -n "$INGRESS_HOST" ]]; then
        echo "  🌍 Ingress URL: https://$INGRESS_HOST (if DNS is configured)"
    fi
}

update_image() {
    local image_tag="${3:-latest}"
    log_info "Updating image to: expense-tracker:$image_tag"
    
    kubectl set image deployment/expense-tracker-app expense-tracker=expense-tracker:$image_tag -n "$NAMESPACE"
    kubectl rollout status deployment/expense-tracker-app -n "$NAMESPACE"
    
    log_success "Image updated successfully"
}

# Main script logic
main() {
    echo "🚀 Expense Tracker Kubernetes Deployment"
    echo "========================================"
    echo "Environment: $ENVIRONMENT"
    echo "Operation: $OPERATION"
    echo "Namespace: $NAMESPACE"
    echo

    check_prerequisites

    case $OPERATION in
        "apply"|"deploy")
            create_namespace
            apply_secrets
            apply_manifests
            wait_for_deployment
            show_status
            show_access_info
            ;;
        "delete"|"destroy")
            delete_manifests
            log_success "Resources deleted"
            ;;
        "status"|"info")
            show_status
            show_access_info
            ;;
        "logs")
            show_logs
            ;;
        "update")
            update_image "$@"
            ;;
        *)
            log_error "Unknown operation: $OPERATION"
            echo "Available operations: apply, delete, status, logs, update"
            exit 1
            ;;
    esac
}

# Help function
show_help() {
    cat << EOF
Kubernetes Deployment Script for Expense Tracker

Usage: $0 [environment] [operation] [args...]

Environments:
  default      - Base configuration
  development  - Development environment with reduced resources
  production   - Production environment with optimized settings

Operations:
  apply        - Deploy the application (default)
  delete       - Delete all resources
  status       - Show deployment status
  logs         - Show recent logs
  update TAG   - Update image to specified tag

Examples:
  $0                           # Deploy with default configuration
  $0 development apply         # Deploy development environment
  $0 production status         # Check production status
  $0 default logs              # Show logs
  $0 production update v1.2.0  # Update production to v1.2.0

Prerequisites:
  - kubectl configured and connected to cluster
  - Sufficient permissions to create resources
  - Updated secrets in k8s/secret.yaml

EOF
}

# Parse arguments
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    show_help
    exit 0
fi

# Run main function
main "$@"
