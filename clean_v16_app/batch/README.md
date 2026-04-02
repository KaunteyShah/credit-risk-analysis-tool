# Batch Processing Tools

This directory contains batch processing utilities for the credit risk analysis application.

## Files

### auto_sic_confidence_calculator.py

**Purpose**: Automatically calculates existing SIC confidence scores for companies based on business descriptions and SIC code descriptions.

**Source**: Recovered from git history (was accidentally deleted from the main codebase)

**Location**: 
- `/batch/auto_sic_confidence_calculator.py` (backup copy)
- `/auto_sic_confidence_calculator.py` (working copy used by SICConfidenceService)

**Features**:
- Fuzzy matching using fuzzywuzzy library for text similarity analysis
- Keyword-based sector analysis when fuzzy matching isn't available
- Confidence categorization (Excellent, Good, Fair, Very Poor)
- Database integration with sic_prediction_history table
- Batch processing capabilities for multiple companies

**Key Methods**:
- `calculate_confidence_score_with_reasoning()` - Core confidence calculation with detailed reasoning
- `get_companies_needing_confidence()` - Find companies that need confidence calculation
- `create_sic_prediction_record()` - Save confidence data to database
- `run_auto_calculation()` - Batch process all companies needing calculation

**Dependencies**:
- fuzzywuzzy (optional, falls back to keyword analysis if unavailable)
- sqlite3
- Standard Python libraries

**Usage**:
```python
from auto_sic_confidence_calculator import AutoSICConfidenceCalculator

# Initialize calculator
calculator = AutoSICConfidenceCalculator()

# Calculate confidence for a single company
confidence, reasoning = calculator.calculate_confidence_score_with_reasoning(
    business_description="Retail supermarket services",
    sic_code="47110",
    sic_description="Retail sale in non-specialised stores"
)

# Run batch calculation for all companies
calculator.run_auto_calculation()
```

**Integration**:
This file is imported by `app_modules/services/sic_confidence_service.py` to provide confidence calculation capabilities for the agentic SIC prediction workflow.

**Status**: ✅ Fully restored and functional (Nov 5, 2025)

## Recovery Notes

The `auto_sic_confidence_calculator.py` file was missing from the codebase but was successfully recovered from git history using:
```bash
git log -p --all | grep -A 300 "class AutoSICConfidenceCalculator"
```

The file has been restored to both:
1. `/batch/` directory for backup and future reference
2. Root directory for immediate use by the SICConfidenceService

## Testing

The restored file has been tested and confirmed working:
- ✅ Import successful
- ✅ Calculator instantiation works
- ✅ Confidence calculation functional
- ✅ Integration with SICConfidenceService operational
- ✅ Database operations working (returns existing_sic_confidence values)

## Future Maintenance

Keep this backup copy in the `/batch/` directory to prevent future loss of this critical component.