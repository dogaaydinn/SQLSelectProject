# Production Deployment Guide

> **Target**: Production-Ready Kubernetes Deployment
> **Level**: Senior Software Engineer
> **Cloud Providers**: AWS, GCP, Azure

---

## Pre-Deployment Checklist

### Security Requirements
- [ ] All secrets stored in environment variables or secrets manager
- [ ] SECRET_KEY and JWT_SECRET changed from defaults
- [ ] HTTPS/TLS certificates configured
- [ ] Database credentials rotated
- [ ] API keys secured in vault
- [ ] CORS origins restricted to production domains
- [ ] Allowed hosts configured (no wildcards)
- [ ] Debug mode disabled
- [ ] API documentation disabled or protected
- [ ] Rate limiting enabled
- [ ] Security headers configured
- [ ] Input validation tested
- [ ] SQL injection tests passed
- [ ] XSS protection verified
- [ ] CSRF tokens implemented (for web forms)
- [ ] Account lockout mechanism tested

### Performance Requirements
- [ ] Database connection pooling configured
- [ ] Redis cache warmed up
- [ ] CDN configured for static assets
- [ ] Database indexes optimized
- [ ] Query performance tested
- [ ] Load testing completed (5000+ req/s)
- [ ] Response time < 100ms (p95)
- [ ] Memory usage profiled
- [ ] CPU usage optimized
- [ ] Docker images optimized (multi-stage builds)

### Monitoring & Observability
- [ ] Prometheus metrics exporters configured
- [ ] Grafana dashboards created
- [ ] ELK Stack configured for logs
- [ ] Jaeger distributed tracing setup
- [ ] Error tracking (Sentry/Rollbar) configured
- [ ] Uptime monitoring (Pingdom/StatusCake)
- [ ] APM (DataDog/New Relic) integrated
- [ ] Alert rules configured
- [ ] On-call rotation established
- [ ] Runbooks created

### Database
- [ ] Migrations tested on staging
- [ ] Backup strategy implemented
- [ ] Restore procedure tested
- [ ] Read replicas configured
- [ ] Connection pooling tuned
- [ ] Slow query log enabled
- [ ] Database monitoring configured
- [ ] Retention policies defined

### Application
- [ ] Health checks responding
- [ ] Liveness/readiness probes configured
- [ ] Graceful shutdown implemented
- [ ] Zero-downtime deployment tested
- [ ] Rollback procedure documented
- [ ] Environment variables documented
- [ ] Feature flags configured
- [ ] Dependency vulnerabilities scanned

---

## Environment Configuration

### Production Environment Variables

```bash
# Application
ENVIRONMENT=production
PROJECT_NAME="Employee Management System API"
VERSION=1.0.0
DEBUG=False
LOG_LEVEL=INFO

# Security (MUST CHANGE THESE!)
SECRET_KEY="<generate-with: python -c 'import secrets; print(secrets.token_urlsafe(64))'>"
JWT_SECRET="<generate-with: python -c 'import secrets; print(secrets.token_urlsafe(64))'>"
JWT_ALGORITHM=HS256
JWT_EXPIRATION=3600
REFRESH_TOKEN_EXPIRATION=604800

# Database
POSTGRES_HOST=<your-rds-endpoint>
POSTGRES_PORT=5432
POSTGRES_DB=employees
POSTGRES_USER=<secure-username>
POSTGRES_PASSWORD=<secure-password>
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_TIMEOUT=30
DB_ECHO=False

# Redis Cache
REDIS_HOST=<your-elasticache-endpoint>
REDIS_PORT=6379
REDIS_PASSWORD=<secure-password>
REDIS_DB=0
REDIS_TTL=600
CACHE_ENABLED=True

# CORS (Restrict to your domains)
CORS_ORIGINS=https://app.yourcompany.com,https://admin.yourcompany.com
CORS_ALLOW_CREDENTIALS=True
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,PATCH,OPTIONS
CORS_ALLOW_HEADERS=*

# Trusted Hosts
ALLOWED_HOSTS=app.yourcompany.com,api.yourcompany.com

# API Features
ENABLE_DOCS=False  # Disable in production or protect with auth
ENABLE_METRICS=True
ENABLE_TRACING=True
ENABLE_PROFILING=False

# Rate Limiting
RATE_LIMIT_ENABLED=True
RATE_LIMIT_MAX_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60

# Monitoring
JAEGER_AGENT_HOST=jaeger-agent
JAEGER_AGENT_PORT=6831

# External Services
ANALYTICS_SERVICE_URL=http://analytics-cuda:8001
GRAPHQL_GATEWAY_URL=http://graphql-gateway:4000
```

