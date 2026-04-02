# 🏗️ Credit Risk Analysis - Modular Architecture with SQLite Integration Plan

## 📋 Complete Architecture Overview

### 🎯 **Architecture Layers with SQLite Integration**

```
🏛️ CREDIT RISK ANALYSIS - MODULAR ARCHITECTURE
├─────────────────────────────────────────────────────────────────────────────────
│ 🌐 Layer 1: API Gateway & Routing
├─────────────────────────────────────────────────────────────────────────────────
│ 🔧 Layer 2: Service Layer (Business Logic)
├─────────────────────────────────────────────────────────────────────────────────
│ 🗄️ Layer 3: Repository Layer (Data Abstraction) ← SQLite Integration Point
├─────────────────────────────────────────────────────────────────────────────────
│ 💾 Layer 4: Data Storage (File System ↔️ SQLite Database)
├─────────────────────────────────────────────────────────────────────────────────
│ 🤖 Layer 5: Agent System (AI/ML Services)
├─────────────────────────────────────────────────────────────────────────────────
│ 🛠️ Layer 6: Infrastructure (Config, Logging, DI)
└─────────────────────────────────────────────────────────────────────────────────
```

---

## 🗄️ **Layer 3: Repository Layer - SQLite Integration Hub**

### **📁 Complete Repository Structure**
```
app/repositories/
├── __init__.py                          # Repository factory exports
│
├── interfaces/                          # Abstract Contracts
│   ├── __init__.py
│   ├── base_repository.py              # Base repository interface
│   ├── company_repository_interface.py # Company data operations
│   ├── sic_repository_interface.py     # SIC code operations
│   ├── revenue_repository_interface.py # Revenue data operations
│   └── workflow_repository_interface.py# Workflow state operations
│
├── implementations/                     # Concrete Implementations
│   ├── __init__.py
│   │
│   ├── file_based/                     # Current File System (Phase 1)
│   │   ├── __init__.py
│   │   ├── file_company_repository.py  # CSV/Excel company data
│   │   ├── file_sic_repository.py      # SIC codes from files
│   │   └── file_revenue_repository.py  # Revenue calculations
│   │
│   └── sqlite/                         # Future SQLite (Phase 2+)
│       ├── __init__.py
│       ├── sqlite_company_repository.py# SQLite company operations
│       ├── sqlite_sic_repository.py    # SQLite SIC operations
│       └── sqlite_revenue_repository.py# SQLite revenue operations
│
├── database/                           # SQLite Infrastructure
│   ├── __init__.py
│   ├── connection.py                   # SQLite connection management
│   ├── schema.py                       # Database schema definitions
│   ├── migrations/                     # Database migrations
│   │   ├── __init__.py
│   │   ├── 001_initial_schema.py       # Initial tables
│   │   ├── 002_sic_enhancements.py     # SIC improvements
│   │   └── migration_runner.py         # Migration execution
│   │
│   └── models/                         # SQLAlchemy Models (Optional)
│       ├── __init__.py
│       ├── company.py                  # Company table model
│       ├── sic_code.py                 # SIC codes table model
│       └── workflow_session.py         # Workflow state model
│
└── factory.py                          # Repository Factory (DI Integration)
```

---

## 🔄 **Data Flow Architecture: Current vs Future**

### **🔄 Current Data Flow (File-Based)**
```
User Request
    ↓
API Routes (flask_main.py)
    ↓
Direct File Access
    ↓
pandas.read_csv/excel
    ↓
In-Memory DataFrames
    ↓
Business Logic Processing
    ↓
JSON Response
```

### **🔄 New Modular Flow (SQLite-Ready)**
```
User Request
    ↓
API Gateway (app/api/gateway.py)
    ↓
Route Handler (app/api/routes/data_routes.py)
    ↓
Service Layer (app/services/company_service.py)
    ↓
Repository Interface (app/repositories/interfaces/company_repository_interface.py)
    ↓                                           ↓
File Implementation                    SQLite Implementation
(Current - Phase 1)                      (Future - Phase 2+)
    ↓                                           ↓
CSV/Excel Files                        SQLite Database
    ↓                                           ↓
pandas.read_csv                        pd.read_sql_query
    ↓                                           ↓
DataFrames ←←←←←←←← Repository Interface →→→→→→→→ DataFrames
    ↓
Service Layer Processing
    ↓
JSON Response
```

---

## 🏗️ **Detailed Implementation Plan**

