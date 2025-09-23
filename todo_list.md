# Credit Risk Analysis Tool - TODO List

## Priority Scale
- **1-3**: Critical/High Priority (Security, Data Safety, Core Functionality)
- **4-6**: Medium Priority (Performance, User Experience, Code Quality)
- **7-10**: Low Priority (Nice-to-have, Documentation, Optimization)

---

## 🔴 Critical Priority (1-3)

### Priority 1 - Data Safety & Security
- [ ] **Implement atomic CSV writing pattern** - Prevent data corruption during concurrent writes
  - Add file locking mechanism (e.g., `portalocker`)
  - Use temp file + rename pattern for SIC updates
  - Test concurrent access scenarios

- [ ] **Add input validation and sanitization** - Prevent injection attacks
  - Validate company_index parameter types/ranges  
  - Add schema validation using `pydantic` for API inputs
  - Sanitize user inputs in all endpoints

### Priority 2 - Core System Stability
- [ ] **Fix concurrency issues with global singletons** - Thread safety for production
  - Add thread locks to `_enhanced_sic_matcher` global instance
  - Protect config manager initialization
  - Test multi-threaded Flask deployment scenarios

- [ ] **Implement proper error taxonomy** - Better error handling
  - Create custom exception classes (`DataLoadError`, `ExternalAPIError`)
  - Replace broad `except Exception` blocks with specific catches
  - Add Flask error handler middleware for unified JSON responses

### Priority 3 - Configuration Management
- [ ] **Externalize configuration and thresholds** - Remove hardcoded values
  - Create `config/settings.py` or `config/thresholds.yaml`
  - Move 90% accuracy threshold to config
  - Externalize magic numbers from agents and workflows
  - Add environment-specific config loading

---

## 🟡 Medium Priority (4-6)

### Priority 4 - API & Service Quality
- [ ] **Add /health endpoint** - Service monitoring and readiness checks
  - Check database connections
  - Verify file dependencies (SIC codes, company data)
  - Report service readiness status
  - Include dependency versions and status

- [ ] **Consolidate Companies House clients** - Resolve dual implementations
  - Migrate agents from `app/utils/companies_house_client.py` to `app/apis/companies_house_client.py`
  - Update method calls (`get_company_filing_history` → `get_filing_history`)
  - Ensure consistent error handling patterns
  - Remove legacy client after migration

### Priority 5 - Code Architecture
- [ ] **Split large monolithic agent files** - Improve maintainability
  - Break down 500-600 line agent files into smaller modules
  - Separate data models, rule engines, and extraction strategies
  - Create service layer (`SICService`, `RevenueService`)
  - Add dependency injection for better testability

- [ ] **Improve data persistence layer** - Move beyond CSV
  - Evaluate SQLite/DuckDB for SIC updates
  - Design transactional update patterns
  - Add data migration utilities
  - Consider caching strategies for frequent lookups

### Priority 6 - Performance & Scalability
- [ ] **Optimize SIC fuzzy matching** - Performance improvements
  - Cache description embeddings for repeat lookups
  - Vectorize row-by-row operations where possible
  - Implement incremental accuracy updates
  - Add performance metrics and monitoring

---

## 🟢 Low Priority (7-10)

### Priority 7 - Testing & Quality Assurance
- [ ] **Add comprehensive test suite** - Automated testing coverage
  - Unit tests for utils (`enhanced_sic_matcher`, data mappers)
  - API tests using Flask test client
  - Agent isolation tests with mocked dependencies
  - Integration tests for full workflow orchestration
  - Golden file regression tests for SIC update schema

### Priority 8 - Observability & Monitoring
- [ ] **Implement structured logging and metrics** - Better debugging
  - Add correlation IDs for multi-agent workflow tracing
  - Implement structured JSON logging option
  - Add metrics: SIC update counts, anomaly rates, extraction success ratios
  - Consider OpenTelemetry spans for agent steps

### Priority 9 - User Experience
- [ ] **Enhance demo mode and documentation** - Better developer experience
  - Add clear demo mode indicators in UI
  - Create API documentation (OpenAPI/Swagger)
  - Add configuration examples and setup guides
  - Improve error messages with actionable guidance

### Priority 10 - Future Enhancements
- [ ] **Advanced features and optimizations** - Long-term improvements
  - Consider GraphQL layer for flexible frontend queries
  - Implement async document/RAG processing queues
  - Add caching for SIC lookups and company data
  - Explore machine learning model improvements
  - Add data export/import utilities

---

## ✅ Recently Completed (Reference)

### Duplicates & Redundancies Cleanup
- [x] **Removed duplicate Flask file** (`flask_copy_2.py`)
- [x] **Cleaned up legacy SIC utilities** (removed unused `sic_matcher.py`)
- [x] **Fixed logging consistency** (replaced all `print()` with proper logging)
- [x] **Isolated simulation code** (created `simulation.py` with `DEMO_MODE` flag)
- [x] **Removed duplicate workflow files** (cleaned up nested workflows directory)

---

## 📋 Implementation Notes

### Quick Wins (Can be completed in 1-2 hours)
- Health endpoint (Priority 4)
- Basic input validation (Priority 1)
- Configuration file creation (Priority 3)

### Medium Effort (1-2 days)
- Atomic CSV writing (Priority 1)
- Thread safety improvements (Priority 2)
- Companies House client consolidation (Priority 4)

### Large Effort (1+ weeks)
- Comprehensive test suite (Priority 7)
- Service layer refactoring (Priority 5)
- Database migration (Priority 5)

### Dependencies
- **Priority 1-2** items should be completed before production deployment
- **Priority 3** items enable better configuration management
- **Priority 4-6** items improve system architecture and performance
- **Priority 7-10** items enhance long-term maintainability

---

## 🎯 Recommended Next Steps

1. **Start with Priority 1** - Address data safety and security concerns
2. **Add basic tests** for critical components as you implement fixes
3. **Create configuration framework** early to support other improvements
4. **Plan service refactoring** in phases to avoid breaking existing functionality
5. **Establish CI/CD pipeline** to automate testing and deployment

---

*Last Updated: September 23, 2025*
*Based on: Code Quality Report (GPT-5 Review) and recent cleanup efforts*