---

## Docker Production Build

### Optimized Multi-Stage Dockerfile

Create `services/api-python/Dockerfile.production`:

```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser . .

# Set environment variables
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Run with Gunicorn for production
CMD ["gunicorn", "app.main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--keep-alive", "5"]
```

### Build and Push

```bash
# Build for production
docker build -f Dockerfile.production -t employee-api:1.0.0 .

# Tag for registry
docker tag employee-api:1.0.0 your-registry.com/employee-api:1.0.0
docker tag employee-api:1.0.0 your-registry.com/employee-api:latest

# Push to registry
docker push your-registry.com/employee-api:1.0.0
docker push your-registry.com/employee-api:latest
```

---

## Kubernetes Deployment

### Create Namespace

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: employee-system
  labels:
    name: employee-system
    environment: production
```

### Secrets

```bash
# Create secrets from environment variables
kubectl create secret generic app-secrets \
  --from-literal=SECRET_KEY='your-secret-key' \
  --from-literal=JWT_SECRET='your-jwt-secret' \
  --from-literal=POSTGRES_PASSWORD='your-db-password' \
  --from-literal=REDIS_PASSWORD='your-redis-password' \
  -n employee-system
```

### ConfigMap

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: employee-system
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  POSTGRES_HOST: "postgres-service"
  POSTGRES_PORT: "5432"
  POSTGRES_DB: "employees"
  REDIS_HOST: "redis-service"
  REDIS_PORT: "6379"
  ENABLE_DOCS: "False"
  ENABLE_METRICS: "True"
```

### Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: employee-api
  namespace: employee-system
  labels:
    app: employee-api
    version: v1.0.0
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: employee-api
  template:
    metadata:
      labels:
        app: employee-api
        version: v1.0.0
    spec:
      containers:
      - name: api
        image: your-registry.com/employee-api:1.0.0
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
          name: http
          protocol: TCP
        env:
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: SECRET_KEY
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: JWT_SECRET
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: POSTGRES_PASSWORD
        envFrom:
        - configMapRef:
            name: app-config
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /api/v1/health/liveness
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /api/v1/health/readiness
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 15"]
      terminationGracePeriodSeconds: 30
```

### Service

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: employee-api-service
  namespace: employee-system
  labels:
    app: employee-api
spec:
  type: ClusterIP
  selector:
    app: employee-api
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
    name: http
  sessionAffinity: None
```

### Horizontal Pod Autoscaler

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: employee-api-hpa
  namespace: employee-system
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: employee-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Ingress (NGINX)

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: employee-api-ingress
  namespace: employee-system
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - api.yourcompany.com
    secretName: api-tls-secret
  rules:
  - host: api.yourcompany.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: employee-api-service
            port:
              number: 80
```

---

## Database Setup (AWS RDS Example)

### PostgreSQL Configuration

```sql
-- Create production database
CREATE DATABASE employees
    WITH ENCODING='UTF8'
    LC_COLLATE='en_US.UTF-8'
    LC_CTYPE='en_US.UTF-8'
    TEMPLATE=template0;

-- Create application user
CREATE USER app_user WITH PASSWORD 'secure-password';
GRANT ALL PRIVILEGES ON DATABASE employees TO app_user;

-- Run migrations
\i V1__create_schema.sql
\i V2__create_functions_and_triggers.sql
\i V3__create_views_and_materialized_views.sql
\i V4__create_indexes_and_optimization.sql
```

### RDS Recommended Settings

- Instance Class: db.r6g.xlarge (4 vCPU, 32 GB RAM)
- Storage: 500 GB SSD (gp3)
- Multi-AZ: Enabled
- Automated Backups: Enabled (7-day retention)
- Backup Window: 03:00-04:00 UTC
- Maintenance Window: Sun 04:00-05:00 UTC
- Enhanced Monitoring: Enabled
- Performance Insights: Enabled
- Encryption: Enabled (AWS KMS)

### Parameter Group

```
max_connections = 200
shared_buffers = 8GB
effective_cache_size = 24GB
maintenance_work_mem = 2GB
work_mem = 20MB
random_page_cost = 1.1
effective_io_concurrency = 200
```

---

## Deployment Steps

### 1. Pre-Deployment Testing

```bash
# Run all tests
cd services/api-python
pytest -v --cov=app --cov-report=html

# Security scan
bandit -r app/
safety check

