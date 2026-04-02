# Storage Architecture Design

## Overview

This document describes the 3-tier storage architecture for the Credit Risk Analysis application. The design separates data by access patterns, size, and lifecycle requirements to optimize performance, cost, and scalability.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Azure Web App                                │
│                   (credit-risk-final)                          │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                    Application Layer                         │ │
│  │  • Flask Routes                                              │ │
│  │  • Agentic Workflows (LangGraph)                            │ │
│  │  • RAG Processing                                            │ │
│  │  • Document Vectorization                                    │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                            │                                        │
│                            ▼                                        │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                    Data Access Layer                         │ │
│  │  • Repository Pattern                                        │ │
│  │  • Service Layer                                             │ │
│  │  • Connection Pooling                                        │ │
│  └──────────────────────────────────────────────────────────────┘ │
└─────────────────────────┬───────────────┬────────────────┬─────────┘
                          │               │                │
                          ▼               ▼                ▼
┌─────────────────────────────────────────────────────────────────────┐
│             Azure Storage Account (creditriskstorageacc)            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────┐ │
│  │   TIER 1: HOT DATA   │  │  TIER 2: WARM DATA   │  │  TIER 3: │ │
│  │   File Share (SMB)   │  │   File Share (SMB)   │  │COLD DATA │ │
│  │  credit-risk-db      │  │credit-risk-vector-db │  │Blob (Hot)│ │
│  ├──────────────────────┤  ├──────────────────────┤  ├──────────┤ │
│  │                      │  │                      │  │          │ │
│  │  credit_risk.db      │  │  vector_database.db  │  │ PDFs/    │ │
│  │  Size: 1.9 MB        │  │  Size: 30 MB         │  │ 39 MB    │ │
│  │  Mount: /home/data   │  │  Mount:              │  │          │ │
│  │                      │  │    /home/vector_data │  │          │ │
│  │  Access: Very High   │  │  Access: Medium      │  │Access:   │ │
│  │  Read/Write: High    │  │  Read: High          │  │Low       │ │
│  │                      │  │  Write: Low          │  │          │ │
│  │  Quota: 5 GB         │  │  Quota: 5 GB         │  │Lifecycle │ │
│  │  Backup: Daily       │  │  Backup: Weekly      │  │Managed   │ │
│  └──────────────────────┘  └──────────────────────┘  └──────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

                          ┌──────────────────────┐
                          │  SQLite Browser      │
                          │  (Container Instance)│
                          │                      │
                          │  Mounts:             │
                          │  • credit-risk-db    │
                          │                      │
                          │  Access: Read-only   │
                          │  Port: 8080          │
                          └──────────────────────┘
```

## Storage Tier Details

### Tier 1: Main Database (Hot Data)

**Storage Type:** Azure File Share (SMB)  
**Share Name:** `credit-risk-db`  
**Mount Path:** `/home/data`  
**Quota:** 5 GB  

#### Purpose
Stores the primary relational database with company information, SIC predictions, activity logs, and user data.

#### Contents
- `credit_risk.db` (1.9 MB) - Main SQLite database

#### Access Patterns
- **Read Frequency:** Very High (every API request)
- **Write Frequency:** High (company updates, SIC predictions, logging)
- **Concurrency:** Multiple concurrent connections (connection pooling)
- **Latency Requirements:** < 50ms

#### Schema Overview
```sql
-- Companies table
CREATE TABLE companies (
    id INTEGER PRIMARY KEY,
    company_number TEXT UNIQUE,
    company_name TEXT,
    sic_code TEXT,
    confidence REAL,
    revenue REAL,
    ...
);

-- SIC predictions table
CREATE TABLE sic_predictions (
    id INTEGER PRIMARY KEY,
    company_id INTEGER,
    predicted_sic TEXT,
    confidence REAL,
    prediction_date TIMESTAMP,
    ...
);

-- Activity logs
CREATE TABLE activity_logs (
    id INTEGER PRIMARY KEY,
    action TEXT,
    timestamp TIMESTAMP,
    details TEXT,
    ...
);
```

#### Backup Strategy
- **Frequency:** Daily at 2:00 AM UTC
- **Retention:** 7 days
- **Method:** Automated backup to `/home/data/backups`
- **Recovery Time:** < 5 minutes

#### Performance Characteristics
- Connection pooling: 5 connections (max 10 with overflow)
- Transaction isolation: SERIALIZABLE
- WAL mode enabled for concurrent reads/writes
- Vacuum scheduled: Weekly

---

### Tier 2: Vector Database (Warm Data)

**Storage Type:** Azure File Share (SMB)  
**Share Name:** `credit-risk-vector-db`  
**Mount Path:** `/home/vector_data`  
**Quota:** 5 GB  

#### Purpose
Stores document embeddings for semantic search and RAG (Retrieval-Augmented Generation) workflows.

#### Contents
- `vector_database.db` (30 MB) - sqlite-vec database with embeddings

#### Access Patterns
- **Read Frequency:** Medium-High (during document search and RAG queries)
- **Write Frequency:** Low (only when new documents are processed)
- **Concurrency:** Low (mostly sequential writes, parallel reads)
- **Latency Requirements:** < 100ms

#### Schema Overview
```sql
-- Document embeddings table
CREATE TABLE embeddings (
    id INTEGER PRIMARY KEY,
    document_id TEXT,
    chunk_text TEXT,
    embedding BLOB,  -- 3072 dimensions (text-embedding-3-large)
    metadata TEXT,   -- JSON metadata
    created_at TIMESTAMP
);

