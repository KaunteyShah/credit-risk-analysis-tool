# Cost Analysis & Optimization

## Executive Summary

This document provides a comprehensive analysis of the Azure infrastructure costs for the Credit Risk Analysis application, along with optimization recommendations.

### Current Monthly Cost: **£66.48**
### Optimized Monthly Cost: **£47.48**
### **Potential Savings: £19.00/month (29% reduction)**

---

## Current Cost Breakdown

### Compute Resources

#### 1. Web App Service Plan
**Resource:** `credit-risk-final-plan`  
**SKU:** B3 (Basic Tier)  
**Specifications:**
- 2 vCPUs
- 7 GB RAM
- 10 GB Storage
- Always On enabled

**Monthly Cost:** £45.60

**Usage Pattern:**
- Running 24/7 (730 hours/month)
- Average CPU: 30-40%
- Average Memory: 50-60%
- Traffic: ~10,000 requests/month

---

#### 2. Container Instances (SQLite Browser)
**Resource:** `sqlite-browser`  
**SKU:** 1 vCPU, 1.5 GB RAM  
**Usage:** On-demand (not always running)

**Monthly Cost:** £0.00 - £4.00 (depends on usage)
- Cost per hour: £0.0133
- Typical usage: 0-300 hours/month
- Average cost: £2.00/month

**Usage Pattern:**
- Started only when database browsing is needed
- Typically runs 2-3 hours/week
- Auto-stops after 4 hours of inactivity

---

### Storage Resources

#### 3. Storage Account
**Resource:** `creditriskstorageacc`  
**SKU:** Standard_LRS (Locally Redundant Storage)  
**Location:** UK West

**Monthly Cost:** £1.00

**Breakdown:**
- **File Shares (2x):** £0.20/month
  - `credit-risk-db`: 5 GB quota, 1.9 MB used
  - `credit-risk-vector-db`: 5 GB quota, 30 MB used
  
- **Blob Storage:** £0.80/month
  - `credit-risk-documents`: Hot tier, 39 MB used
  
- **Transactions:** £0.00
  - ~100,000 transactions/month (within free tier)
  
- **Data Transfer:** £0.00
  - Egress: <1 GB/month (within free tier)

**Storage Utilization:**
- Total provisioned: 10 GB (file shares)
- Total used: ~70 MB (0.7% utilization)
- Efficiency: Very low utilization, but minimal cost

---

### AI/ML Resources

#### 4. Azure OpenAI Service
**Resource:** `data-risk-modernisation-OAI`  
**Models:**
- GPT-4o (text generation)
- text-embedding-3-large (embeddings)

**Monthly Cost:** £15.00 - £18.00 (variable)

**Usage Breakdown:**

**Text Generation (GPT-4o):**
- Input tokens: ~500K tokens/month
- Output tokens: ~200K tokens/month
- Cost per 1M input tokens: £4.00
- Cost per 1M output tokens: £12.00
- **Subtotal: £4.40/month**

**Embeddings (text-embedding-3-large):**
- Tokens processed: ~2M tokens/month
- Cost per 1M tokens: £0.10
- **Subtotal: £0.20/month**

**Total AI Cost: £4.60/month** (typical)  
**Peak Cost: £18.00/month** (high usage scenarios)

**Usage Pattern:**
- SIC predictions: ~100 requests/month
- Revenue extraction: ~50 requests/month
- Document embeddings: ~200 documents/month
- RAG queries: ~500 queries/month

---

### Monitoring & Logging

#### 5. Log Analytics Workspace
**Resource:** `workspace-rgcreditriskcleanSOiN`  
**Data Ingestion:** ~1 GB/month

**Monthly Cost:** £0.00
- First 5 GB/month free
- Current usage well within free tier

---

#### 6. Application Insights (Optional)
**Status:** Not currently deployed  
**Potential Cost:** £0.00 - £2.00/month
- First 5 GB/month free
- Estimated usage: <1 GB/month

---

### Unused Resources (To Be Deleted)

#### 7. Container Registries (3x) ❌
**Resources:**
- `creditriskcleanapp20240524233833`
- `creditriskfullapp20250425233456`
- `creditriskappregistry`

**Current Cost:** £15.00/month (£5.00 each)

**Status:** Unused, candidates for deletion  
**Potential Savings:** £15.00/month

