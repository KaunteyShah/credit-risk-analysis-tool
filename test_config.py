#!/usr/bin/env python3
"""
Startup Configuration Test
Tests all API connections and displays configuration status
"""

import os
import sys
from pathlib import Path

# Add app directory to path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

def main():
    print("🚀 Credit Risk Analysis - Configuration Test")
    print("=" * 60)
    
    try:
        from app.apis.unified_api_service import get_unified_api_service
        from app.utils.config_manager import ConfigManager
        
        # Initialize services
        print("📋 Initializing services...")
        api_service = get_unified_api_service()
        config_manager = ConfigManager()
        
        # Check configuration validity
        print("\n🔧 Configuration Status:")
        validations = config_manager.validate_api_keys()
        
        for service, is_valid in validations.items():
            status = "✅ CONFIGURED" if is_valid else "❌ NOT CONFIGURED"
            print(f"  {service.upper():<15}: {status}")
        
        # Check service status
        print("\n🌐 Service Connectivity:")
        service_status = api_service.get_service_status()
        
        for service_name, status in service_status.items():
            if status.available and status.configured:
                print(f"  {service_name.upper():<15}: ✅ READY")
            elif status.available and not status.configured:
                print(f"  {service_name.upper():<15}: ⚠️  AVAILABLE BUT NOT CONFIGURED")
            else:
                print(f"  {service_name.upper():<15}: ❌ ERROR - {status.error_message}")
        
        # Overall status
        print("\n📊 Overall Status:")
        if api_service.is_production_ready():
            print("✅ ALL SYSTEMS READY FOR PRODUCTION")
        else:
            missing = api_service.get_missing_services()
            print(f"⚠️  MISSING CONFIGURATIONS: {', '.join(missing)}")
            print("\n💡 To fix this:")
            for service in missing:
                if service == "databricks":
                    print(f"   • Set DATABRICKS_HOST and DATABRICKS_TOKEN in .env")
                elif service == "openai":
                    print(f"   • Set OPENAI_API_KEY in .env")
                elif service == "companies_house":
                    print(f"   • Set COMPANIES_HOUSE_API_KEY in .env")
        
        # Test basic operations if all configured
        if api_service.is_production_ready():
            print("\n🧪 Running Basic Tests...")
            
            # Test Databricks
            try:
                data = api_service.get_databricks_data(limit=5)
                print(f"  • Databricks: ✅ Connected (found {len(data)} records)")
            except Exception as e:
                print(f"  • Databricks: ❌ Error - {e}")
            
            # Test OpenAI
            try:
                response = api_service.generate_ai_response("Hello, can you respond with 'API Working'?")
                if response:
                    print(f"  • OpenAI: ✅ Connected")
                else:
                    print(f"  • OpenAI: ❌ No response")
            except Exception as e:
                print(f"  • OpenAI: ❌ Error - {e}")
            
            # Test Companies House (if configured)
            try:
                result = api_service.search_companies("Microsoft", 1)
                if result:
                    print(f"  • Companies House: ✅ Connected")
                else:
                    print(f"  • Companies House: ❌ No results")
            except Exception as e:
                print(f"  • Companies House: ❌ Error - {e}")
        
        print("\n" + "=" * 60)
        print("🎯 Configuration test complete!")
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
