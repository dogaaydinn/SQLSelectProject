# Terraform Infrastructure - SQL Select Project

Enterprise-grade Infrastructure as Code for deploying the SQL Select Employee Management System on AWS with GPU-accelerated CUDA analytics.

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Modules](#modules)
- [Environments](#environments)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Deployment](#deployment)
- [GPU Support](#gpu-support)
- [Security](#security)
- [Cost Optimization](#cost-optimization)
- [Maintenance](#maintenance)

## 🏗️ Architecture Overview

This infrastructure deploys a complete, production-ready environment with:

- **VPC**: Multi-AZ networking with public, private, and database subnets
- **EKS**: Kubernetes cluster with general and GPU node groups
- **RDS PostgreSQL**: High-availability database with read replicas
- **ElastiCache Redis**: In-memory caching cluster
- **Security**: Encryption at rest/transit, VPC isolation, IAM roles
- **Monitoring**: CloudWatch logs, alarms, and metrics

```
┌─────────────────────────────────────────────────────────────┐
│                         VPC (10.x.0.0/16)                   │
│                                                               │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐   │
│  │ Public Subnet │  │ Public Subnet │  │ Public Subnet │   │
│  │   AZ-1        │  │   AZ-2        │  │   AZ-3        │   │
│  │  (NAT GW)     │  │  (NAT GW)     │  │  (NAT GW)     │   │
│  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘   │
│          │                  │                  │             │
│  ┌───────┴───────┐  ┌───────┴───────┐  ┌───────┴───────┐   │
│  │ Private Sub   │  │ Private Sub   │  │ Private Sub   │   │
│  │   AZ-1        │  │   AZ-2        │  │   AZ-3        │   │
│  │               │  │               │  │               │   │
│  │ ┌───────────┐ │  │ ┌───────────┐ │  │ ┌───────────┐ │   │
│  │ │  EKS      │ │  │ │  EKS      │ │  │ │  EKS      │ │   │
│  │ │  Nodes    │ │  │ │  Nodes    │ │  │ │  Nodes    │ │   │
│  │ │ (General) │ │  │ │ (General) │ │  │ │ (General) │ │   │
│  │ └───────────┘ │  │ └───────────┘ │  │ └───────────┘ │   │
│  │               │  │               │  │               │   │
│  │ ┌───────────┐ │  │ ┌───────────┐ │  │               │   │
│  │ │  EKS GPU  │ │  │ │  EKS GPU  │ │  │               │   │
│  │ │  Nodes    │ │  │ │  Nodes    │ │  │               │   │
│  │ │ (NVIDIA)  │ │  │ │ (NVIDIA)  │ │  │               │   │
│  │ └───────────┘ │  │ └───────────┘ │  │               │   │
│  │               │  │               │  │               │   │
│  │ ┌───────────┐ │  │ ┌───────────┐ │  │ ┌───────────┐ │   │
│  │ │ Redis     │ │  │ │ Redis     │ │  │ │ Redis     │ │   │
│  │ │ (Primary) │ │  │ │ (Replica) │ │  │ │ (Replica) │ │   │
│  │ └───────────┘ │  │ └───────────┘ │  │ └───────────┘ │   │
│  └───────────────┘  └───────────────┘  └───────────────┘   │
│                                                               │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐   │
│  │ Database Sub  │  │ Database Sub  │  │ Database Sub  │   │
│  │   AZ-1        │  │   AZ-2        │  │   AZ-3        │   │
│  │               │  │               │  │               │   │
│  │ ┌───────────┐ │  │ ┌───────────┐ │  │ ┌───────────┐ │   │
│  │ │ RDS       │ │  │ │ RDS Read  │ │  │ │ RDS Read  │ │   │
│  │ │ Primary   │ │  │ │ Replica 1 │ │  │ │ Replica 2 │ │   │
│  │ │ (Multi-AZ)│ │  │ │           │ │  │ │           │ │   │
│  │ └───────────┘ │  │ └───────────┘ │  │ └───────────┘ │   │
│  └───────────────┘  └───────────────┘  └───────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 📦 Modules

### VPC Module (`modules/vpc/`)

Creates a production-ready VPC with:
- 3 public subnets across 3 AZs (for load balancers)
- 3 private subnets across 3 AZs (for EKS, Redis)
- 3 database subnets across 3 AZs (for RDS)
- NAT Gateways (1 or 3 depending on environment)
- VPC Flow Logs for security monitoring
- Automatic tagging for EKS integration

### EKS Module (`modules/eks/`)

Deploys Kubernetes with GPU support:
- **General Node Group**: t3/t4 instances for API workloads
- **GPU Node Group**: g4dn instances (NVIDIA Tesla T4) for CUDA analytics
- Add-ons: VPC CNI, CoreDNS, kube-proxy, EBS CSI driver
- IAM Roles for Service Accounts (IRSA)
- Control plane logging to CloudWatch
- Automatic scaling groups

**GPU Instance Types**:
- `g4dn.xlarge`: 1 GPU, 4 vCPU, 16 GB RAM
- `g4dn.2xlarge`: 1 GPU, 8 vCPU, 32 GB RAM
- `g4dn.4xlarge`: 1 GPU, 16 vCPU, 64 GB RAM

### RDS Module (`modules/rds/`)

PostgreSQL 16 with enterprise features:
- Multi-AZ primary for automatic failover
- Read replicas for read scaling (production)
- Automatic backups with 7-30 day retention
- Performance Insights
- Enhanced Monitoring
- CloudWatch alarms (CPU, connections, storage)
- Encryption at rest with KMS
- Performance-tuned parameters

### ElastiCache Module (`modules/elasticache/`)

Redis 7.1 cluster:
- Primary + replicas for high availability
- Multi-AZ deployment
- Automatic failover
- Encryption at rest and in transit
- AUTH token authentication
- CloudWatch alarms (CPU, memory, evictions)
- Configurable eviction policies

## 🌍 Environments

### Development (`environments/dev/`)

Cost-optimized configuration:
- Single NAT Gateway
- Smaller instance types
- SPOT instances where possible
- No VPC Flow Logs
- Minimal read replicas
- Shorter backup retention

**Estimated Cost**: ~$350-450/month

### Production (`environments/prod/`)

Enterprise-grade configuration:
- NAT Gateway per AZ (high availability)
- Larger instance types
- ON_DEMAND instances for stability
- VPC Flow Logs enabled
- 2 read replicas for RDS
- 30-day backup retention
- CloudWatch alarms
- Deletion protection

**Estimated Cost**: ~$1,800-2,500/month

## ⚙️ Prerequisites

1. **AWS Account** with appropriate permissions
2. **Terraform** >= 1.5.0
   ```bash
   brew install terraform  # macOS
   ```

3. **AWS CLI** configured
   ```bash
   aws configure
   ```

4. **kubectl** for Kubernetes management
   ```bash
   brew install kubectl  # macOS
   ```

## 🚀 Quick Start

### 1. Choose Environment

```bash
cd infrastructure/terraform/environments/dev  # or prod
```

### 2. Create Configuration

```bash
cp terraform.tfvars.example terraform.tfvars
```

### 3. Edit Variables

**IMPORTANT**: Update these values in `terraform.tfvars`:
- `db_master_password` - Strong password (min 16 chars)
- `redis_auth_token` - Strong token (min 16 chars)
- `allowed_cidr_blocks` - Your IP ranges (production)

**For Production**:
- `kms_key_arn` - KMS key for encryption
- `alarm_sns_topic_arn` - SNS topic for alerts

### 4. Initialize Terraform

```bash
terraform init
```

### 5. Review Plan

```bash
terraform plan
```

### 6. Deploy

```bash
terraform apply
```

**Deployment time**: 20-30 minutes

## 📊 Deployment

### Step-by-Step Deployment

#### 1. Initialize Backend (Production)

For production, use remote state:

```bash
# Create S3 bucket for state
aws s3api create-bucket \
  --bucket sqlselect-terraform-state-prod \
  --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket sqlselect-terraform-state-prod \
  --versioning-configuration Status=Enabled

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

Uncomment backend configuration in `main.tf`.

#### 2. Create KMS Key (Production)

```bash
aws kms create-key --description "SQLSelect Production Encryption"
```

Update `kms_key_arn` in `terraform.tfvars`.

#### 3. Create SNS Topic (Production)

```bash
aws sns create-topic --name production-alerts
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT:production-alerts \
  --protocol email \
  --notification-endpoint your-email@company.com
```

#### 4. Deploy Infrastructure

```bash
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

#### 5. Configure kubectl

```bash
aws eks update-kubeconfig --region us-east-1 --name sqlselect-prod-eks
```

#### 6. Install NVIDIA Device Plugin

For GPU workloads:

```bash
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml
```

Verify GPU nodes:

```bash
kubectl get nodes -l nvidia.com/gpu=true
kubectl describe node <gpu-node-name> | grep nvidia.com/gpu
```

## 🎮 GPU Support

### GPU Node Configuration

The EKS GPU node group uses:
- **Instance Types**: g4dn.xlarge, g4dn.2xlarge, g4dn.4xlarge
- **GPU**: NVIDIA Tesla T4 (16 GB VRAM, 2,560 CUDA cores)
- **Taints**: `nvidia.com/gpu=true:NoSchedule` (GPU workloads only)
- **Labels**:
  - `nvidia.com/gpu=true`
  - `accelerator=nvidia-tesla-t4`
  - `workload=cuda-analytics`

### Deploying CUDA Workloads

Example pod spec:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: cuda-analytics
spec:
  nodeSelector:
    nvidia.com/gpu: "true"
  tolerations:
  - key: nvidia.com/gpu
    operator: Equal
    value: "true"
    effect: NoSchedule
  containers:
  - name: cuda-app
    image: your-cuda-app:latest
    resources:
      limits:
        nvidia.com/gpu: 1  # Request 1 GPU
```

### GPU Monitoring

```bash
# Check GPU availability
kubectl describe node <gpu-node> | grep -A5 "Allocatable"

# Monitor GPU usage
kubectl exec -it <pod-name> -- nvidia-smi
```

## 🔒 Security

### Encryption

- **EKS Secrets**: Encrypted with KMS
- **RDS**: Encrypted at rest with KMS
- **Redis**: Encrypted at rest and in transit
- **S3 State**: Server-side encryption enabled

### Network Security

- **Private Subnets**: All workloads run in private subnets
- **Security Groups**: Least privilege access
- **VPC Flow Logs**: Network traffic monitoring
- **NAT Gateways**: Secure outbound internet access

### Authentication

- **RDS**: Password authentication (consider IAM auth)
- **Redis**: AUTH token required
- **EKS**: IAM roles via IRSA

### Best Practices

1. **Secrets Management**: Use AWS Secrets Manager
   ```bash
   aws secretsmanager create-secret \
     --name prod/db/master-password \
     --secret-string "YOUR_STRONG_PASSWORD"
   ```

2. **Least Privilege IAM**: Minimal permissions for all roles

3. **MFA**: Enable MFA for AWS root and admin users

4. **Audit Logging**: Enable CloudTrail, Config, GuardDuty

## 💰 Cost Optimization

### Development Environment

- **SPOT Instances**: 70% cost savings on EKS nodes
- **Single NAT**: $32/month vs $96/month (3 NATs)
- **Smaller Instances**: t3/t4g over r6g
- **GPU Scaling**: Min 0 nodes (scale to 0 when idle)

### Production Environment

- **Reserved Instances**: 30-60% savings (1-3 year commitment)
- **Savings Plans**: Flexible compute savings
- **Read Replicas**: Scale reads, reduce primary load
- **RDS Storage Autoscaling**: Pay for what you use
- **Redis Memory Optimization**: allkeys-lru eviction policy

### Cost Monitoring

```bash
# View estimated monthly cost
terraform plan | grep "aws_instance\|aws_db_instance\|aws_elasticache"

# AWS Cost Explorer
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=TAG,Key=Environment
```

## 🔧 Maintenance

### Updating Infrastructure

```bash
# Make changes to .tf files
terraform plan
terraform apply
```

### Upgrading EKS

```bash
# Update cluster_version in variables.tf
# Apply changes (EKS will handle rolling upgrade)
terraform apply

# Update node groups
terraform taint module.eks.aws_eks_node_group.general
terraform apply
```

### Database Maintenance

Maintenance windows configured in variables:
- **RDS**: Sunday 04:00-05:00 UTC
- **Redis**: Sunday 05:00-07:00 UTC

### Backup and Recovery

**RDS Backups**:
```bash
# Manual snapshot
aws rds create-db-snapshot \
  --db-instance-identifier sqlselect-prod-db \
  --db-snapshot-identifier manual-snapshot-$(date +%Y%m%d)

# Restore from snapshot
terraform import module.rds.aws_db_instance.primary <snapshot-arn>
```

**Redis Backups**:
```bash
# Manual snapshot
aws elasticache create-snapshot \
  --replication-group-id sqlselect-prod-redis \
  --snapshot-name manual-snapshot-$(date +%Y%m%d)
```

### Disaster Recovery

**Recovery Time Objective (RTO)**: < 1 hour
**Recovery Point Objective (RPO)**: < 5 minutes

1. **Database**: Multi-AZ automatic failover (< 2 minutes)
2. **Redis**: Automatic failover to replica (< 30 seconds)
3. **EKS**: Multi-AZ node groups with auto-healing

## 📚 Additional Resources

- [AWS EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
- [NVIDIA GPU Operator](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/getting-started.html)
- [Terraform AWS Modules](https://github.com/terraform-aws-modules)
- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)

## 🆘 Troubleshooting

### EKS Nodes Not Joining

```bash
# Check node IAM role
aws eks describe-nodegroup --cluster-name <cluster> --nodegroup-name <nodegroup>

# Check security groups
kubectl get nodes
kubectl describe node <node-name>
```

### GPU Not Available

```bash
# Verify device plugin
kubectl get daemonset -n kube-system nvidia-device-plugin-daemonset

# Check node labels
kubectl get nodes --show-labels | grep nvidia
```

### Database Connection Issues

```bash
# Test connectivity from EKS
kubectl run -it --rm debug --image=postgres:16 --restart=Never -- \
  psql -h <rds-endpoint> -U postgres -d employees
```

### Redis Connection Issues

```bash
# Test connectivity
kubectl run -it --rm redis-cli --image=redis:7 --restart=Never -- \
  redis-cli -h <redis-endpoint> -p 6379 --tls -a <auth-token>
```

## 📄 License

This infrastructure code is part of the SQL Select Project.

---

**Deployed with**: Terraform v1.5+ | AWS Provider v5.0+
**Maintained by**: Platform Engineering Team