### **📅 Phase 1: Foundation + SQLite Preparation (Week 1)**

#### **Step 1A: Repository Interfaces**
```python
# app/repositories/interfaces/company_repository_interface.py
from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional, List, Dict, Any

class CompanyRepositoryInterface(ABC):
    """Abstract interface for company data operations"""
    
    @abstractmethod
    def get_all_companies(self) -> pd.DataFrame:
        """Get all companies as DataFrame"""
        pass
    
    @abstractmethod
    def get_company_by_id(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Get specific company by ID"""
        pass
    
    @abstractmethod
    def update_company_sic(self, company_id: str, sic_code: str, confidence: float) -> bool:
        """Update company SIC code prediction"""
        pass
    
    @abstractmethod
    def update_company_revenue(self, company_id: str, revenue: float) -> bool:
        """Update company revenue data"""
        pass
    
    @abstractmethod
    def search_companies(self, query: str) -> pd.DataFrame:
        """Search companies by name or other criteria"""
        pass
    
    @abstractmethod
    def get_companies_by_sic(self, sic_code: str) -> pd.DataFrame:
        """Get companies by SIC code"""
        pass
```

#### **Step 1B: Current File Implementation**
```python
# app/repositories/implementations/file_based/file_company_repository.py
from repositories.interfaces.company_repository_interface import CompanyRepositoryInterface
import pandas as pd
import os

class FileCompanyRepository(CompanyRepositoryInterface):
    """File-based implementation using current CSV/Excel logic"""
    
    def __init__(self, data_path: str = "data/"):
        self.data_path = data_path
        self._company_data: Optional[pd.DataFrame] = None
    
    def get_all_companies(self) -> pd.DataFrame:
        """Load from CSV/Excel files (your current logic)"""
        if self._company_data is None:
            # Use existing file loading logic from flask_main.py
            self._company_data = self._load_from_files()
        return self._company_data.copy()
    
    def get_company_by_id(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Get specific company from loaded DataFrame"""
        companies = self.get_all_companies()
        company_row = companies[companies['Company_Registration'] == company_id]
        return company_row.iloc[0].to_dict() if not company_row.empty else None
    
    def _load_from_files(self) -> pd.DataFrame:
        """Your existing file loading logic goes here"""
        # Copy logic from flask_main.py load_company_data()
        pass
```

#### **Step 1C: SQLite Infrastructure (Ready but Unused)**
```python
# app/repositories/database/connection.py
import sqlite3
import pandas as pd
from typing import Optional
from contextlib import contextmanager

class SQLiteConnection:
    """SQLite connection management"""
    
    def __init__(self, db_path: str = "data/credit_risk.db"):
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        try:
            conn = sqlite3.connect(self.db_path)
            yield conn
        finally:
            conn.close()
    
    def execute_query(self, query: str, params=None) -> pd.DataFrame:
        """Execute SELECT query and return DataFrame"""
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)
    
    def execute_update(self, query: str, params=None) -> int:
        """Execute INSERT/UPDATE/DELETE query"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or [])
            conn.commit()
            return cursor.rowcount
```

#### **Step 1D: SQLite Schema Definition**
```python
# app/repositories/database/schema.py
SCHEMA_DEFINITIONS = {
    'companies': '''
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_registration TEXT UNIQUE NOT NULL,
            company_name TEXT NOT NULL,
            sic_code TEXT,
            sic_description TEXT,
            predicted_sic TEXT,
            sic_confidence REAL,
            revenue REAL,
            turnover_estimate REAL,
            business_description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''',
    
    'sic_codes': '''
        CREATE TABLE IF NOT EXISTS sic_codes (
            sic_code TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            section TEXT,
            division TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''',
    
    'workflow_sessions': '''
        CREATE TABLE IF NOT EXISTS workflow_sessions (
            session_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            input_data TEXT,
            results TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''',
    
    'sic_predictions': '''
        CREATE TABLE IF NOT EXISTS sic_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_registration TEXT,
            business_description TEXT,
            predicted_sic TEXT,
            confidence REAL,
            algorithm_used TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_registration) REFERENCES companies(company_registration)
        )
    '''
}
```

