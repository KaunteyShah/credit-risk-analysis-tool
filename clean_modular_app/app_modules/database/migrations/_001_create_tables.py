"""
Database migration for Phase 1: Schema Creation
Creates all necessary tables for SQLite migration from CSV files.
"""

MIGRATION_001_CREATE_TABLES = """
-- Migration 001: Create comprehensive schema matching API requirements
-- Created: {timestamp}

-- Companies table (matching models.py Company class and Sample_data2.csv structure)
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Core identification fields
    company_number TEXT,
    company_name TEXT,
    status TEXT DEFAULT 'Active',
    incorporation_date TEXT,
    dissolution_date TEXT,
    company_type TEXT,
    jurisdiction TEXT,
    
    -- Address fields (from CSV)
    address_line_1 TEXT,
    address_line_2 TEXT,
    address_line_3 TEXT,
    city TEXT,
    post_code TEXT,
    country TEXT,
    registered_office_address TEXT,
    
    -- Contact information (from CSV)
    phone TEXT,
    email TEXT,
    website TEXT,
    
    -- Business information (from CSV and models)
    business_description TEXT,
    
    -- Company House specific fields (from models.py)
    accounts_next_due_date TEXT,
    accounts_last_made_up_date TEXT,
    confirmation_statement_next_due_date TEXT,
    confirmation_statement_last_made_up_date TEXT,
    
    -- Boolean flags (from models.py)
    can_file BOOLEAN DEFAULT TRUE,
    has_been_liquidated BOOLEAN DEFAULT FALSE,
    has_charges BOOLEAN DEFAULT FALSE,
    has_insolvency_history BOOLEAN DEFAULT FALSE,
    undeliverable_registered_office_address BOOLEAN DEFAULT FALSE,
    
    -- Additional CSV fields
    duns_number TEXT,
    ownership_type TEXT,
    entity_type TEXT,
    parent_company TEXT,
    parent_country TEXT,
    global_ultimate_company TEXT,
    global_ultimate_country TEXT,
    
    -- Metadata
    date_of_creation TEXT,
    date_of_cessation TEXT,
    etag TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Company financial data table (matching Sample_data2.csv)
CREATE TABLE IF NOT EXISTS company_financials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    -- Financial metrics from CSV
    sales_usd REAL,
    pre_tax_profit_usd REAL,
    assets_usd REAL,
    employees_single_site INTEGER,
    employees_total INTEGER,
    -- Metadata
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
);

-- SIC codes table (from SIC_codes.xlsx)
CREATE TABLE IF NOT EXISTS sic_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sic_code TEXT UNIQUE NOT NULL,
    sic_description TEXT,
    section TEXT,
    division TEXT,
    group_code TEXT,
    class_code TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Company SIC codes table with detailed SIC information
CREATE TABLE IF NOT EXISTS company_sic_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    company_name TEXT NOT NULL,
    sic_code_id INTEGER,
    
    -- Detailed SIC code fields from CSV
    us_8_digit_sic_code TEXT,
    us_8_digit_sic_description TEXT,
    us_sic_1987_code TEXT,
    us_sic_1987_description TEXT,
    uk_sic_2007_code TEXT,
    uk_sic_2007_description TEXT,
    naics_2022_code TEXT,
    naics_2022_description TEXT,
    anzsic_2006_code TEXT,
    anzsic_2006_description TEXT,
    
    is_primary BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE,
    FOREIGN KEY (sic_code_id) REFERENCES sic_codes (id) ON DELETE SET NULL
);

-- API audit log table (matching audit_middleware.py requirements)
CREATE TABLE IF NOT EXISTS api_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    response_status INTEGER,
    response_time_ms REAL,
    response_size_bytes INTEGER,
    ip_address TEXT,
    user_agent TEXT,
    request_payload TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- SIC prediction history table (for AI predictions tracking)
CREATE TABLE IF NOT EXISTS sic_prediction_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    company_name TEXT,
    business_description TEXT,
    predicted_sic_code TEXT,
    predicted_sic_description TEXT,
    confidence_score REAL,
    model_version TEXT DEFAULT '1.0',
    prediction_method TEXT DEFAULT 'AI',
    prediction_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT DEFAULT 'system',
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE SET NULL
);

-- Performance optimization indexes
CREATE INDEX IF NOT EXISTS idx_companies_number ON companies (company_number);
CREATE INDEX IF NOT EXISTS idx_companies_name ON companies (company_name);
CREATE INDEX IF NOT EXISTS idx_companies_status ON companies (status);
CREATE INDEX IF NOT EXISTS idx_companies_jurisdiction ON companies (jurisdiction);
CREATE INDEX IF NOT EXISTS idx_sic_codes_code ON sic_codes (sic_code);
CREATE INDEX IF NOT EXISTS idx_company_sic_codes_company ON company_sic_codes (company_id);
CREATE INDEX IF NOT EXISTS idx_company_sic_codes_company_name ON company_sic_codes (company_name);
CREATE INDEX IF NOT EXISTS idx_company_sic_codes_uk_sic ON company_sic_codes (uk_sic_2007_code);
CREATE INDEX IF NOT EXISTS idx_company_sic_codes_us_sic ON company_sic_codes (us_sic_1987_code);
CREATE INDEX IF NOT EXISTS idx_company_sic_codes_naics ON company_sic_codes (naics_2022_code);
CREATE INDEX IF NOT EXISTS idx_company_financials_company ON company_financials (company_id);
CREATE INDEX IF NOT EXISTS idx_api_audit_endpoint ON api_audit_log (endpoint);
CREATE INDEX IF NOT EXISTS idx_api_audit_timestamp ON api_audit_log (timestamp);
CREATE INDEX IF NOT EXISTS idx_api_audit_status ON api_audit_log (response_status);
CREATE INDEX IF NOT EXISTS idx_sic_prediction_company ON sic_prediction_history (company_id);
CREATE INDEX IF NOT EXISTS idx_sic_prediction_timestamp ON sic_prediction_history (prediction_timestamp);

-- Triggers for updating updated_at timestamps
CREATE TRIGGER IF NOT EXISTS update_companies_timestamp 
    AFTER UPDATE ON companies
    BEGIN
        UPDATE companies SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_sic_codes_timestamp 
    AFTER UPDATE ON sic_codes
    BEGIN
        UPDATE sic_codes SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_company_financials_timestamp 
    AFTER UPDATE ON company_financials
    BEGIN
        UPDATE company_financials SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;
"""

