"""
Sample_data2.csv Data Mapping Utility
Maps columns from Sample_data2.csv to standardized database schema
"""

import pandas as pd
from typing import Dict, List
from .logger import logger

class Sample2DataMapper:
    """
    Maps Sample_data2.csv columns to standardized format for Databricks integration
    """
    
    # Column mapping from CSV headers to database column names
    COLUMN_MAPPING = {
        'Company Name': 'company_name',
        'Registration number': 'registration_number',
        'D-U-N-S® Number': 'duns_number',
        'Address Line 1': 'address_line_1',
        'Address Line 2': 'address_line_2',
        'Address Line 3': 'address_line_3',
        'City': 'city',
        'Post Code': 'post_code',
        'Country': 'country',
        'Phone': 'phone',
        'Company Email': 'company_email',
        'Website': 'website',
        'Sales (USD)': 'sales_usd',
        'Pre Tax Profit (USD)': 'pre_tax_profit_usd',
        'Assets (USD)': 'assets_usd',
        'Employees (Single Site)': 'employees_single_site',
        'Employees (Total)': 'employees_total',
        'Business Description': 'business_description',
        'Ownership Type': 'ownership_type',
        'Entity Type': 'entity_type',
        'Parent Company': 'parent_company',
        'Parent Country/Region': 'parent_country_region',
        'Global Ultimate Company': 'global_ultimate_company',
        'Global Ultimate Country/Region': 'global_ultimate_country_region',
        'US 8-Digit SIC Code': 'us_8_digit_sic_code',
        'US 8-Digit SIC Description': 'us_8_digit_sic_description',
        'US SIC 1987 Code': 'us_sic_1987_code',
        'US SIC 1987 Description': 'us_sic_1987_description',
        'NAICS 2022 Code': 'naics_2022_code',
        'NAICS 2022 Description': 'naics_2022_description',
        'UK SIC 2007 Code': 'uk_sic_2007_code',
        'UK SIC 2007 Description': 'uk_sic_2007_description',
        'ANZSIC 2006 Code': 'anzsic_2006_code',
        'ANZSIC 2006 Description': 'anzsic_2006_description'
    }
    
    @classmethod
    def map_dataframe(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Map DataFrame columns from Sample_data2.csv format to standardized format
        """
        # Create a copy to avoid modifying original
        mapped_df = df.copy()
        
        # Rename columns according to mapping
        mapped_df = mapped_df.rename(columns=cls.COLUMN_MAPPING)
        
        # Add prediction columns
        mapped_df['predicted_sic'] = None
        mapped_df['prediction_confidence'] = None
        mapped_df['created_at'] = pd.Timestamp.now().date()
        mapped_df['updated_at'] = pd.Timestamp.now().date()
        
        return mapped_df
    
    @classmethod
    def get_key_columns_for_streamlit(cls) -> List[str]:
        """
        Get key columns to display in Streamlit interface
        """
        return [
            'company_name',
            'registration_number',
            'city',
            'country',
            'business_description',
            'uk_sic_2007_code',
            'uk_sic_2007_description',
            'predicted_sic',
            'prediction_confidence'
        ]
    
    @classmethod
    def get_identifier_column(cls) -> str:
        """
        Get the unique identifier column for companies
        """
        return 'registration_number'
    
    @classmethod
    def get_sic_columns(cls) -> Dict[str, str]:
        """
        Get available SIC code columns
        """
        return {
            'UK SIC 2007': 'uk_sic_2007_code',
            'US SIC 1987': 'us_sic_1987_code',
            'US 8-Digit SIC': 'us_8_digit_sic_code',
            'NAICS 2022': 'naics_2022_code',
            'ANZSIC 2006': 'anzsic_2006_code'
        }
    
    @classmethod
    def get_description_for_sic_column(cls, sic_column: str) -> str:
        """
        Get the description column for a given SIC code column
        """
        description_mapping = {
            'uk_sic_2007_code': 'uk_sic_2007_description',
            'us_sic_1987_code': 'us_sic_1987_description',
            'us_8_digit_sic_code': 'us_8_digit_sic_description',
            'naics_2022_code': 'naics_2022_description',
            'anzsic_2006_code': 'anzsic_2006_description'
        }
        return description_mapping.get(sic_column, '')

def load_and_map_sample_data(csv_path: str = "data/Sample_data2.csv") -> pd.DataFrame:
    """
    Load Sample_data2.csv and map it to standardized format
    """
    try:
        # Load the CSV
        df = pd.read_csv(csv_path)
        
        # Map columns
        mapped_df = Sample2DataMapper.map_dataframe(df)
        
        logger.info(f"Successfully loaded and mapped {len(mapped_df)} rows from {csv_path}")
        logger.debug(f"Mapped columns: {list(mapped_df.columns)}")
        
        return mapped_df
        
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

if __name__ == "__main__":
    # Test the mapping
    df = load_and_map_sample_data()
    if not df.empty:
        logger.info("Sample of mapped data:")
        logger.info(df[Sample2DataMapper.get_key_columns_for_streamlit()].head(3).to_string())
        
        logger.info("Available SIC columns:")
        for name, column in Sample2DataMapper.get_sic_columns().items():
            logger.info(f"  - {name}: {column}")