**Rationale for Deletion:**
- Application deployed as Web App (not containerized)
- No container images stored
- Created during initial testing, no longer needed

---

#### 8. Orphaned Container Instance ❌
**Resource:** `credit-risk-full-app` (Container Instance)  
**Status:** Stopped, orphaned

**Current Cost:** £4.00/month (storage charges)

**Potential Savings:** £4.00/month

**Rationale for Deletion:**
- Application migrated to Web App
- Container instance no longer used
- Still incurring storage charges

---

## Total Cost Summary

### Current Monthly Costs

| Category | Resource | Cost/Month |
|----------|----------|------------|
| **Compute** | Web App (B3) | £45.60 |
| | SQLite Browser (ACI) | £2.00 |
| **Storage** | Storage Account | £1.00 |
| **AI/ML** | Azure OpenAI | £4.60 - £18.00 |
| **Monitoring** | Log Analytics | £0.00 |
| **Unused** | Container Registries (3x) | £15.00 ❌ |
| | Orphaned Container | £4.00 ❌ |
| **Total** | | **£66.48 - £80.00** |

### Optimized Monthly Costs (After Cleanup)

| Category | Resource | Cost/Month |
|----------|----------|------------|
| **Compute** | Web App (B3) | £45.60 |
| | SQLite Browser (ACI) | £2.00 |
| **Storage** | Storage Account | £1.00 |
| **AI/ML** | Azure OpenAI | £4.60 - £18.00 |
| **Monitoring** | Log Analytics | £0.00 |
| **Total** | | **£47.48 - £61.00** |

**Savings: £19.00/month (29% reduction)**

---

## Cost Optimization Recommendations

### Immediate Actions (Savings: £19.00/month)

#### 1. Delete Unused Container Registries
```bash
# Run cleanup script
./azure_deployment/scripts/cleanup_unused_resources.sh
```

**Impact:**
- Savings: £15.00/month
- Risk: None (resources are unused)
- Time: 5 minutes

---

#### 2. Delete Orphaned Container Instance
```bash
az container delete \
  --name credit-risk-full-app \
  --resource-group rg-credit-risk-clean \
  --yes
```

**Impact:**
- Savings: £4.00/month
- Risk: None (application migrated)
- Time: 2 minutes

---

### Short-Term Optimizations (1-3 months)

#### 3. Right-Size App Service Plan
**Current:** B3 (2 vCPU, 7 GB RAM) - £45.60/month  
**Recommendation:** Monitor usage for 1 month

**Options:**
- **Option A:** Downgrade to B2 (1 vCPU, 3.5 GB RAM) - £22.80/month
  - **Savings:** £22.80/month
  - **Risk:** May impact performance during peak loads
  - **When:** If CPU consistently < 50% and Memory < 60%

- **Option B:** Stay on B3 but optimize application
  - Enable caching to reduce CPU usage
  - Optimize database queries
  - Implement request throttling

**Action:**
```bash
# Monitor metrics for 30 days
az monitor metrics list \
  --resource credit-risk-final \
  --metric-names "CpuPercentage,MemoryPercentage" \
  --start-time $(date -u -d '30 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ)

# If average CPU < 50% and Memory < 60%, consider downgrade
```

---

#### 4. Optimize Azure OpenAI Usage
**Current:** £4.60 - £18.00/month (variable)

**Optimization Strategies:**

**A. Implement Response Caching**
```python
# Cache common queries for 24 hours
@cache.memoize(timeout=86400)
def get_sic_prediction(company_name):
    return openai_service.predict_sic(company_name)
```
**Potential Savings:** 30-50% of AI costs (£1.38 - £9.00/month)

**B. Use Smaller Models for Simple Tasks**
```python
# Use GPT-3.5 for simple classifications
# Use GPT-4o only for complex reasoning
if task.complexity == "simple":
    model = "gpt-35-turbo"  # 10x cheaper
else:
    model = "gpt-4o"
```
**Potential Savings:** 20-40% of AI costs (£0.92 - £7.20/month)

**C. Batch Embedding Requests**
```python
# Batch 100 documents per request instead of 1-by-1
embeddings = openai.embeddings.create(
    input=batch_of_100_texts,
    model="text-embedding-3-large"
)
```
**Potential Savings:** 10-20% of embedding costs (£0.02 - £0.04/month)

