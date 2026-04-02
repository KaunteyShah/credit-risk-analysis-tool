# Container Deployment Guide

## 🐳 Container-Friendly Configuration Overview

The Credit Risk Analysis application now uses a **hybrid configuration approach** that seamlessly supports:

- **Local Development**: Uses `.env` file with sensible defaults
- **Docker Containers**: Environment variables override defaults
- **Azure Container Instances**: Azure App Settings integration
- **Kubernetes**: ConfigMaps and Secrets support

## 📋 Environment Variables Reference

### **Database Configuration**
| Variable | Description | Default | Container Example |
|----------|-------------|---------|-------------------|
| `DATABASE_PATH` | SQLite database file path | `data/credit_risk.db` | `/app/data/credit_risk.db` |
| `SIC_TABLE_NAME` | SIC codes table name | `sic_codes` | `sic_codes` |
| `PREDICTION_TABLE_NAME` | Predictions table name | `sic_prediction_history` | `sic_prediction_history` |

### **Application Settings**
| Variable | Description | Default | Container Example |
|----------|-------------|---------|-------------------|
| `ENVIRONMENT` | Runtime environment | `development` | `production` |
| `SIC_MODEL_VERSION` | Model version | `1.0` | `2.0` |
| `CONFIDENCE_THRESHOLD` | Prediction threshold | `0.75` | `0.85` |
| `FLASK_SECRET_KEY` | Flask secret key | `dev-key` | `prod-secure-key` |
| `DEBUG` | Debug mode | `false` | `false` |

### **File Paths**
| Variable | Description | Default | Container Example |
|----------|-------------|---------|-------------------|
| `DATA_DIRECTORY` | Data folder path | `data` | `/app/data` |
| `PREDICTIONS_FILE` | CSV predictions file | `updated_sic_predictions.csv` | `predictions.csv` |

## 🚀 Deployment Examples

### **Local Development**
```bash
# Uses .env file defaults
python3 app_modules/flask_main.py
```

### **Docker Container**
```dockerfile
# Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

# Environment variables for container
ENV DATABASE_PATH=/app/data/credit_risk.db
ENV SIC_MODEL_VERSION=2.0
ENV ENVIRONMENT=production
ENV FLASK_SECRET_KEY=secure-production-key

EXPOSE 5000
CMD ["python", "app_modules/flask_main.py"]
```

```bash
# Build and run
docker build -t credit-risk-app .
docker run -p 5000:5000 \
  -e DATABASE_PATH=/app/data/prod.db \
  -e SIC_MODEL_VERSION=2.1 \
  -v ./data:/app/data \
  credit-risk-app
```

### **Azure Container Instances**
```bash
az container create \
  --resource-group credit-risk-rg \
  --name credit-risk-app \
  --image creditrisk.azurecr.io/app:latest \
  --cpu 2 --memory 4 \
  --environment-variables \
    DATABASE_PATH=/app/data/credit_risk.db \
    SIC_MODEL_VERSION=2.0 \
    ENVIRONMENT=production \
    FLASK_SECRET_KEY=azure-secure-key \
    CONFIDENCE_THRESHOLD=0.85
```

### **Azure App Service (Container)**
```json
{
  "name": "credit-risk-app",
  "properties": {
    "siteConfig": {
      "linuxFxVersion": "DOCKER|creditrisk.azurecr.io/app:latest",
      "appSettings": [
        {
          "name": "DATABASE_PATH",
          "value": "/home/site/wwwroot/data/credit_risk.db"
        },
        {
          "name": "SIC_MODEL_VERSION",
          "value": "2.0"
        },
        {
          "name": "ENVIRONMENT", 
          "value": "production"
        },
        {
          "name": "FLASK_SECRET_KEY",
          "value": "@Microsoft.KeyVault(VaultName=my-vault;SecretName=flask-secret)"
        }
      ]
    }
  }
}
```

### **Kubernetes Deployment**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: credit-risk-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: credit-risk-app
  template:
    metadata:
      labels:
        app: credit-risk-app
    spec:
      containers:
      - name: app
        image: creditrisk.azurecr.io/app:latest
        ports:
        - containerPort: 5000
        env:
        - name: DATABASE_PATH
          value: "/app/data/credit_risk.db"
        - name: SIC_MODEL_VERSION
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: model-version
        - name: FLASK_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: flask-secret-key
        - name: ENVIRONMENT
          value: "production"
        volumeMounts:
        - name: data-volume
          mountPath: /app/data
      volumes:
      - name: data-volume
        persistentVolumeClaim:
          claimName: data-pvc
```

## 🔧 Configuration Validation

The application includes built-in configuration validation:

```python
# Check configuration health
from app_modules.config import CreditRiskConfig
config = CreditRiskConfig()
status = config.validate_configuration()
print(status)
```

Example output:
```json
{
  "valid": true,
  "errors": [],
  "warnings": [],
  "environment": "production",
  "container_mode": true,
  "database_accessible": true
}
```

## 🔒 Security Best Practices

### **Production Secrets**
1. **Never use default secret keys** in production
2. **Use Azure Key Vault** for sensitive configuration
3. **Mount secrets as volumes** in Kubernetes
4. **Use managed identities** when possible

### **Database Security**
```bash
# Production database with restricted access
DATABASE_PATH=/app/data/production.db
# Or use Azure SQL with managed identity
DATABASE_URL=Server=tcp:myserver.database.windows.net,1433;Database=mydb;Authentication=Active Directory Managed Identity;
```

### **Environment Isolation**
```bash
# Development
ENVIRONMENT=development
DEBUG=true

# Staging  
ENVIRONMENT=staging
DEBUG=false
CONFIDENCE_THRESHOLD=0.80

# Production
ENVIRONMENT=production
DEBUG=false
CONFIDENCE_THRESHOLD=0.85
FLASK_SECRET_KEY=production-secure-key
```

## ✅ Migration Benefits

After implementing container-friendly configuration:

1. ✅ **Zero Code Changes** between environments
2. ✅ **Container Native** environment variable support  
3. ✅ **Azure Integration** ready for cloud deployment
4. ✅ **Security Enhanced** with secret management support
5. ✅ **Scalable Architecture** for multi-container deployments
6. ✅ **Development Friendly** with sensible defaults

The application is now **production-ready** for container deployment on Azure! 🚀