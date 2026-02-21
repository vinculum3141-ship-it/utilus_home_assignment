# Deployment Guide

## 🎯 Deployment Overview

This guide covers deploying the Energy Platform to various environments.

## 🏠 Local Development Deployment

### Prerequisites
- Python 3.11+
- pip
- Virtual environment tool

### Steps

```bash
# 1. Clone repository
git clone <repository-url>
cd energy_platform

# 2. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# 3. Install dependencies
make install-dev
# or: pip install -e ".[dev]"

# 4. Configure environment
cp .env.example .env
# Edit .env with your settings

# 5. Run tests
make test

# 6. Generate sample data and run pipeline
make run-batch

# 7. Start API server
make run-api
# or: uvicorn app.main:app --reload
```

## 🐳 Docker Deployment

### Single Container

```bash
# Build image
docker build -t energy-platform:latest .

# Run container
docker run -d \
  --name energy-platform \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e EXECUTION_MODE=local \
  -e LOG_LEVEL=INFO \
  energy-platform:latest

# Run batch job
docker exec energy-platform energy-platform run-batch --generate-sample

# View logs
docker logs -f energy-platform
```

### Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Run batch processing
docker-compose exec app energy-platform run-batch --generate-sample

# Access services
# API: http://localhost:8000
# PgAdmin: http://localhost:5050 (dev profile)

# Stop services
docker-compose down
```

## ☁️ Cloud Deployments

### AWS Deployment

#### Option 1: ECS Fargate

```bash
# 1. Build and push image to ECR
aws ecr create-repository --repository-name energy-platform
aws ecr get-login-password --region us-west-2 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-west-2.amazonaws.com

docker tag energy-platform:latest <account-id>.dkr.ecr.us-west-2.amazonaws.com/energy-platform:latest
docker push <account-id>.dkr.ecr.us-west-2.amazonaws.com/energy-platform:latest

# 2. Deploy using Terraform
cd terraform
terraform init
terraform plan
terraform apply

# 3. Configure ECS Task Definition
# - Set environment variables
# - Configure IAM roles
# - Set resource limits
```

#### Option 2: Lambda + Step Functions

```python
# For serverless batch processing
# Lambda function to trigger batch jobs
# Step Functions to orchestrate pipeline stages
# EventBridge for scheduling
```

#### Storage Configuration
```bash
# S3 for data lakes
aws s3 mb s3://energy-platform-bronze
aws s3 mb s3://energy-platform-silver
aws s3 mb s3://energy-platform-gold

# Update .env
STORAGE_PATH=s3://energy-platform
```

### Azure Deployment

#### Option 1: Azure Container Instances

```bash
# 1. Create Azure Container Registry
az acr create --resource-group energy-platform-rg \
  --name energyplatformacr --sku Basic

# 2. Build and push image
az acr build --registry energyplatformacr \
  --image energy-platform:latest .

# 3. Create Container Instance
az container create \
  --resource-group energy-platform-rg \
  --name energy-platform-api \
  --image energyplatformacr.azurecr.io/energy-platform:latest \
  --cpu 2 --memory 4 \
  --registry-login-server energyplatformacr.azurecr.io \
  --registry-username <username> \
  --registry-password <password> \
  --dns-name-label energy-platform-api \
  --ports 8000 \
  --environment-variables \
    EXECUTION_MODE=local \
    LOG_LEVEL=INFO
```

#### Storage Configuration
```bash
# Azure Data Lake Storage Gen2
STORAGE_PATH=abfss://bronze@energyplatform.dfs.core.windows.net/
```

### GCP Deployment

#### Option 1: Cloud Run

```bash
# 1. Build and push to Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/energy-platform

# 2. Deploy to Cloud Run
gcloud run deploy energy-platform \
  --image gcr.io/PROJECT_ID/energy-platform \
  --platform managed \
  --region us-west1 \
  --allow-unauthenticated \
  --set-env-vars EXECUTION_MODE=local,LOG_LEVEL=INFO
```

#### Storage Configuration
```bash
# Google Cloud Storage
STORAGE_PATH=gs://energy-platform-data
```

## 🔥 Databricks Deployment

### Setup

```bash
# 1. Install Databricks CLI
pip install databricks-cli

# 2. Configure authentication
databricks configure --token
# Enter workspace URL and token

# 3. Upload code to DBFS
databricks fs cp -r app dbfs:/FileStore/energy-platform/app/
databricks fs cp pyproject.toml dbfs:/FileStore/energy-platform/

# 4. Create job
cat > databricks-job.json << EOF
{
  "name": "Energy Platform Batch Processing",
  "new_cluster": {
    "spark_version": "13.3.x-scala2.12",
    "node_type_id": "i3.xlarge",
    "num_workers": 2
  },
  "libraries": [
    {
      "pypi": {
        "package": "fastapi>=0.109.0"
      }
    }
  ],
  "spark_python_task": {
    "python_file": "dbfs:/FileStore/energy-platform/app/cli.py",
    "parameters": ["run-batch"]
  }
}
EOF

databricks jobs create --json-file databricks-job.json

