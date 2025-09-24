# Database Integration Plan: CSV to SQLite

## 1. Introduction
This document outlines a detailed plan for migrating the existing CSV-based data store to an embedded SQLite database. The goals of this migration are:

- Improve performance by enabling indexed queries and filtering
- Ensure data integrity through constraints and normalization
- Provide audit trails for data changes and API calls
- Simplify development by centralizing data access
- Support views for reporting and analytics

## 2. Current State
- **Data Files**: `Sample_data2.csv` (509 rows, 34+ columns) and `SIC_codes.xlsx` (751 codes)
- **Processing**: Loaded entirely into pandas DataFrames in memory
- **Limitations**:
  - Full file scans on every API call
  - No relational constraints or foreign keys
  - No built-in audit logging or timestamp history
  - Difficult to support time-series and change history

## 3. Proposed Schema

### 3.1 Core Tables
```sql
-- Companies
CREATE TABLE companies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  company_name TEXT NOT NULL,
  registration_number TEXT UNIQUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Addresses
CREATE TABLE company_addresses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  company_id INTEGER NOT NULL,
  country TEXT NOT NULL,
  ...,
  FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- Financials (time-series)
CREATE TABLE company_financials (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  company_id INTEGER NOT NULL,
  fiscal_year INTEGER,
  employees_total INTEGER,
  sales_usd DECIMAL(15,2),
  ...,
  FOREIGN KEY(company_id) REFERENCES companies(id)
);

-- SIC Classifications
CREATE TABLE company_sic_classifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  company_id INTEGER NOT NULL,
  sic_code TEXT NOT NULL,
  classification_type TEXT,
  accuracy_score DECIMAL(5,4),
  ...,
  FOREIGN KEY(company_id) REFERENCES companies(id)
);

-- Reference SIC codes
CREATE TABLE sic_codes (
  code TEXT PRIMARY KEY,
  description TEXT NOT NULL
);
```  

### 3.2 Audit & History Tables
```sql
-- API Audit Log
CREATE TABLE api_audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  endpoint TEXT NOT NULL,
  method TEXT NOT NULL,
  request_params TEXT,
  response_status INTEGER,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Data Change History
CREATE TABLE data_change_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  table_name TEXT NOT NULL,
  record_id INTEGER NOT NULL,
  field_name TEXT NOT NULL,
  old_value TEXT,
  new_value TEXT,
  change_type TEXT,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```  

## 4. Phased Implementation

### Phase 1: Database Architecture & Schema Design
- Finalize normalization strategy and table definitions
- Create SQLite `credit_risk.db` and apply schema
- Define indexes for performance on frequently filtered fields
- Set up triggers for `updated_at` timestamps
- Deliverable: `init_db.py` script and ER diagram

### Phase 2: Migration Infrastructure
- Write data loader that reads CSV and populates tables
- Implement validation: row counts, distinct counts, checksum
- Backup original CSV before migration
- Deliverable: `migrate_data.py`, migration logs, validation report

### Phase 3: API Layer Integration
- Build `DatabaseManager` abstraction for queries and updates
- Update Flask endpoints to use SQL queries instead of pandas
- Add audit logging middleware to record API calls in `api_audit_log`
- Implement caching strategy for heavy queries
- Deliverable: Updated `flask_main.py` and `db_manager.py`

### Phase 4: Testing & Deployment
- Unit tests for data migration and query correctness
- Integration tests for Flask endpoints against SQLite
- Performance benchmarks vs. CSV approach
- Prepare Docker image with SQLite database file
- Deploy to Azure (App Service) and set up backups
- Deliverable: Test suite, CI/CD pipeline updates, deployment guide

## 5. Pros & Cons

**Pros**:
- ACID compliance and referential integrity
- Faster filtered queries via indexes
- Built-in audit and change history
- Simplified development and debugging
- Support for complex views and reporting

**Cons**:
- Single-writer lock on SQLite (rare write contention)
- Migration effort and downtime planning
- Maintenance of backup/restore strategy
- Learning curve for new query layer

## 6. Next Steps
1. Review schema and provide feedback
2. Kick off Phase 1: schema creation
3. Schedule migration and testing windows
4. Update project documentation with new integration guide

---
*Prepared on 25 September 2025*