**Total AI Savings Potential:** £2.32 - £16.24/month

---

#### 5. Implement Storage Lifecycle Policies
**Current:** All blob storage in Hot tier (£0.80/month)

**Recommendation:** Auto-tier old documents to Cool/Archive

```bash
az storage account management-policy create \
  --account-name creditriskstorageacc \
  --policy @lifecycle_policy.json
```

**Lifecycle Policy:**
```json
{
  "rules": [{
    "name": "TierOldDocuments",
    "type": "Lifecycle",
    "definition": {
      "actions": {
        "baseBlob": {
          "tierToCool": {"daysAfterModificationGreaterThan": 90},
          "tierToArchive": {"daysAfterModificationGreaterThan": 180},
          "delete": {"daysAfterModificationGreaterThan": 365}
        }
      }
    }
  }]
}
```

**Savings:**
- Hot tier: £0.016/GB
- Cool tier: £0.008/GB (50% cheaper)
- Archive tier: £0.002/GB (87.5% cheaper)

**Estimated Savings:** £0.20 - £0.40/month (depends on document growth)

---

### Medium-Term Optimizations (3-6 months)

#### 6. Enable Reserved Capacity
If usage is consistent, commit to 1-year reserved capacity:

**App Service Reserved Instance:**
- Current: B3 @ £45.60/month (Pay-as-you-go)
- Reserved (1 year): £36.48/month
- **Savings: £9.12/month (20% discount)**

**Azure OpenAI Reserved Capacity:**
- Available for predictable workloads
- Up to 40% discount
- **Potential Savings: £1.84 - £7.20/month**

**Total Reserved Capacity Savings: £10.96 - £16.32/month**

---

#### 7. Implement Azure Front Door + CDN
For global users or high traffic:

**Benefits:**
- Cache static content at edge locations
- Reduce backend compute requirements
- Potential to downgrade App Service tier

**Cost:**
- Azure Front Door: ~£15/month
- Break-even: Only if can downgrade to B2 (saves £22.80)
- **Net Savings: £7.80/month**

**Not Recommended Yet:** Wait until traffic justifies CDN costs

---

### Long-Term Optimizations (6-12 months)

#### 8. Migrate to Azure Container Apps
**Current:** App Service B3 (£45.60/month)  
**Alternative:** Azure Container Apps (consumption-based)

**Container Apps Pricing:**
- vCPU: £0.000014/second
- Memory: £0.0000014/GB-second
- For typical usage: ~£20-30/month

**Potential Savings:** £15-25/month

**Considerations:**
- Requires containerization
- More complex deployment
- Better for variable workloads

---

#### 9. Move Vector Search to Azure AI Search
**Current:** SQLite-vec in file share (included in storage)  
**Alternative:** Azure AI Search (£60-100/month)

**Not Recommended:** Current solution is cost-effective for current scale

**When to Consider:**
- Vector database exceeds 1 GB
- Search queries exceed 10,000/month
- Need advanced features (hybrid search, semantic ranking)

---

## Cost Monitoring & Alerts

### Set Up Budget Alerts

```bash
# Create monthly budget alert
az consumption budget create \
  --amount 75 \
  --budget-name credit-risk-monthly-budget \
  --category Cost \
  --time-grain Monthly \
  --time-period start-date=$(date +%Y-%m-01) \
  --resource-group rg-credit-risk-clean
```

**Alert Thresholds:**
- 50% of budget: Warning email (£37.50)
- 75% of budget: Warning email + Slack notification (£56.25)
- 90% of budget: Critical alert + escalation (£67.50)
- 100% of budget: Emergency alert (£75.00)

---

### Monitor Cost Trends

```bash
# Weekly cost analysis
az costmanagement query \
  --type Usage \
  --dataset-filter "{\"and\":[{\"dimensions\":{\"name\":\"ResourceGroup\",\"operator\":\"In\",\"values\":[\"rg-credit-risk-clean\"]}}]}" \
  --timeframe WeekToDate

# Monthly cost forecast
az costmanagement forecast \
  --type Usage \
  --timeframe MonthToDate \
  --dataset-filter "{\"and\":[{\"dimensions\":{\"name\":\"ResourceGroup\",\"operator\":\"In\",\"values\":[\"rg-credit-risk-clean\"]}}]}"
```