# 5. Run job
databricks jobs run-now --job-id <job-id>
```

### Configuration

```bash
# .env for Databricks
EXECUTION_MODE=databricks
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=<your-token>
STORAGE_PATH=/mnt/data
BRONZE_PATH=bronze
SILVER_PATH=silver
GOLD_PATH=gold
```

## 📅 Scheduling

### Cron (Linux)

```bash
# Edit crontab
crontab -e

# Run batch every hour
0 * * * * cd /path/to/energy_platform && ./venv/bin/energy-platform run-batch >> /var/log/energy-platform.log 2>&1

# Run at 2 AM daily
0 2 * * * cd /path/to/energy_platform && ./venv/bin/energy-platform run-batch --source daily
```

### AWS EventBridge

```hcl
resource "aws_cloudwatch_event_rule" "batch_schedule" {
  name                = "energy-platform-batch"
  description         = "Trigger batch processing"
  schedule_expression = "cron(0 2 * * ? *)"  # 2 AM daily
}

resource "aws_cloudwatch_event_target" "ecs_task" {
  rule      = aws_cloudwatch_event_rule.batch_schedule.name
  target_id = "energy-platform-batch"
  arn       = aws_ecs_cluster.main.arn
  role_arn  = aws_iam_role.ecs_events.arn

  ecs_target {
    task_definition_arn = aws_ecs_task_definition.batch.arn
    launch_type         = "FARGATE"
  }
}
```

### Azure Logic Apps

```json
{
  "definition": {
    "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
    "actions": {
      "Run_Container": {
        "type": "ApiConnection",
        "inputs": {
          "host": {
            "connection": {
              "name": "@parameters('$connections')['aci']['connectionId']"
            }
          },
          "method": "post",
          "path": "/containerGroups/@{encodeURIComponent('energy-platform-batch')}/start"
        }
      }
    },
    "triggers": {
      "Recurrence": {
        "type": "Recurrence",
        "recurrence": {
          "frequency": "Day",
          "interval": 1,
          "schedule": {
            "hours": ["2"]
          }
        }
      }
    }
  }
}
```

### Databricks Jobs

```python
# Via Databricks UI or API
# Schedule: Daily at 2 AM
# Cluster: Existing or new
# Task: Run app/cli.py with run-batch command
```

## 🔒 Security Configuration

### Environment Variables

```bash
# Use secret management services

# AWS Secrets Manager
aws secretsmanager create-secret \
  --name energy-platform/database-url \
  --secret-string "postgresql://user:pass@host:5432/db"

# Azure Key Vault
az keyvault secret set \
  --vault-name energy-platform-kv \
  --name database-url \
  --value "postgresql://user:pass@host:5432/db"

# GCP Secret Manager
echo -n "postgresql://user:pass@host:5432/db" | \
  gcloud secrets create database-url --data-file=-
```

### TLS/SSL Configuration

```python
# For API deployment
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 443 \
  --ssl-keyfile /path/to/key.pem \
  --ssl-certfile /path/to/cert.pem
```

## 📊 Monitoring Setup

### Prometheus + Grafana

```yaml
# docker-compose.monitoring.yml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

### CloudWatch (AWS)

```python
# Add CloudWatch logging
import boto3

logs_client = boto3.client('logs')
# Configure log group and stream
```

### Application Insights (Azure)

```python
# Add Application Insights
from applicationinsights import TelemetryClient
tc = TelemetryClient('<instrumentation-key>')
```

## 🔄 CI/CD Setup

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
      - run: pytest

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build and push Docker image
        run: |
          docker build -t energy-platform:${{ github.sha }} .
          docker push energy-platform:${{ github.sha }}
      - name: Deploy to ECS
        run: |
          # Update ECS service
```

### GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - test
  - build
  - deploy

test:
  stage: test
  script:
    - pip install -e ".[dev]"
    - pytest

build:
  stage: build
  script:
    - docker build -t energy-platform:$CI_COMMIT_SHA .
    - docker push energy-platform:$CI_COMMIT_SHA

deploy:
  stage: deploy
  script:
    - kubectl set image deployment/energy-platform app=energy-platform:$CI_COMMIT_SHA
  only:
    - main
```

## ✅ Post-Deployment Checklist

- [ ] Environment variables configured
- [ ] Database connections verified
- [ ] Storage access tested
- [ ] API health endpoint responding
- [ ] Batch job execution successful
- [ ] Logs flowing to monitoring system
- [ ] Metrics being collected
- [ ] Alerts configured
- [ ] Backup strategy in place
- [ ] Documentation updated
- [ ] Team trained on operations

## 🚨 Troubleshooting

### Common Issues

#### Container won't start
```bash
# Check logs
docker logs energy-platform

# Common fixes:
# - Verify environment variables
# - Check storage permissions
# - Ensure database is accessible
```

#### Batch job fails
```bash
# Check execution logs
energy-platform run-batch --generate-sample

# Verify:
# - Bronze data exists
# - Storage permissions
# - Transformation logic
```

#### API returns errors
```bash
# Test health endpoint
curl http://localhost:8000/health

# Check:
# - Repository connectivity
# - Gold layer data
# - Database connection
```

## 📞 Support

For deployment issues:
1. Check logs first
2. Verify configuration
3. Test connectivity
4. Review architecture docs
5. Consult team lead