#### **Step 1E: Repository Factory with Configuration**
```python
# app/repositories/factory.py
from app.infrastructure.config.app_config import get_config
from repositories.interfaces.company_repository_interface import CompanyRepositoryInterface
from repositories.implementations.file_based.file_company_repository import FileCompanyRepository
from repositories.implementations.sqlite.sqlite_company_repository import SQLiteCompanyRepository

class RepositoryFactory:
    """Factory for creating repository implementations based on configuration"""
    
    @staticmethod
    def create_company_repository() -> CompanyRepositoryInterface:
        """Create company repository based on configuration"""
        config = get_config()
        
        if config.DATABASE_TYPE == 'sqlite':
            return SQLiteCompanyRepository(config.SQLITE_PATH)
        else:
            return FileCompanyRepository(config.DATA_PATH)
    
    @staticmethod
    def create_sic_repository() -> SicRepositoryInterface:
        """Create SIC repository based on configuration"""
        config = get_config()
        
        if config.DATABASE_TYPE == 'sqlite':
            return SQLiteSicRepository(config.SQLITE_PATH)
        else:
            return FileSicRepository(config.DATA_PATH)
```

---

## 🔧 **Service Layer Integration**

### **📁 Services Using Repository Pattern**
```python
# app/services/company_service.py
from repositories.factory import RepositoryFactory

class CompanyService:
    """Company business logic service"""
    
    def __init__(self):
        # Repository is injected based on configuration
        self.company_repo = RepositoryFactory.create_company_repository()
        self.sic_repo = RepositoryFactory.create_sic_repository()
    
    def get_all_companies(self) -> Dict[str, Any]:
        """Get all companies with business logic"""
        companies = self.company_repo.get_all_companies()
        
        # Add business logic processing
        processed_companies = self._add_calculated_fields(companies)
        
        return {
            'success': True,
            'data': processed_companies.to_dict('records'),
            'total_count': len(processed_companies),
            'data_source': 'sqlite' if self._is_using_sqlite() else 'files'
        }
    
    def predict_company_sic(self, company_id: str, business_description: str) -> Dict[str, Any]:
        """Predict SIC code for company"""
        # Business logic stays the same regardless of data source
        prediction_result = self._run_sic_prediction(business_description)
        
        # Update via repository interface
        success = self.company_repo.update_company_sic(
            company_id, 
            prediction_result['sic_code'], 
            prediction_result['confidence']
        )
        
        return {
            'success': success,
            'prediction': prediction_result,
            'data_source': 'sqlite' if self._is_using_sqlite() else 'files'
        }
```

---

## 🌐 **API Layer with SQLite Support**

### **📁 Data Routes with Dual Mode Support**
```python
# app/api/routes/data_routes.py
from flask import Blueprint, request, jsonify
from app.services.company_service import CompanyService
from app.services.data_migration_service import DataMigrationService

bp = Blueprint('data', __name__)

@bp.route('/api/data')
def get_company_data():
    """Get company data - works with both file and SQLite"""
    company_service = CompanyService()
    result = company_service.get_all_companies()
    return jsonify(result)

@bp.route('/api/data/source-info')
def get_data_source_info():
    """Get information about current data source"""
    from app.infrastructure.config.app_config import get_config
    config = get_config()
    
    return jsonify({
        'current_source': config.DATABASE_TYPE,
        'sqlite_available': config.SQLITE_ENABLED,
        'migration_available': config.DATABASE_TYPE == 'file',
        'database_path': config.SQLITE_PATH if config.DATABASE_TYPE == 'sqlite' else None,
        'file_data_path': config.DATA_PATH if config.DATABASE_TYPE == 'file' else None
    })

# Future migration endpoints (Phase 2+)
@bp.route('/api/data/migrate-to-sqlite', methods=['POST'])
def migrate_to_sqlite():
    """Migrate from files to SQLite database"""
    migration_service = DataMigrationService()
    result = migration_service.migrate_files_to_sqlite()
    return jsonify(result)

@bp.route('/api/data/sqlite/status')
def sqlite_status():
    """Get SQLite database status and statistics"""
    if get_config().DATABASE_TYPE != 'sqlite':
        return jsonify({'error': 'SQLite not active'}), 400
    
    # Return database statistics, table counts, etc.
    return jsonify({
        'status': 'active',
        'tables': ['companies', 'sic_codes', 'workflow_sessions'],
        'total_companies': 1000,  # Query actual count
        'last_updated': '2025-09-27T10:30:00Z'
    })
```

---

## ⚙️ **Configuration System**