-- Vector index (HNSW)
CREATE VIRTUAL TABLE embedding_index USING vec0(
    embedding float[3072]
);
```

#### Data Characteristics
- Embedding Model: `text-embedding-3-large`
- Dimensions: 3072
- Vector Count: ~500-1000 document chunks
- Index Type: HNSW (Hierarchical Navigable Small World)
- Similarity Metric: Cosine similarity

#### Backup Strategy
- **Frequency:** Weekly (Sunday at 2:00 AM UTC)
- **Retention:** 14 days
- **Method:** Automated backup to `/home/vector_data/backups`
- **Recovery Time:** < 30 minutes
- **Note:** Can be regenerated from source documents if needed

#### Performance Characteristics
- Top-K search: K=5 (configurable)
- Similarity threshold: 0.7
- Search latency: 50-100ms
- Index rebuild: Monthly (automatic)

---

### Tier 3: Document Storage (Cold Data)

**Storage Type:** Azure Blob Storage (Hot tier with lifecycle management)  
**Container Name:** `credit-risk-documents`  
**Access:** Private (no public access)  

#### Purpose
Stores raw PDF documents downloaded from Companies House for financial analysis and revenue extraction.

#### Structure
```
credit-risk-documents/
├── pdfs/                    # Raw downloaded PDFs
│   ├── 12345678.pdf        # Company number as filename
│   ├── 87654321.pdf
│   └── ...
├── processed/              # Extracted/processed content
│   ├── 12345678.json       # Extracted financial data
│   └── ...
└── archived/               # Archived old documents
    └── ...
```

#### Contents
- Raw PDF files: ~39 MB (100-500 files)
- Processed extracts: Variable
- Archived documents: Variable

#### Access Patterns
- **Read Frequency:** Low (only during revenue update workflows)
- **Write Frequency:** Medium (new document downloads)
- **Concurrency:** Low
- **Latency Requirements:** < 2 seconds (acceptable for bulk operations)

#### Lifecycle Management
Automatically manages document lifecycle to optimize costs:

1. **Hot Tier (0-90 days)**
   - Newly uploaded documents
   - Cost: ~£0.80/month for 50 GB
   - Access: Immediate

2. **Cool Tier (90-180 days)**
   - Documents older than 90 days
   - Cost: ~£0.40/month for 50 GB
   - Access: Slightly slower (acceptable)

3. **Archive Tier (180-365 days)**
   - Documents older than 180 days
   - Cost: ~£0.10/month for 50 GB
   - Access: Slower (rehydration required)

4. **Deletion (365+ days)**
   - Documents older than 1 year
   - Automatically deleted
   - Rationale: Can be re-downloaded from source if needed

#### Backup Strategy
- **Frequency:** None
- **Rationale:** Documents can be re-downloaded from Companies House API
- **Exception:** Critical financial reports may be manually backed up

#### Performance Characteristics
- Download speed: 10-50 MB/s
- Upload speed: 5-20 MB/s
- Batch operations: Parallel uploads (5 concurrent)
- Retry logic: 3 attempts with exponential backoff

---

## Design Rationale

### Why Separate Storage Tiers?

#### 1. Performance Optimization
- **Hot Data (Main DB):** Requires lowest latency, stored in file share with SMB protocol for fast random access
- **Warm Data (Vectors):** Medium latency acceptable, separate file share prevents main DB contention
- **Cold Data (PDFs):** Higher latency acceptable, blob storage optimized for large files

#### 2. Cost Optimization
- **File Shares:** Fixed cost regardless of usage, good for frequently accessed small files
- **Blob Storage:** Pay for what you use, with lifecycle management to move old data to cheaper tiers
- **Total Savings:** Estimated £19/month from removing unused resources and optimizing storage

#### 3. Scalability
- **Independent Scaling:** Each tier can scale independently
  - Main DB: Can increase quota if database grows
  - Vector DB: Can move to dedicated vector database service (e.g., Azure AI Search) if needed
  - Blob Storage: Unlimited scalability for document growth

#### 4. Data Lifecycle Management
- **Main DB:** Always hot, daily backups, strict consistency requirements
- **Vector DB:** Can be regenerated, weekly backups sufficient
- **Blob Storage:** Automatic tiering and deletion, source of truth is Companies House API

#### 5. Access Control
- **Main DB:** Read/write from web app, read-only from SQLite browser
- **Vector DB:** Read/write from web app only
- **Blob Storage:** Web app only, no public access

#### 6. Backup and Recovery
Different data types require different backup strategies:
- **Main DB:** Critical operational data, daily backups, 7-day retention
- **Vector DB:** Regenerable data, weekly backups, 14-day retention
- **Blob Storage:** No backups, re-downloadable from source

---

## Migration from Local Storage

### Current State (Local Development)
```
clean_modular_app/
├── data/
│   └── credit_risk.db           # 1.9 MB - Already migrated ✓
├── vector_database.db           # 30 MB - Needs migration
└── downloaded_documents/
    └── pdfs/                    # 39 MB - Needs migration
