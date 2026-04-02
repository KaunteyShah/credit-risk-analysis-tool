#!/usr/bin/env python3
"""Quick local test: AVIVA end-to-end revenue extraction with transaction_id."""
import logging
logging.basicConfig(level=logging.WARNING)

from app_modules.services.update_revenue_service import UpdateRevenueService

svc = UpdateRevenueService()
print("✅ Service initialized, running AVIVA extraction...")

result = svc.update_revenue_agentic(
    company_name="AVIVA PLC",
    company_number="02468686",
    transaction_id="MzQ2NTc0OTUyMWFkaXF6a2N4"
)

print(f"success           = {result.get('success')}")
print(f"extracted_revenue = {result.get('extracted_revenue')}")
print(f"revenue_currency  = {result.get('revenue_currency')}")
print(f"confidence_score  = {result.get('confidence_score')}")
print(f"extraction_method = {result.get('extraction_method')}")
if result.get("errors"):
    print(f"errors = {result['errors']}")
if result.get("error"):
    print(f"error  = {result['error']}")