# Lint code
flake8 app/
mypy app/

# Load testing
k6 run tests/performance/load_test.js
```

### 2. Build and Push Images

```bash
# Build production image
docker build -f Dockerfile.production -t employee-api:1.0.0 .

# Push to registry
docker push your-registry.com/employee-api:1.0.0
```

### 3. Apply Kubernetes Manifests

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Create secrets and configmaps
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml

# Deploy application
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml

# Verify deployment
kubectl get pods -n employee-system
kubectl get svc -n employee-system
kubectl get ingress -n employee-system
```

### 4. Run Database Migrations

```bash
# Port-forward to database
kubectl port-forward svc/postgres-service 5432:5432 -n employee-system

# Run migrations
psql -h localhost -U app_user -d employees -f database/migrations/V1__create_schema.sql
```

### 5. Verify Deployment

```bash
# Check health
curl https://api.yourcompany.com/health

# Check metrics
curl https://api.yourcompany.com/metrics

# Test API
curl https://api.yourcompany.com/api/v1/employees
```

---

## Monitoring Setup

### Prometheus Configuration

```yaml
# prometheus/prometheus.yml
scrape_configs:
  - job_name: 'employee-api'
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
            - employee-system
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: employee-api
      - source_labels: [__meta_kubernetes_pod_container_port_number]
        action: keep
        regex: "8000"
```

### Grafana Dashboard

Import dashboard ID: Create custom dashboard with:
- Request rate
- Response time (p50, p95, p99)
- Error rate
- CPU/Memory usage
- Database connection pool
- Cache hit rate

### Alert Rules

```yaml
# alerts.yaml
groups:
  - name: employee_api
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"

      - alert: HighResponseTime
        expr: http_request_duration_seconds{quantile="0.95"} > 0.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "API response time is high"

      - alert: PodCrashLooping
        expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
        labels:
          severity: critical
        annotations:
          summary: "Pod is crash looping"
```

---

## Rollback Procedure

```bash
# Rollback to previous version
kubectl rollout undo deployment/employee-api -n employee-system

# Rollback to specific revision
kubectl rollout undo deployment/employee-api --to-revision=2 -n employee-system

# Check rollout status
kubectl rollout status deployment/employee-api -n employee-system

# View rollout history
kubectl rollout history deployment/employee-api -n employee-system
```

---

## Disaster Recovery

### Backup Strategy

```bash
# Database backup (automated)
pg_dump -h postgres-host -U app_user employees | gzip > backup_$(date +%Y%m%d).sql.gz

# Upload to S3
aws s3 cp backup_$(date +%Y%m%d).sql.gz s3://your-backup-bucket/postgres/
```

### Restore Procedure

```bash
# Download from S3
aws s3 cp s3://your-backup-bucket/postgres/backup_20241115.sql.gz .

# Restore database
gunzip backup_20241115.sql.gz
psql -h postgres-host -U app_user -d employees < backup_20241115.sql
```

---

## Troubleshooting

### Common Issues

**1. Pods not starting**
```bash
kubectl describe pod <pod-name> -n employee-system
kubectl logs <pod-name> -n employee-system
```

**2. Database connection errors**
- Check database credentials in secrets
- Verify network connectivity
- Check connection pool settings

**3. High memory usage**
- Review connection pool size
- Check cache configuration
- Profile application with memory profiler

**4. Slow API responses**
- Enable query logging
- Check database indexes
- Review cache hit rate
- Analyze slow query log

---

## Maintenance

### Regular Tasks

**Daily:**
- Review error logs
- Check system metrics
- Monitor alert notifications

**Weekly:**
- Review performance metrics
- Check database slow queries
- Update dependencies (security patches)

**Monthly:**
- Review and rotate secrets
- Update SSL certificates (if needed)
- Capacity planning review
- Cost optimization review

---

## Security Hardening

### Additional Recommendations

1. **Enable WAF**: AWS WAF, Cloudflare, or similar
2. **DDoS Protection**: Cloudflare, AWS Shield
3. **Secrets Rotation**: Implement automated rotation
4. **Audit Logging**: Enable CloudTrail or equivalent
5. **Network Policies**: Restrict pod-to-pod communication
6. **Pod Security Policies**: Enforce security standards
7. **Image Scanning**: Scan for vulnerabilities (Trivy, Clair)
8. **Penetration Testing**: Regular security audits

---

**Last Updated**: 2025-11-15
**Version**: 1.0.0
**Status**: Production-Ready ✅
