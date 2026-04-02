"""
SQLite database models following modular architecture pattern.
Defines database table structures and data access patterns.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class CompanyStatus(Enum):
    """Company status enumeration."""
    ACTIVE = "Active"
    DISSOLVED = "Dissolved"
    IN_LIQUIDATION = "In Liquidation"
    UNKNOWN = "Unknown"


@dataclass
class Company:
    """
    Company model representing the companies table.
    """
    id: Optional[int] = None
    company_number: Optional[str] = None
    company_name: Optional[str] = None
    status: Optional[str] = None
    incorporation_date: Optional[str] = None
    dissolution_date: Optional[str] = None
    company_type: Optional[str] = None
    jurisdiction: Optional[str] = None
    registered_office_address: Optional[str] = None
    accounts_next_due_date: Optional[str] = None
    accounts_last_made_up_date: Optional[str] = None
    confirmation_statement_next_due_date: Optional[str] = None
    confirmation_statement_last_made_up_date: Optional[str] = None
    # Detailed SIC fields (now in separate company_sic_codes table)
    us_8_digit_sic_code: Optional[str] = None
    us_8_digit_sic_description: Optional[str] = None
    us_sic_1987_code: Optional[str] = None
    us_sic_1987_description: Optional[str] = None
    uk_sic_2007_code: Optional[str] = None
    uk_sic_2007_description: Optional[str] = None
    naics_2022_code: Optional[str] = None
    naics_2022_description: Optional[str] = None
    anzsic_2006_code: Optional[str] = None
    anzsic_2006_description: Optional[str] = None
    can_file: Optional[bool] = None
    has_been_liquidated: Optional[bool] = None
    has_charges: Optional[bool] = None
    has_insolvency_history: Optional[bool] = None
    undeliverable_registered_office_address: Optional[bool] = None
    date_of_creation: Optional[str] = None
    date_of_cessation: Optional[str] = None
    etag: Optional[str] = None
    # Additional fields for CSV import
    business_description: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    sales_gbp: Optional[str] = None
    pre_tax_profit_usd: Optional[str] = None
    assets_usd: Optional[str] = None
    employees_single_site: Optional[str] = None
    employees_total: Optional[str] = None
    ownership_type: Optional[str] = None
    entity_type: Optional[str] = None
    parent_company: Optional[str] = None
    parent_country: Optional[str] = None
    global_ultimate_company: Optional[str] = None
    global_ultimate_country: Optional[str] = None
    website: Optional[str] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    address_line_3: Optional[str] = None
    city: Optional[str] = None
    post_code: Optional[str] = None
    ownership_type: Optional[str] = None
    parent_company: Optional[str] = None
    global_ultimate_company: Optional[str] = None
    duns_number: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert company to dictionary."""
        return {
            'id': self.id,
            'company_number': self.company_number,
            'company_name': self.company_name,
            'status': self.status,
            'incorporation_date': self.incorporation_date,
            'dissolution_date': self.dissolution_date,
            'company_type': self.company_type,
            'jurisdiction': self.jurisdiction,
            'registered_office_address': self.registered_office_address,
            'accounts_next_due_date': self.accounts_next_due_date,
            'accounts_last_made_up_date': self.accounts_last_made_up_date,
            'confirmation_statement_next_due_date': self.confirmation_statement_next_due_date,
            'confirmation_statement_last_made_up_date': self.confirmation_statement_last_made_up_date,
            'can_file': self.can_file,
            'has_been_liquidated': self.has_been_liquidated,
            'has_charges': self.has_charges,
            'has_insolvency_history': self.has_insolvency_history,
            'undeliverable_registered_office_address': self.undeliverable_registered_office_address,
            'date_of_creation': self.date_of_creation,
            'date_of_cessation': self.date_of_cessation,
            'etag': self.etag,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Company':
        """Create company from dictionary."""
        return cls(**data)


@dataclass 
class SICCode:
    """
    SIC Code model representing the sic_codes table.
    """
    id: Optional[int] = None
    sic_code: Optional[str] = None
    sic_description: Optional[str] = None
    section: Optional[str] = None
    division: Optional[str] = None
    group_code: Optional[str] = None
    class_code: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert SIC code to dictionary."""
        return {
            'id': self.id,
            'sic_code': self.sic_code,
            'sic_description': self.sic_description,
            'section': self.section,
            'division': self.division,
            'group_code': self.group_code,
            'class_code': self.class_code,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SICCode':
        """Create SIC code from dictionary."""
        return cls(**data)


@dataclass
class CompanySICCode:
    """
    Company SIC Code junction model representing the company_sic_codes table.
    """
    id: Optional[int] = None
    company_id: Optional[int] = None
    sic_code_id: Optional[int] = None
    is_primary: Optional[bool] = False
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert company SIC code to dictionary."""
        return {
            'id': self.id,
            'company_id': self.company_id,
            'sic_code_id': self.sic_code_id,
            'is_primary': self.is_primary,
            'created_at': self.created_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CompanySICCode':
        """Create company SIC code from dictionary."""
        return cls(**data)


@dataclass
class CompanyFinancial:
    """
    Company Financial model representing the company_financials table.
    """
    id: Optional[int] = None
    company_id: Optional[int] = None
    period_end_date: Optional[str] = None
    period_start_date: Optional[str] = None
    balance_sheet_date: Optional[str] = None
    cash_at_bank_and_in_hand: Optional[float] = None
    creditors_due_within_one_year: Optional[float] = None
    current_assets: Optional[float] = None
    debtors: Optional[float] = None
    net_current_assets_liabilities: Optional[float] = None
    tangible_assets: Optional[float] = None
    total_assets_less_current_liabilities: Optional[float] = None
    net_assets_liabilities: Optional[float] = None
    called_up_share_capital: Optional[float] = None
    profit_loss: Optional[float] = None
    shareholders_funds: Optional[float] = None
    # Additional fields for CSV import
    sales_gbp: Optional[float] = None
    assets_usd: Optional[float] = None
    pre_tax_profit_usd: Optional[float] = None
    employees_total: Optional[int] = None
    employees_single_site: Optional[int] = None
    financial_year: Optional[str] = None
    currency_original: Optional[str] = None
    data_source: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert company financial to dictionary."""
        return {
            'id': self.id,
            'company_id': self.company_id,
            'period_end_date': self.period_end_date,
            'period_start_date': self.period_start_date,
            'balance_sheet_date': self.balance_sheet_date,
            'cash_at_bank_and_in_hand': self.cash_at_bank_and_in_hand,
            'creditors_due_within_one_year': self.creditors_due_within_one_year,
            'current_assets': self.current_assets,
            'debtors': self.debtors,
            'net_current_assets_liabilities': self.net_current_assets_liabilities,
            'tangible_assets': self.tangible_assets,
            'total_assets_less_current_liabilities': self.total_assets_less_current_liabilities,
            'net_assets_liabilities': self.net_assets_liabilities,
            'called_up_share_capital': self.called_up_share_capital,
            'profit_loss': self.profit_loss,
            'shareholders_funds': self.shareholders_funds,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CompanyFinancial':
        """Create company financial from dictionary."""
        return cls(**data)


@dataclass
class APIAuditLog:
    """
    API Audit Log model representing the api_audit_log table.
    """
    id: Optional[int] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    request_params: Optional[str] = None
    response_status: Optional[int] = None
    response_time_ms: Optional[float] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert API audit log to dictionary."""
        return {
            'id': self.id,
            'endpoint': self.endpoint,
            'method': self.method,
            'request_params': self.request_params,
            'response_status': self.response_status,
            'response_time_ms': self.response_time_ms,
            'user_agent': self.user_agent,
            'ip_address': self.ip_address,
            'timestamp': self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'APIAuditLog':
        """Create API audit log from dictionary."""
        return cls(**data)


@dataclass
class SICPredictionHistory:
    """
    SIC Prediction History model representing the sic_prediction_history table.
    """
    id: Optional[int] = None
    company_id: Optional[int] = None
    input_text: Optional[str] = None
    predicted_sic_code: Optional[str] = None
    confidence_score: Optional[float] = None
    model_version: Optional[str] = None
    prediction_timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert SIC prediction history to dictionary."""
        return {
            'id': self.id,
            'company_id': self.company_id,
            'input_text': self.input_text,
            'predicted_sic_code': self.predicted_sic_code,
            'confidence_score': self.confidence_score,
            'model_version': self.model_version,
            'prediction_timestamp': self.prediction_timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SICPredictionHistory':
        """Create SIC prediction history from dictionary."""
        return cls(**data)