### **📁 Environment-Based Data Source Configuration**
```python
# app/infrastructure/config/app_config.py
import os
from dataclasses import dataclass

@dataclass
class AppConfig:
    """Application configuration with SQLite support"""
    
    # Data source configuration
    DATABASE_TYPE: str = os.getenv('DATABASE_TYPE', 'file')  # 'file' or 'sqlite'
    DATA_PATH: str = os.getenv('DATA_PATH', 'data/')
    SQLITE_PATH: str = os.getenv('SQLITE_PATH', 'data/credit_risk.db')
    SQLITE_ENABLED: bool = os.getenv('SQLITE_ENABLED', 'true').lower() == 'true'
    
    # Migration settings
    MIGRATION_BACKUP_PATH: str = os.getenv('MIGRATION_BACKUP_PATH', 'data/backup/')
    AUTO_MIGRATE: bool = os.getenv('AUTO_MIGRATE', 'false').lower() == 'true'
    
    # Performance settings
    DATABASE_POOL_SIZE: int = int(os.getenv('DATABASE_POOL_SIZE', '10'))
    CACHE_ENABLED: bool = os.getenv('CACHE_ENABLED', 'true').lower() == 'true'
```

### **📁 Environment Files**
```bash
# .env.development (Current setup)
DATABASE_TYPE=file
DATA_PATH=data/
SQLITE_ENABLED=true

# .env.production (Future setup)
DATABASE_TYPE=sqlite
SQLITE_PATH=/app/data/production.db
SQLITE_ENABLED=true
```

---

## 🔄 **Migration Strategy**

### **📅 Migration Phases**

#### **Phase 1: Foundation (Immediate)**
- ✅ **Repository interfaces created** - Abstract contracts
- ✅ **File implementation wrapped** - Current logic preserved
- ✅ **SQLite infrastructure ready** - Connection, schema, models
- ✅ **Configuration system** - Environment-based switching
- ✅ **No functionality changes** - Everything works as before

#### **Phase 2: SQLite Activation (Future)**
- ✅ **Data migration tools** - CSV → SQLite converters
- ✅ **SQLite implementations** - Full repository implementations
- ✅ **Configuration switch** - `DATABASE_TYPE=sqlite`
- ✅ **Performance optimization** - SQL queries vs file loading

#### **Phase 3: Advanced Features (Optional)**
- ✅ **Database indexing** - Performance optimization
- ✅ **Connection pooling** - Concurrent request handling
- ✅ **Caching layers** - Redis/memory caching
- ✅ **Database migrations** - Schema evolution tools

---

## 🎯 **Key Benefits of This Architecture**

### **🔄 Seamless Migration Path**
```python
# Change one configuration setting
DATABASE_TYPE = "sqlite"  # Switch from "file" to "sqlite"

# Everything else works exactly the same:
# - All API endpoints unchanged
# - All business logic unchanged  
# - All service interfaces unchanged
# - Only data source implementation changes
```

### **🧪 Testing Advantages**
```python
# Easy to test with different data sources
def test_company_service():
    # Test with file repository
    config.DATABASE_TYPE = 'file'
    service = CompanyService()
    result = service.get_all_companies()
    
    # Test with SQLite repository
    config.DATABASE_TYPE = 'sqlite'
    service = CompanyService()
    result = service.get_all_companies()
    
    # Same business logic, different data sources
```

### **📊 Performance Benefits**
```python
# File-based (Current)
- Startup time: Load all CSV/Excel files
- Query time: Scan entire DataFrames
- Memory usage: Keep all data in RAM

# SQLite-based (Future)  
- Startup time: Just establish connection
- Query time: Indexed SQL queries
- Memory usage: Load only needed data
```

---

## 🚀 **Implementation Decision Points**

### **Should I proceed with this SQLite-ready architecture?**

**What you get immediately (Phase 1):**
- ✅ **Clean repository pattern** - Better organized data access
- ✅ **Future-ready infrastructure** - SQLite migration path prepared
- ✅ **Same functionality** - No changes to current behavior
- ✅ **Better testing** - Mock repositories for unit tests

**What stays the same:**
- ✅ **All your CSV/Excel files** - Still used as primary data source
- ✅ **All API responses** - Identical JSON responses
- ✅ **Performance** - No slowdown in Phase 1
- ✅ **Deployment** - Same deployment process

**Future migration (Phase 2+):**
- 🚀 **One configuration change** - Switch to SQLite
- 🚀 **Automatic data migration** - Tools to convert files to database
- 🚀 **Performance boost** - SQL queries vs file scanning
- 🚀 **Advanced features** - Database indexing, relationships, constraints

**Ready to start Phase 1: SQLite-Ready Foundation?**