```

### Target State (Azure Production)
```
Azure Storage Account: creditriskstorageacc
│
├── File Share: credit-risk-db
│   └── credit_risk.db           # Already deployed ✓
│
├── File Share: credit-risk-vector-db
│   └── vector_database.db       # To be deployed
│
└── Blob Container: credit-risk-documents
    └── pdfs/                    # To be deployed
```

### Migration Steps

1. **Create New Storage Resources** (Script: `1_setup_storage.sh`)
   ```bash
   # Create vector DB file share
   az storage share create \
     --name credit-risk-vector-db \
     --quota 5 \
     --account-name creditriskstorageacc
   
   # Create blob container
   az storage container create \
     --name credit-risk-documents \
     --account-name creditriskstorageacc
   ```

2. **Upload Vector Database** (Script: `2_deploy_databases.sh`)
   ```bash
   # Upload vector database
   az storage file upload \
     --share-name credit-risk-vector-db \
     --source vector_database.db \
     --account-name creditriskstorageacc
   ```

3. **Upload PDF Documents** (Script: `2_deploy_databases.sh`)
   ```bash
   # Upload all PDFs
   az storage blob upload-batch \
     --destination credit-risk-documents \
     --source downloaded_documents/pdfs \
     --account-name creditriskstorageacc
   ```

4. **Update Application Configuration** (Script: `3_deploy_webapp.sh`)
   ```bash
   # Add environment variables
   az webapp config appsettings set \
     --name credit-risk-final \
     --settings \
       VECTOR_DB_PATH="/home/vector_data/vector_database.db" \
       PDF_STORAGE_PATH="/home/documents/pdfs"
   ```

5. **Verify Deployment**
   ```bash
   # Test vector search
   curl https://credit-risk-final.azurewebsites.net/api/test/vector-search
   
   # Test PDF access
   curl https://credit-risk-final.azurewebsites.net/api/test/pdf-access
   ```

---

## Monitoring and Maintenance

### Key Metrics to Monitor

#### Storage Capacity
```bash
# Check file share usage
az storage share stats \
  --name credit-risk-db \
  --account-name creditriskstorageacc

# Check blob container size
az storage blob list \
  --container-name credit-risk-documents \
  --account-name creditriskstorageacc \
  --query "[].properties.contentLength" \
  --output table
```

#### Performance Metrics
- **File Share Latency:** Monitor P50, P95, P99 latency
- **Blob Storage Throughput:** Monitor ingress/egress
- **Error Rate:** Monitor 500/503 errors

#### Cost Monitoring
```bash
# View storage costs
az costmanagement query \
  --type Usage \
  --dataset-filter "{\"and\":[{\"dimensions\":{\"name\":\"ResourceGroup\",\"operator\":\"In\",\"values\":[\"rg-credit-risk-clean\"]}}]}"
```

### Maintenance Tasks

#### Daily
- Automated backup of main database
- Check error logs for storage access issues

#### Weekly
- Automated backup of vector database
- Review storage usage and growth trends

#### Monthly
- Review blob storage lifecycle transitions
- Analyze cost optimization opportunities
- Rebuild vector indexes for optimal performance

#### Quarterly
- Review access patterns and adjust storage tiers
- Update lifecycle policies based on usage
- Disaster recovery testing

---

## Security Considerations

### Encryption
- **At Rest:** Microsoft-managed keys (MMK)
- **In Transit:** TLS 1.2+
- **Network:** HTTPS only, no public blob access

### Access Control
- **Web App:** Uses managed identity + connection strings
- **SQLite Browser:** Mounts file share read-only
- **Administrators:** Azure RBAC roles

### Compliance
- Data residency: UK West (ukwest)
- Retention: Automated lifecycle policies
- Audit: Azure Monitor logs all access

---

## Disaster Recovery

### Recovery Point Objective (RPO)
- **Main DB:** 24 hours (daily backups)
- **Vector DB:** 7 days (weekly backups, can regenerate)
- **Blob Storage:** N/A (can re-download from source)

### Recovery Time Objective (RTO)
- **Main DB:** < 1 hour
- **Vector DB:** < 4 hours (restore or regenerate)
- **Blob Storage:** < 24 hours (re-download from source)

### Recovery Procedures

#### Scenario 1: Main Database Corruption
```bash
# 1. Stop the web app
az webapp stop --name credit-risk-final --resource-group rg-credit-risk-clean

