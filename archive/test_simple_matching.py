#!/usr/bin/env python3
"""
Simple effective SIC matching test
"""
import pandas as pd
from rapidfuzz import fuzz, process
import re

def extract_business_activity(description):
    """
    Extract the core business activity from complex descriptions
    """
    description = description.lower()
    
    # Remove corporate structure words
    noise_words = [
        'plc', 'ltd', 'limited', 'group', 'holdings', 'company', 'corporation', 
        'corp', 'inc', 'the', 'and', 'through', 'its', 'subsidiaries', 'engaged',
        'in', 'business', 'of', 'activities', 'services', 'operations'
    ]
    
    # Remove noise words
    for word in noise_words:
        description = re.sub(r'\b' + word + r'\b', ' ', description)
    
    # Extract key activity phrases
    activity_patterns = [
        r'(food service|catering|restaurant|dining)',
        r'(retail|supermarket|grocery|store|shop)',
        r'(bank|banking|financial|lending|deposit)',
        r'(software|technology|computing)',
        r'(manufacturing|production|factory)'
    ]
    
    key_activities = []
    for pattern in activity_patterns:
        matches = re.findall(pattern, description)
        key_activities.extend(matches)
    
    # If no specific patterns, take first few meaningful words
    if not key_activities:
        words = [w for w in description.split() if len(w) > 3][:3]
        key_activities = words
    
    return ' '.join(key_activities)

def test_business_extraction():
    """Test business activity extraction"""
    
    test_cases = [
        "Compass Group PLC food catering and support services",
        "Tesco PLC retail supermarket grocery stores",
        "HSBC Holdings PLC banking financial services",
        "Simple catering",
        "Restaurant business",
        "Food retail store"
    ]
    
    print("=== BUSINESS ACTIVITY EXTRACTION TEST ===")
    for desc in test_cases:
        extracted = extract_business_activity(desc)
        print(f"Original: {desc}")
        print(f"Extracted: {extracted}")
        print()

def test_matching_with_extraction():
    """Test SIC matching with business activity extraction"""
    
    # Load SIC codes
    sic_df = pd.read_excel('/Users/kaunteyshah/Databricks/Credit_Risk/data/SIC_codes.xlsx')
    
    # Fix column names - first column is SIC code, second is description
    sic_df.columns = ['SIC_Code', 'Description']
    
    # Create description mapping
    description_to_code = {}
    for _, row in sic_df.iterrows():
        description_to_code[row['Description']] = row['SIC_Code']
    
    test_cases = [
        "Compass Group PLC food catering and support services",
        "Tesco PLC retail supermarket grocery stores", 
        "HSBC Holdings PLC banking financial services"
    ]
    
    print("=== SMART MATCHING TEST ===")
    
    for business_desc in test_cases:
        print(f"\nTesting: {business_desc}")
        
        # Extract key business activity
        key_activity = extract_business_activity(business_desc)
        print(f"Key activity: {key_activity}")
        
        # Match against SIC descriptions using extracted activity
        sic_descriptions = list(description_to_code.keys())
        matches = process.extract(key_activity, sic_descriptions, scorer=fuzz.WRatio, limit=3)
        
        print("Top matches:")
        for desc, score, idx in matches:
            sic_code = description_to_code[desc]
            print(f"  {score:3.0f}% - {sic_code} - {desc}")

if __name__ == "__main__":
    test_business_extraction()
    test_matching_with_extraction()