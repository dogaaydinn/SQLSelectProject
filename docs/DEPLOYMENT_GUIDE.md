# Production Deployment Guide

> **Employee Management System - FastAPI REST API**
>
> Complete guide for deploying to production environments

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Cloud Platform Deployment](#cloud-platform-deployment)
6. [Database Migration](#database-migration)
7. [Security Configuration](#security-configuration)
8. [Monitoring Setup](#monitoring-setup)
9. [Backup and Recovery](#backup-and-recovery)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Infrastructure

- **Compute**: 2+ CPU cores, 4GB+ RAM per API instance
- **Database**: PostgreSQL 16 server with 10GB+ storage
- **Cache**: Redis 7 server with 512MB+ memory
- **Load Balancer**: NGINX or cloud load balancer
- **Monitoring**: Prometheus + Grafana stack

### Required Software

```bash
# Docker (for containerized deployment)
docker --version  # Should be 24.0+
docker-compose --version  # Should be 2.20+

# Kubernetes (optional, for orchestrated deployment)
kubectl version --client  # Should be 1.28+
helm version  # Should be 3.12+

# Database client
psql --version  # Should be 16+
```

### Required Access

- Server SSH access with sudo privileges
- Database administrator credentials
- Cloud provider account (if deploying to cloud)
- Domain name with DNS management
- SSL/TLS certificate (for HTTPS)

---

## Infrastructure Setup

### 1. Provision Servers

#### Option A: Cloud Providers (AWS, GCP, Azure)

**AWS Example:**
```bash
# Create EC2 instance
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --count 1 \
  --instance-type t3.medium \
  --key-name your-key-pair \
  --security-group-ids sg-xxxxxxxx \
  --subnet-id subnet-xxxxxxxx \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=api-python-prod}]'

# Create RDS PostgreSQL database
aws rds create-db-instance \
  --db-instance-identifier employee-db-prod \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 16.1 \
  --master-username postgres \
  --master-user-password SECURE_PASSWORD \
  --allocated-storage 100 \
  --storage-type gp3 \
  --backup-retention-period 7 \
  --multi-az

# Create ElastiCache Redis cluster
aws elasticache create-cache-cluster \
  --cache-cluster-id employee-cache-prod \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --engine-version 7.0 \
  --num-cache-nodes 1
```

**GCP Example:**
```bash
# Create Compute Engine instance
gcloud compute instances create api-python-prod \
  --zone=us-central1-a \
  --machine-type=e2-medium \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=20GB

# Create Cloud SQL PostgreSQL instance
gcloud sql instances create employee-db-prod \
  --database-version=POSTGRES_16 \
  --tier=db-custom-2-7680 \
  --region=us-central1 \
  --backup \
  --backup-start-time=03:00

# Create Memorystore Redis instance
gcloud redis instances create employee-cache-prod \
  --size=1 \
  --region=us-central1 \
  --redis-version=redis_7_0
```

#### Option B: On-Premise/VPS

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install PostgreSQL client
sudo apt install -y postgresql-client-16

# Install monitoring tools
sudo apt install -y prometheus grafana
```

### 2. Network Configuration

```bash
# Configure firewall rules
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# For cloud providers, configure security groups
# AWS Example:
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxxxxx \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0
```

### 3. DNS Configuration

```bash
# Add A records for your domain
api.example.com     A     1.2.3.4
grafana.example.com A     1.2.3.4
kibana.example.com  A     1.2.3.4
```

### 4. SSL/TLS Certificate

#### Using Let's Encrypt (Free)

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d api.example.com

# Auto-renewal (runs twice daily)
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

#### Using Custom Certificate

```bash
# Place your certificates
sudo mkdir -p /etc/ssl/certs
sudo cp your-cert.crt /etc/ssl/certs/api.example.com.crt
sudo cp your-key.key /etc/ssl/private/api.example.com.key
sudo chmod 600 /etc/ssl/private/api.example.com.key
```

---

## Docker Deployment

### 1. Prepare Environment

```bash
# Clone repository
git clone https://github.com/dogaaydinn/SQLSelectProject.git
cd SQLSelectProject

# Create production environment file
cat > .env.production << EOF
# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
API_V1_STR=/api/v1

# Database
POSTGRES_USER=produser
POSTGRES_PASSWORD=$(openssl rand -base64 32)
POSTGRES_DB=employees
DATABASE_URL=postgresql://produser:PASSWORD@postgres:5432/employees
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_PASSWORD=$(openssl rand -base64 32)
REDIS_URL=redis://:PASSWORD@redis:6379/0
CACHE_TTL=300

# Security
JWT_SECRET=$(openssl rand -base64 64)
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=https://api.example.com,https://yourdomain.com

# Monitoring
PROMETHEUS_ENABLED=true
JAEGER_ENABLED=true
EOF

# Secure the environment file
chmod 600 .env.production
```

### 2. Build Images

```bash
# Build production images
docker-compose -f docker-compose.yml build --no-cache

# Tag images
docker tag sqlselect-api-python:latest sqlselect-api-python:v1.0.0
docker tag sqlselect-nginx:latest sqlselect-nginx:v1.0.0
```

### 3. Deploy Services

```bash
# Start production stack
docker-compose --env-file .env.production up -d

# Verify all services are running
docker-compose ps

# Check logs
docker-compose logs -f api-python

# Check health
curl https://api.example.com/api/v1/health/detailed
```

### 4. Initialize Database

```bash
# Run migrations
docker-compose exec postgres psql -U produser -d employees -f /docker-entrypoint-initdb.d/V1__create_schema.sql
docker-compose exec postgres psql -U produser -d employees -f /docker-entrypoint-initdb.d/V2__create_functions_and_triggers.sql
docker-compose exec postgres psql -U produser -d employees -f /docker-entrypoint-initdb.d/V3__create_views_and_materialized_views.sql
docker-compose exec postgres psql -U produser -d employees -f /docker-entrypoint-initdb.d/V4__create_indexes_and_optimization.sql

# Verify migrations
docker-compose exec postgres psql -U produser -d employees -c "\dt"
```

### 5. Scale Services

```bash
# Scale API service to 3 instances
docker-compose up -d --scale api-python=3

# Verify load balancing
for i in {1..10}; do
  curl https://api.example.com/api/v1/health
  sleep 1
done
```

---

## Kubernetes Deployment

### 1. Create Namespace

```bash
kubectl create namespace employees-prod
kubectl config set-context --current --namespace=employees-prod
```

### 2. Create Secrets

```bash
# Database credentials
kubectl create secret generic postgres-credentials \
  --from-literal=username=produser \
  --from-literal=password=$(openssl rand -base64 32) \
  --from-literal=database=employees

# Redis credentials
kubectl create secret generic redis-credentials \
  --from-literal=password=$(openssl rand -base64 32)

# JWT secret
kubectl create secret generic jwt-secret \
  --from-literal=secret=$(openssl rand -base64 64)

# Verify secrets
kubectl get secrets
```

### 3. Create ConfigMap

```yaml
# config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: api-config
  namespace: employees-prod
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  API_V1_STR: "/api/v1"
  DATABASE_POOL_SIZE: "20"
  CACHE_TTL: "300"
  CORS_ORIGINS: "https://api.example.com"
  PROMETHEUS_ENABLED: "true"
```

```bash
kubectl apply -f config.yaml
```

### 4. Deploy Database

```yaml
# postgres-deployment.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: employees-prod
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:16-alpine
        env:
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: postgres-credentials
              key: username
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-credentials
              key: password
        - name: POSTGRES_DB
          valueFrom:
            secretKeyRef:
              name: postgres-credentials
              key: database
        ports:
        - containerPort: 5432
          name: postgres
        volumeMounts:
        - name: postgres-data
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
  volumeClaimTemplates:
  - metadata:
      name: postgres-data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 100Gi
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: employees-prod
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
  clusterIP: None
```

### 5. Deploy API

```yaml
# api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-python
  namespace: employees-prod
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: api-python
  template:
    metadata:
      labels:
        app: api-python
        version: v1.0.0
    spec:
      containers:
      - name: api-python
        image: ghcr.io/dogaaydinn/sqlselectproject/api-python:v1.0.0
        imagePullPolicy: Always
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: postgres-credentials
              key: url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-credentials
              key: url
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: jwt-secret
              key: secret
        envFrom:
        - configMapRef:
            name: api-config
        ports:
        - containerPort: 8000
          name: http
        - containerPort: 8001
          name: metrics
        livenessProbe:
          httpGet:
            path: /api/v1/health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /api/v1/health/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1"
---
apiVersion: v1
kind: Service
metadata:
  name: api-python
  namespace: employees-prod
spec:
  selector:
    app: api-python
  ports:
  - name: http
    port: 80
    targetPort: 8000
  - name: metrics
    port: 8001
    targetPort: 8001
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-python-hpa
  namespace: employees-prod
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-python
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

### 6. Deploy Ingress

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  namespace: employees-prod
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - api.example.com
    secretName: api-tls
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-python
            port:
              number: 80
```

### 7. Deploy All Resources

```bash
# Apply all configurations
kubectl apply -f postgres-deployment.yaml
kubectl apply -f api-deployment.yaml
kubectl apply -f ingress.yaml

# Verify deployments
kubectl get all -n employees-prod

# Check pod logs
kubectl logs -f deployment/api-python -n employees-prod

# Check HPA status
kubectl get hpa -n employees-prod

# Test endpoint
curl https://api.example.com/api/v1/health/detailed
```

---

## Database Migration

### Production Migration Strategy

```bash
# 1. Backup current database
./database/scripts/backup.sh

# 2. Test migrations on staging
psql -h staging-db -U postgres -d employees < database/migrations/V1__create_schema.sql

# 3. Schedule maintenance window
echo "Scheduled maintenance: $(date)"

# 4. Put application in maintenance mode
kubectl scale deployment api-python --replicas=0 -n employees-prod

# 5. Run migrations
psql -h prod-db -U postgres -d employees -f database/migrations/V1__create_schema.sql
psql -h prod-db -U postgres -d employees -f database/migrations/V2__create_functions_and_triggers.sql
psql -h prod-db -U postgres -d employees -f database/migrations/V3__create_views_and_materialized_views.sql
psql -h prod-db -U postgres -d employees -f database/migrations/V4__create_indexes_and_optimization.sql

# 6. Verify migration
psql -h prod-db -U postgres -d employees -c "SELECT COUNT(*) FROM employees;"

# 7. Restore application
kubectl scale deployment api-python --replicas=3 -n employees-prod

# 8. Verify application health
kubectl get pods -n employees-prod
curl https://api.example.com/api/v1/health/detailed
```

---

## Security Configuration

### 1. Environment Variables

Never commit secrets to version control. Use:

- **Kubernetes Secrets** for K8s deployments
- **AWS Secrets Manager** for AWS
- **GCP Secret Manager** for GCP
- **Azure Key Vault** for Azure
- **HashiCorp Vault** for on-premise

### 2. Database Security

```sql
-- Create read-only user for replicas
CREATE USER readonly_user WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE employees TO readonly_user;
GRANT USAGE ON SCHEMA public TO readonly_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;

-- Restrict network access
-- Edit pg_hba.conf:
# IPv4 local connections:
host    all             all             10.0.0.0/8              scram-sha-256
host    all             all             172.16.0.0/12           scram-sha-256
```

### 3. API Security Headers

Already configured in NGINX, verify:

```bash
curl -I https://api.example.com/api/v1/health
# Should include:
# X-Frame-Options: SAMEORIGIN
# X-Content-Type-Options: nosniff
# X-XSS-Protection: 1; mode=block
```

---

## Monitoring Setup

### 1. Prometheus

```bash
# Verify Prometheus is scraping targets
curl http://prometheus:9090/api/v1/targets

# Check metrics endpoint
curl http://api-python:8000/metrics
```

### 2. Grafana

```bash
# Access Grafana
open https://grafana.example.com

# Import dashboards
# Navigate to: Dashboards → Import
# Use dashboard ID: infrastructure/monitoring/grafana/dashboards/api-performance.json
```

### 3. Alerts

```bash
# Verify alerts are configured
curl http://prometheus:9090/api/v1/rules

# Test alert
# Simulate high error rate and verify alert fires
```

---

## Backup and Recovery

### Automated Backups

```bash
# Setup cron job for daily backups
crontab -e

# Add:
0 3 * * * /path/to/database/scripts/backup.sh
```

### Disaster Recovery

```bash
# 1. Provision new infrastructure
# 2. Restore database
./database/scripts/restore.sh /backups/employees_backup_2024-01-15.sql.gz

# 3. Deploy application
kubectl apply -f k8s/

# 4. Verify
curl https://api.example.com/api/v1/health/detailed
```

---

## Troubleshooting

### Common Issues

**Issue: API returns 502 Bad Gateway**
```bash
# Check API logs
kubectl logs -f deployment/api-python

# Check if pods are running
kubectl get pods

# Restart deployment
kubectl rollout restart deployment/api-python
```

**Issue: Database connection errors**
```bash
# Test database connectivity
kubectl exec -it postgres-0 -- psql -U postgres -d employees

# Check connection pool
kubectl logs api-python | grep "pool"
```

**Issue: High memory usage**
```bash
# Check memory usage
kubectl top pods

# Increase resources
kubectl set resources deployment api-python --limits=memory=2Gi
```

---

## Production Checklist

- [ ] SSL/TLS certificate installed and auto-renewal configured
- [ ] Environment variables secured (no hardcoded secrets)
- [ ] Database migrations tested on staging
- [ ] Backup automation configured and tested
- [ ] Monitoring and alerting configured
- [ ] Log aggregation setup (ELK stack)
- [ ] Rate limiting configured
- [ ] CORS configured for allowed origins only
- [ ] Health checks responding correctly
- [ ] Auto-scaling configured
- [ ] Disaster recovery plan documented and tested
- [ ] Security scan completed (no critical vulnerabilities)
- [ ] Load testing completed and passed
- [ ] Documentation updated
- [ ] Team trained on deployment procedures

---

**Deployment Complete!** 🚀

For issues or questions, contact the ops team or file a GitHub issue.

[⬆ Back to top](#production-deployment-guide)