# 2. Download latest backup
az storage file download \
  --share-name credit-risk-db \
  --path backups/credit_risk_backup_YYYYMMDD.db \
  --dest ./credit_risk.db

# 3. Upload restored database
az storage file upload \
  --share-name credit-risk-db \
  --source ./credit_risk.db

# 4. Start the web app
az webapp start --name credit-risk-final --resource-group rg-credit-risk-clean
```

#### Scenario 2: Vector Database Loss
```bash
# Option A: Restore from backup
az storage file download \
  --share-name credit-risk-vector-db \
  --path backups/vector_database_backup_YYYYMMDD.db

# Option B: Regenerate from documents
curl -X POST https://credit-risk-final.azurewebsites.net/api/admin/regenerate-vectors
```

#### Scenario 3: Complete Storage Account Failure
```bash
# 1. Create new storage account
az storage account create --name creditriskstorageacc2

# 2. Restore from geo-redundant backup (if LRS → GRS)
# 3. Re-upload all data from local backups
# 4. Update web app connection strings
```

---

## Future Enhancements

### Short Term (1-3 months)
1. **Implement Azure Backup for File Shares**
   - Automated backup with Azure Backup service
   - Point-in-time recovery
   - Longer retention (30 days)

2. **Add Geo-Redundant Storage**
   - Upgrade from LRS to GRS
   - Disaster recovery across regions
   - Cost: +£1-2/month

3. **Implement Connection String Rotation**
   - Automatic key rotation every 90 days
   - Use Azure Key Vault for secrets
   - Managed identity for authentication

### Medium Term (3-6 months)
1. **Migrate to Azure AI Search for Vectors**
   - Better performance for large-scale vector search
   - Built-in semantic ranking
   - Hybrid search (keyword + vector)
   - Cost: ~£50-100/month

2. **Implement CDN for Static Content**
   - Azure CDN for PDF delivery
   - Reduce latency for document access
   - Cost: ~£5-10/month

3. **Add Application Insights Integration**
   - Detailed telemetry for storage operations
   - Custom metrics and dashboards
   - Alerting on performance degradation

### Long Term (6-12 months)
1. **Multi-Region Deployment**
   - Replicate storage to secondary region
   - Active-active or active-passive setup
   - Global load balancing

2. **Advanced Data Archival**
   - Move old data to Azure Archive Storage
   - Compliance and regulatory requirements
   - Long-term retention (5-10 years)

3. **Implement Data Lake**
   - Azure Data Lake Storage Gen2
   - Advanced analytics and ML
   - Historical trend analysis

---

## Cost Summary

### Current Monthly Costs
| Resource | Type | Size | Cost/Month |
|----------|------|------|------------|
| Main DB File Share | Standard_LRS | 1.9 MB / 5 GB | £0.10 |
| Vector DB File Share | Standard_LRS | 30 MB / 5 GB | £0.10 |
| Blob Storage (Hot) | Standard_LRS | 39 MB | £0.80 |
| **Total Storage** | | | **£1.00** |

### Projected Monthly Costs (1 year)
| Resource | Type | Projected Size | Cost/Month |
|----------|------|----------------|------------|
| Main DB File Share | Standard_LRS | 5 MB / 5 GB | £0.10 |
| Vector DB File Share | Standard_LRS | 100 MB / 5 GB | £0.10 |
| Blob Storage (Tiered) | Standard_LRS | 200 MB | £1.00 |
| **Total Storage** | | | **£1.20** |

### Savings from Optimization
- Removed unused ACRs: £15/month
- Removed orphaned container: £4/month
- **Total Savings: £19/month**

---

## Conclusion

The 3-tier storage architecture provides:
- ✅ **Performance:** Optimized access patterns for each data type
- ✅ **Cost Efficiency:** ~£1/month storage costs, £19/month in savings
- ✅ **Scalability:** Independent scaling for each tier
- ✅ **Reliability:** Automated backups and disaster recovery
- ✅ **Security:** Encryption, access control, and compliance
- ✅ **Maintainability:** Clear separation of concerns and lifecycle management

This design supports current needs while providing a foundation for future growth and enhancements.