---

## Cost Projection (12 Months)

### Scenario A: Current State (No Optimization)
| Month | Cost | Cumulative |
|-------|------|------------|
| Month 1-12 | £66.48 | £797.76 |

---

### Scenario B: Immediate Cleanup Only
| Month | Cost | Cumulative | Savings |
|-------|------|------------|---------|
| Month 1-12 | £47.48 | £569.76 | £228.00 |

---

### Scenario C: Full Optimization
| Optimization | Monthly Savings | Annual Savings |
|--------------|-----------------|----------------|
| Delete unused resources | £19.00 | £228.00 |
| Optimize AI usage | £5.00 | £60.00 |
| Storage lifecycle | £0.30 | £3.60 |
| Reserved capacity | £12.00 | £144.00 |
| **Total** | **£36.30** | **£435.60** |

**Optimized Annual Cost: £362.16** (vs £797.76 current)  
**Total Savings: £435.60/year (55% reduction)**

---

## Recommendations Summary

### Priority 1: Immediate (Do This Week)
✅ Delete unused Container Registries (£15/month)  
✅ Delete orphaned Container Instance (£4/month)  
**Total Savings: £19/month**

### Priority 2: Short-Term (Next 1-3 Months)
🔄 Implement AI response caching (£5/month)  
🔄 Implement storage lifecycle policies (£0.30/month)  
🔄 Monitor App Service usage for right-sizing  
**Total Savings: £5.30/month**

### Priority 3: Medium-Term (3-6 Months)
📅 Evaluate reserved capacity (£12/month)  
📅 Consider App Service downgrade if usage allows (£22.80/month)  
**Total Savings: £34.80/month**

### Priority 4: Long-Term (6-12 Months)
🔮 Evaluate Azure Container Apps migration  
🔮 Assess Azure AI Search for large-scale vector search  

---

## Cost Optimization Checklist

- [ ] Run `cleanup_unused_resources.sh` script
- [ ] Set up monthly budget alerts (£75 threshold)
- [ ] Enable Application Insights for cost tracking
- [ ] Implement AI response caching
- [ ] Configure storage lifecycle policies
- [ ] Monitor App Service metrics for 30 days
- [ ] Evaluate reserved capacity options
- [ ] Review OpenAI usage patterns
- [ ] Document cost optimization decisions
- [ ] Schedule quarterly cost reviews

---

## Cost Comparison: Alternative Architectures

### Option A: Current Architecture (Azure App Service)
**Monthly Cost:** £47.48 (after cleanup)  
**Pros:** Simple deployment, always available, predictable costs  
**Cons:** Fixed cost regardless of usage

---

### Option B: Azure Container Apps (Consumption)
**Monthly Cost:** £25-35 (estimated)  
**Pros:** Pay-per-use, auto-scaling, modern architecture  
**Cons:** More complex setup, cold start latency

---

### Option C: Azure Functions (Serverless)
**Monthly Cost:** £10-20 (estimated)  
**Pros:** Very cheap for low traffic, auto-scaling  
**Cons:** Cold start issues, 10-minute timeout limit, major refactoring needed

---

### Option D: Azure Kubernetes Service (AKS)
**Monthly Cost:** £150-200 (estimated)  
**Pros:** Full control, enterprise-grade  
**Cons:** Much more expensive, complex management  
**Not Recommended:** Overkill for current scale

---

## Conclusion

By implementing the immediate optimization recommendations, the application can achieve:

- **29% cost reduction** (from £66.48 to £47.48/month)
- **£228/year savings** with minimal effort
- Potential for **55% total reduction** with full optimization

The current App Service architecture is cost-effective for the application's scale. Focus on cleaning up unused resources first, then optimize AI usage and storage lifecycle management.

---

## Review Schedule

- **Weekly:** Monitor costs in Azure Portal
- **Monthly:** Review budget alerts and usage trends
- **Quarterly:** Full cost optimization review
- **Annually:** Evaluate alternative architectures and reserved capacity

---

## Contact & Support

For cost-related questions:
1. Check Azure Cost Management portal
2. Review this document
3. Run cost analysis scripts in `azure_deployment/scripts/`
4. Contact Azure billing support if needed