# Rollback migration
MIGRATION_001_ROLLBACK = """
-- Rollback Migration 001: Drop all tables and indexes

DROP TRIGGER IF EXISTS update_company_financials_timestamp;
DROP TRIGGER IF EXISTS update_sic_codes_timestamp;
DROP TRIGGER IF EXISTS update_companies_timestamp;

DROP INDEX IF EXISTS idx_sic_prediction_timestamp;
DROP INDEX IF EXISTS idx_sic_prediction_company;
DROP INDEX IF EXISTS idx_api_audit_status;
DROP INDEX IF EXISTS idx_api_audit_timestamp;
DROP INDEX IF EXISTS idx_api_audit_endpoint;
DROP INDEX IF EXISTS idx_company_financials_company;
DROP INDEX IF EXISTS idx_company_sic_codes_sic;
DROP INDEX IF EXISTS idx_company_sic_codes_company;
DROP INDEX IF EXISTS idx_sic_codes_code;
DROP INDEX IF EXISTS idx_companies_sic_codes;
DROP INDEX IF EXISTS idx_companies_jurisdiction;
DROP INDEX IF EXISTS idx_companies_status;
DROP INDEX IF EXISTS idx_companies_name;
DROP INDEX IF EXISTS idx_companies_number;

DROP TABLE IF EXISTS sic_prediction_history;
DROP TABLE IF EXISTS api_audit_log;
DROP TABLE IF EXISTS company_financials;
DROP TABLE IF EXISTS company_sic_codes;
DROP TABLE IF EXISTS sic_codes;
DROP TABLE IF EXISTS companies;
"""