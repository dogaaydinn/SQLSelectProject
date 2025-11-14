# Infrastructure & DevOps Documentation

> **Phase 4 Complete**: Production-ready infrastructure with CI/CD, Kubernetes, and full observability

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [CI/CD Pipeline](#cicd-pipeline)
3. [Kubernetes Architecture](#kubernetes-architecture)
4. [Monitoring & Observability](#monitoring--observability)
5. [Deployment Strategy](#deployment-strategy)
6. [Security](#security)
7. [Scaling & Performance](#scaling--performance)

---

## 🎯 Overview

This document describes the complete infrastructure and DevOps setup for the Enterprise Employee Management System.

### Infrastructure Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| **CI/CD** | GitHub Actions | Automated testing, building, and deployment |
| **Container Orchestration** | Kubernetes | Application deployment and management |
| **Monitoring** | Prometheus + Grafana | Metrics collection and visualization |
| **Load Balancing** | NGINX Ingress | Traffic management and SSL termination |
| **Auto-scaling** | HPA | Dynamic resource allocation |
| **Security** | RBAC, Secrets, Network Policies | Access control and data protection |

---

## 🚀 CI/CD Pipeline

### Workflows

#### 1. **Test Suite** (`.github/workflows/test.yml`)
- **Triggers**: Pull requests, pushes to main/develop
- **Services**: PostgreSQL 16, Redis 7
- **Steps**:
  - Unit tests with pytest
  - Integration tests
  - Performance tests
  - Code coverage (80% threshold)
  - Coverage upload to Codecov

#### 2. **Code Quality** (`.github/workflows/code-quality.yml`)
- **Linting**: Black, isort, Flake8, Pylint, MyPy
- **Security**: Bandit, Safety, pip-audit
- **Complexity**: Radon analysis
- **Outputs**: Security reports, complexity metrics

#### 3. **Build** (`.github/workflows/build.yml`)
- **Triggers**: Push to main/develop, version tags
- **Outputs**: Docker images to GitHub Container Registry
- **Features**:
  - Multi-platform builds (amd64, arm64)
  - Layer caching for faster builds
  - Trivy security scanning
  - SARIF reports to GitHub Security

#### 4. **Deploy - Development** (`.github/workflows/deploy-dev.yml`)
- **Trigger**: Push to develop branch
- **Target**: Development cluster
- **Features**:
  - Automated deployment
  - Smoke tests
  - Slack notifications

#### 5. **Deploy - Staging** (`.github/workflows/deploy-staging.yml`)
- **Trigger**: Push to main branch
- **Target**: Staging cluster
- **Features**:
  - Full integration tests
  - Performance validation

#### 6. **Deploy - Production** (`.github/workflows/deploy-prod.yml`)
- **Trigger**: Release published or manual dispatch
- **Strategy**: Blue-green deployment
- **Features**:
  - Zero-downtime deployment
  - Automatic rollback on failure
  - 5-minute stability monitoring
  - Production smoke tests

### CI/CD Flow

```
┌─────────────┐
│   Commit    │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌──────────────┐
│   Tests     │────▶│ Code Quality │
└──────┬──────┘     └──────┬───────┘
       │                    │
       └────────┬───────────┘
                ▼
         ┌─────────────┐
         │    Build    │
         └──────┬──────┘
                │
       ┌────────┼────────┐
       ▼        ▼        ▼
    ┌─────┐ ┌────────┐ ┌──────┐
    │ Dev │ │Staging │ │ Prod │
    └─────┘ └────────┘ └──────┘
```

---

## ☸️ Kubernetes Architecture

### Cluster Structure

```
┌──────────────────────────────────────────────────┐
│            NGINX Ingress Controller              │
│          (Load Balancer + SSL Termination)       │
└────────────────┬─────────────────────────────────┘
                 │
         ┌───────┴────────┐
         │                │
    ┌────▼────┐     ┌────▼────┐
    │ Service │     │ Service │
    │(ClusterIP)   │(ClusterIP)
    └────┬────┘     └────┬────┘
         │                │
    ┌────▼────────────────▼────┐
    │    API Python Pods        │
    │  (3-10 pods with HPA)     │
    └────┬──────────────────────┘
         │
    ┌────┴───────────┬──────────┐
    │                │          │
┌───▼────┐     ┌────▼────┐  ┌─▼──────┐
│Postgres│     │  Redis  │  │Prometheus
│StatefulSet   │Deployment  │ & Grafana
└─────────┘     └─────────┘  └────────┘
```

### Namespace Organization

- **Development**: `employee-mgmt-dev`
- **Staging**: `employee-mgmt-staging`
- **Production**: `employee-mgmt-prod`

### Key Resources

#### API Python Deployment
- **File**: `k8s/base/api-python/deployment.yaml`
- **Replicas**: 3 (production), auto-scaling 3-10
- **Resources**:
  - Requests: 100m CPU, 256Mi memory
  - Limits: 500m CPU, 512Mi memory
- **Probes**: Liveness, readiness, startup
- **Security**: Non-root user (UID 1000)

#### Services
- **ClusterIP**: Internal service discovery
- **LoadBalancer**: External access via NGINX
- **Session Affinity**: ClientIP with 3-hour timeout

#### Ingress
- **File**: `k8s/base/ingress/ingress.yaml`
- **Features**:
  - SSL/TLS with Let's Encrypt
  - Rate limiting (100 req/min per IP)
  - CORS configuration
  - Request timeouts (60s)
  - Body size limit (10MB)

#### HorizontalPodAutoscaler
- **File**: `k8s/base/api-python/hpa.yaml`
- **Min Replicas**: 3
- **Max Replicas**: 10
- **Metrics**:
  - CPU: Target 70%
  - Memory: Target 80%
- **Scale Down**: 50% reduction per minute (max 2 pods)
- **Scale Up**: 100% increase per 30s (max 4 pods)

#### ConfigMap
- **File**: `k8s/base/api-python/configmap.yaml`
- **Contents**: Application configuration, feature flags

#### StatefulSets
- **PostgreSQL**: 1 replica with 20Gi persistent storage
- **Redis**: Deployment with 512MB memory limit

---

## 📊 Monitoring & Observability

### Prometheus

**File**: `k8s/base/monitoring/prometheus-config.yaml`

#### Scrape Targets
- Kubernetes API server
- Kubernetes nodes
- Application pods (annotation-based)
- Python API metrics endpoint (`/metrics`)
- PostgreSQL exporter
- Redis exporter
- Node exporter

#### Alert Rules
1. **HighErrorRate**: > 5% error rate for 5 minutes
2. **HighResponseTime**: p95 > 1 second for 5 minutes
3. **PodDown**: Pod unavailable for 2 minutes
4. **HighCPUUsage**: > 80% CPU for 10 minutes
5. **HighMemoryUsage**: > 90% memory for 5 minutes
6. **DatabaseConnectionFailure**: Database errors detected

#### Retention
- **Time-series data**: 30 days
- **Evaluation interval**: 15 seconds

### Grafana

**File**: `k8s/base/monitoring/grafana.yaml`

#### Dashboards
1. **API Performance Dashboard**
   - Request rate by endpoint
   - Response time (p95, p99)
   - Error rate (5xx errors)
   - Active pods count

2. **Infrastructure Dashboard** (to be configured)
   - CPU and memory usage
   - Network I/O
   - Disk usage
   - Pod status

#### Data Sources
- Prometheus (default)
- Future: Elasticsearch for logs

### Logging (Planned)
- **ELK Stack**: Elasticsearch, Logstash, Kibana
- **Log Format**: JSON structured logging
- **Retention**: 7 days hot, 30 days warm

### Tracing (Planned)
- **Jaeger**: Distributed tracing
- **OpenTelemetry**: Instrumentation
- **Sampling**: 10% of requests

---

## 🚀 Deployment Strategy

### Development
- **Trigger**: Automatic on push to `develop`
- **Strategy**: Rolling update
- **Validation**: Smoke tests

### Staging
- **Trigger**: Automatic on push to `main`
- **Strategy**: Rolling update
- **Validation**: Full integration tests

### Production
- **Trigger**: Manual or release tag
- **Strategy**: Blue-green deployment
- **Steps**:
  1. Deploy new version (green) alongside existing (blue)
  2. Run production smoke tests on green
  3. Switch traffic to green
  4. Monitor for 5 minutes
  5. Scale down blue deployment
  6. Rollback to blue if failures detected

### Rollback Procedure
```bash
# Manual rollback
kubectl rollout undo deployment/api-python -n employee-mgmt-prod

# Rollback to specific revision
kubectl rollout undo deployment/api-python --to-revision=2 -n employee-mgmt-prod

# Check rollout status
kubectl rollout status deployment/api-python -n employee-mgmt-prod
```

---

## 🔒 Security

### RBAC
- **ServiceAccount**: `api-python`
- **Permissions**: Read ConfigMaps and Secrets
- **Namespace-scoped**: Least privilege principle

### Secrets Management
- **Kubernetes Secrets**: Base64 encoded
- **External Secrets**: Vault integration (planned)
- **Rotation**: Manual (automated rotation planned)

### Network Policies
- Ingress rules for pod-to-pod communication
- Egress rules for external services
- Default deny all policy

### Pod Security
- Run as non-root (UID 1000)
- Read-only root filesystem
- Drop all capabilities
- No privilege escalation

### Image Security
- **Scanning**: Trivy on every build
- **Registry**: GitHub Container Registry
- **Signing**: Cosign (planned)

---

## ⚡ Scaling & Performance

### Horizontal Pod Autoscaling
- **Metrics**: CPU (70%), Memory (80%)
- **Range**: 3-10 pods
- **Behavior**:
  - Scale up: Aggressive (100% per 30s)
  - Scale down: Conservative (50% per 60s)

### Vertical Pod Autoscaling (Planned)
- Automatic resource request/limit adjustment
- Based on historical usage patterns

### Database Scaling
- **Read Replicas**: 2 replicas for read operations
- **Connection Pooling**: 10-20 connections
- **Query Optimization**: Indexed queries

### Caching Strategy
- **Redis**: In-memory caching
- **TTL**: 300 seconds default
- **Invalidation**: Pattern-based
- **Hit Rate Target**: > 80%

### CDN (Planned)
- Static asset caching
- API response caching for GET requests
- Geographic distribution

---

## 📝 Quick Reference

### Useful Commands

```bash
# Check deployment status
kubectl get all -n employee-mgmt-prod

# View logs
kubectl logs -f deployment/api-python -n employee-mgmt-prod

# Execute into pod
kubectl exec -it <pod-name> -n employee-mgmt-prod -- /bin/bash

# Scale manually
kubectl scale deployment/api-python --replicas=5 -n employee-mgmt-prod

# Update image
kubectl set image deployment/api-python api-python=ghcr.io/dogaaydinn/sqlselectproject/api-python:v1.2.0 -n employee-mgmt-prod

# View HPA status
kubectl get hpa -n employee-mgmt-prod

# View resource usage
kubectl top pods -n employee-mgmt-prod
kubectl top nodes
```

### Access Services

```bash
# Port forward to local machine
kubectl port-forward svc/api-python 8000:80 -n employee-mgmt-prod
kubectl port-forward svc/grafana 3000:3000 -n employee-mgmt-prod
kubectl port-forward svc/prometheus 9090:9090 -n employee-mgmt-prod

# Access via ingress
curl https://employee-mgmt.example.com/api/v1/health
curl https://employee-mgmt.example.com/api/v1/docs
```

---

## 🎯 Success Metrics

### Phase 4 Completion Criteria ✅

- [x] CI/CD pipeline with 5 workflows
- [x] Kubernetes manifests for all components
- [x] Monitoring with Prometheus and Grafana
- [x] Auto-scaling configuration
- [x] Blue-green deployment strategy
- [x] Security best practices implemented
- [x] Documentation complete

### Performance Targets

| Metric | Target | Monitoring |
|--------|--------|------------|
| Deployment Time | < 5 minutes | GitHub Actions |
| Test Suite Runtime | < 10 minutes | CI Pipeline |
| Auto-scale Response | < 2 minutes | Prometheus |
| Alert Response | < 1 minute | Alertmanager |
| Rollback Time | < 2 minutes | Manual/Automated |

---

**Last Updated**: 2025-11-14
**Version**: 2.0.0
**Status**: Phase 4 Complete ✅
