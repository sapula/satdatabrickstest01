# Architecture Documentation

## System Overview

This project implements a modern data engineering solution using Databricks Delta Live Tables (DLT) with CI/CD automation.

## Data Architecture - Medallion Pattern

### Bronze Layer (Raw/Landing)
**Purpose**: Ingest raw data from source systems without transformation

- `bronze_orders`: Raw TPC-H orders data
- `bronze_lineitem`: Raw line item transactions
- `bronze_part`: Raw product/part catalog

**Characteristics**:
- No transformations applied
- Full historical data retained
- Source of truth for auditing
- Optimized with Z-ordering on key columns

### Silver Layer (Cleaned/Conformed)
**Purpose**: Cleaned, validated, and joined data ready for analytics

- `silver_order_details`: Joined orders + lineitems + parts with data quality

**Data Quality Rules**:
```python
@dlt.expect_or_drop("valid_orderkey", "o_orderkey IS NOT NULL")
@dlt.expect_or_drop("valid_partkey", "l_partkey IS NOT NULL")
@dlt.expect_or_drop("valid_quantity", "l_quantity > 0")
```

**Characteristics**:
- Data quality expectations enforced
- Invalid rows dropped and tracked
- Standardized schema
- Deduplication applied
- Change Data Capture (CDC) enabled

### Gold Layer (Business/Analytics)
**Purpose**: Aggregated business metrics ready for consumption

- `gold_top_selling_products_last_30_days`: Recent product performance
- `gold_product_sales_metrics`: Comprehensive product analytics with revenue

**Characteristics**:
- Pre-aggregated for performance
- Business logic applied
- Optimized for BI tools
- SLA-driven refresh schedules

## Deployment Architecture

### Environments

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│     DEV     │  -->  │   STAGING   │  -->  │    PROD     │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ 1 worker    │       │ 2 workers   │       │ 4 workers   │
│ i3.xlarge   │       │ i3.xlarge   │       │ i3.2xlarge  │
│ Development │       │ Production  │       │ Production  │
│ mode        │       │ mode        │       │ mode        │
│ On-demand   │       │ On-demand   │       │ Continuous  │
└─────────────┘       └─────────────┘       └─────────────┘
```

### CI/CD Pipeline Flow

```
Developer
   │
   ├─> Create Feature Branch (from dev)
   │
   ├─> Make Changes
   │
   ├─> Create Pull Request
   │
   ├─> CI Workflow Triggers:
   │   ├─> Black (formatting check)
   │   ├─> Ruff (linting)
   │   ├─> MyPy (type checking)
   │   ├─> Pytest (unit tests)
   │   └─> Bundle validation
   │
   ├─> Code Review & Approval
   │
   ├─> Merge to dev
   │
   ├─> Auto-Deploy to DEV
   │
   ├─> Testing in DEV
   │
   ├─> Create PR: dev -> main
   │
   ├─> Approval Required
   │
   ├─> Merge to main
   │
   └─> Deploy to STAGING/PROD (manual approval)
```

### GitHub Actions Workflows

#### 1. CI Workflow (`ci.yml`)
**Trigger**: PR to main/dev, push to dev

**Jobs**:
- `lint-and-test`: Code quality and testing
- `validate-bundle`: Databricks configuration validation

#### 2. Deploy Dev (`deploy-dev.yml`)
**Trigger**: Push to dev branch

**Steps**:
1. Checkout code
2. Install Databricks CLI
3. Validate bundle
4. Deploy to dev workspace
5. (Optional) Run DLT pipeline

#### 3. Deploy Prod (`deploy-prod.yml`)
**Trigger**: Push to main or manual dispatch

**Steps**:
1. Environment selection (staging/prod)
2. Approval gate (GitHub environments)
3. Validate bundle
4. Deploy to target workspace
5. Create deployment summary

## Infrastructure as Code (IaC)

### Databricks Asset Bundles

The `databricks.yml` defines all infrastructure:

```yaml
bundle:
  name: satdatabrickstest01

targets:
  dev:     # Development environment
  staging: # Pre-production environment
  prod:    # Production environment
```

**Benefits**:
- Reproducible deployments
- Version-controlled infrastructure
- Environment parity
- Automated validation

### Resource Configuration

`resources/dlt_pipeline.yml` defines:
- Pipeline configuration
- Cluster specifications
- Data quality settings
- Notification rules
- Catalog/schema targets

## Security Architecture

### Authentication & Authorization

**Development**:
- Personal Access Tokens (PAT)
- User-level permissions
- Direct workspace access

**Staging/Production**:
- Service Principal authentication
- Least-privilege access
- Run-as service principal for pipeline execution

### Secrets Management

**Local Development**:
- `.env` file (git-ignored)
- Environment variables

**CI/CD**:
- GitHub Secrets
- Encrypted at rest
- Scoped to environments

**Databricks**:
- Databricks Secrets (optional)
- Secret scopes for sensitive configs

## Monitoring & Observability

### DLT Built-in Monitoring

- **Data Quality Metrics**: Track expectation failures
- **Pipeline Lineage**: Visualize data flow
- **Event Log**: Detailed execution history
- **Auto-scaling Metrics**: Cluster utilization

### Notifications

- Email alerts on:
  - Pipeline failures
  - Data quality issues
  - Update failures

### Logging

- Spark logs in Databricks workspace
- GitHub Actions logs for deployments
- DLT event log for data quality

## Scalability Considerations

### Horizontal Scaling
- Configure `num_workers` per environment
- Auto-scaling enabled in production
- Photon acceleration for better performance

### Vertical Scaling
- Larger instance types in production (i3.2xlarge)
- Memory-optimized for large aggregations

### Performance Optimization
- Z-ordering on frequently filtered columns
- Delta table optimization enabled
- Photon engine enabled
- Change Data Feed for incremental processing

## Disaster Recovery

### Backup Strategy
- Delta tables are versioned (time travel)
- 30-day retention default
- Can restore to any point in time

### Recovery Procedures
1. Identify failure point using DLT event log
2. Rollback Delta tables if needed:
   ```sql
   RESTORE TABLE catalog.schema.table TO VERSION AS OF 123
   ```
3. Re-run pipeline from last successful state
4. Validate data quality metrics

## Cost Optimization

1. **Development**: Single worker, on-demand execution
2. **Auto-shutdown**: Clusters terminate after inactivity
3. **Spot Instances**: Consider for non-critical workloads
4. **Photon**: Better performance = shorter runtime = lower cost
5. **Incremental Processing**: Only process new/changed data

## Future Enhancements

- [ ] Add data lineage tracking with Unity Catalog
- [ ] Implement data retention policies
- [ ] Add SLI/SLO monitoring
- [ ] Integrate with data catalog (Atlan, Collibra)
- [ ] Add anomaly detection in gold layer
- [ ] Implement incremental loading from source
- [ ] Add dbt integration for transformations
- [ ] Set up cost monitoring and alerts
