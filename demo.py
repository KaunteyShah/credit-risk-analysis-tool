"""
Demonstration script for the Credit Risk Multi-Agent Anomaly Detection System.
"""
import os
import sys
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def main():
    """Run the demonstration."""
    print("🚀 Credit Risk Multi-Agent Anomaly Detection System")
    print("=" * 60)
    print(f"Demo started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Sample data for demonstration
    sample_data = {
        "company_numbers": ["12345678", "87654321", "11111111", "22222222", "33333333"],
        "include_filing_history": False
    }
    
    print("📊 Sample Input Data:")
    print(f"   • Company numbers to analyze: {len(sample_data['company_numbers'])}")
    print(f"   • Include filing history: {sample_data['include_filing_history']}")
    print()
    
    try:
        # Import and initialize orchestrator
        from agents.orchestrator import MultiAgentOrchestrator
        
        orchestrator = MultiAgentOrchestrator()
        print(f"✅ Multi-Agent Orchestrator initialized (Session: {orchestrator.session_id})")
        print()
        
        # Run complete workflow
        print("🔄 Running complete multi-agent workflow...")
        results = orchestrator.run_complete_workflow(sample_data)
        
        # Display results
        display_results(results)
        
    except ImportError as e:
        print(f"⚠️  Could not import agents (expected in demo environment): {e}")
        print("📝 Running mock demonstration instead...")
        mock_demonstration()
    
    except Exception as e:
        print(f"❌ Error running workflow: {e}")
        print("📝 Running mock demonstration instead...")
        mock_demonstration()

def display_results(results):
    """Display workflow results."""
    print("📈 Workflow Results:")
    print("-" * 40)
    
    workflow_info = results.get("workflow_info", {})
    data_summary = results.get("data_summary", {})
    suggestions = results.get("suggestions", {})
    
    print(f"Status: {workflow_info.get('status', 'unknown')}")
    print(f"Duration: {workflow_info.get('duration_seconds', 0):.2f} seconds")
    print(f"Companies processed: {data_summary.get('companies_processed', 0)}")
    print(f"Anomalies detected: {data_summary.get('anomalies_detected', 0)}")
    print(f"Suggestions generated: {data_summary.get('suggestions_generated', 0)}")
    print(f"Data quality score: {data_summary.get('data_quality_score', 0):.1f}%")
    print()
    
    if suggestions.get('total_count', 0) > 0:
        print("💡 AI Suggestions Summary:")
        print(f"   • Sector classifications: {len(suggestions.get('sector_classifications', []))}")
        print(f"   • Turnover estimations: {len(suggestions.get('turnover_estimations', []))}")
        print(f"   • High confidence: {suggestions.get('high_confidence', 0)}")
        print(f"   • Medium confidence: {suggestions.get('medium_confidence', 0)}")
        print(f"   • Low confidence: {suggestions.get('low_confidence', 0)}")
        print()
    
    next_steps = results.get("next_steps", [])
    if next_steps:
        print("🎯 Recommended Next Steps:")
        for i, step in enumerate(next_steps[:5], 1):
            print(f"   {i}. {step}")
        print()

def mock_demonstration():
    """Run a mock demonstration with sample data."""
    print("🎭 Mock Demonstration")
    print("-" * 30)
    
    # Mock companies data
    companies = [
        {"name": "Tech Innovations Ltd", "sic": "62012", "turnover": 850000, "status": "✅ Normal"},
        {"name": "Green Energy Solutions", "sic": "47190", "turnover": -50000, "status": "🚨 Anomalies"},
        {"name": "Financial Advisory Group", "sic": None, "turnover": None, "status": "🚨 Missing Data"},
        {"name": "Mega Corp Industries", "sic": "46190", "turnover": 2500000000, "status": "⚠️  High Value"},
        {"name": "Dormant Holdings Ltd", "sic": "64209", "turnover": 0, "status": "🚨 Zero Turnover"}
    ]
    
    print("📊 Sample Companies Analysis:")
    for company in companies:
        print(f"   • {company['name']}: {company['status']}")
    print()
    
    # Mock anomalies
    anomalies = [
        {"type": "Sector Code Mismatch", "count": 1, "example": "Energy company with retail SIC code"},
        {"type": "Negative Turnover", "count": 1, "example": "Company showing negative revenue"},
        {"type": "Missing SIC Code", "count": 1, "example": "Financial advisory with no classification"},
        {"type": "Missing Turnover", "count": 1, "example": "No financial data available"},
        {"type": "Zero Turnover", "count": 1, "example": "Active company with zero revenue"}
    ]
    
    print("🔍 Detected Anomalies:")
    for anomaly in anomalies:
        print(f"   • {anomaly['type']}: {anomaly['count']} case(s)")
        print(f"     Example: {anomaly['example']}")
    print()
    
    # Mock suggestions
    suggestions = [
        {"company": "Green Energy Solutions", "type": "SIC Code", "suggestion": "71200 (Technical testing)", "confidence": "85%"},
        {"company": "Green Energy Solutions", "type": "Turnover", "suggestion": "£450,000 (Industry estimate)", "confidence": "60%"},
        {"company": "Financial Advisory Group", "type": "SIC Code", "suggestion": "66220 (Insurance agents)", "confidence": "90%"},
        {"company": "Financial Advisory Group", "type": "Turnover", "suggestion": "£320,000 (Sector average)", "confidence": "70%"}
    ]
    
    print("💡 AI-Generated Suggestions:")
    for suggestion in suggestions:
        print(f"   • {suggestion['company']}")
        print(f"     {suggestion['type']}: {suggestion['suggestion']} ({suggestion['confidence']} confidence)")
    print()
    
    print("📈 Summary Statistics:")
    print(f"   • Total companies: {len(companies)}")
    print(f"   • Anomalies detected: {sum(a['count'] for a in anomalies)}")
    print(f"   • Anomaly rate: {(sum(a['count'] for a in anomalies)) / len(companies) * 100:.1f}%")
    print(f"   • Suggestions generated: {len(suggestions)}")
    print(f"   • High confidence suggestions: {len([s for s in suggestions if int(s['confidence'].rstrip('%')) >= 80])}")
    print()
    
    print("🎯 Next Steps:")
    print("   1. Review AI suggestions in analyst interface")
    print("   2. Accept or reject based on domain expertise")
    print("   3. Implement approved corrections")
    print("   4. Set up automated monitoring")
    print("   5. Schedule regular quality checks")

if __name__ == "__main__":
    main()
    print()
    print("=" * 60)
    print("✅ Demonstration completed!")
    print("🚀 Ready to deploy to Databricks for full functionality!")
