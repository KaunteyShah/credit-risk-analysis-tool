"""
Enhanced Dependency Injection Container that integrates your existing architecture
with the modular enhancements for better efficiency and management.

This shows how your sophisticated existing components work with modular architecture.
"""
import os
import logging
from typing import Dict, Any, Optional, Type, TypeVar, Callable

# Your existing sophisticated components  
from app.data_layer.databricks_data import DatabricksDataManager
from app.agents.sector_classification_agent import SectorClassificationAgent
from app.agents.ai_reasoning_agent import AIReasoningAgent
from app.agents.smart_financial_extraction_agent import SmartFinancialExtractionAgent
from app.agents.orchestrator import MultiAgentOrchestrator

# Enhanced modular components that work WITH your existing architecture
from app.repositories.interfaces.company_repository_interface import CompanyRepositoryInterface
from app.repositories.implementations.file_based.file_company_repository import FileCompanyRepository
from app.repositories.implementations.databricks.databricks_company_repository import DatabricksCompanyRepository
from app.services.company_service import CompanyService

logger = logging.getLogger(__name__)
T = TypeVar('T')


class EnhancedDIContainer:
    """
    Enhanced DI Container that coordinates your existing architecture 
    with modular enhancements for better efficiency and management.
    
    Key Benefits:
    - Uses your existing sophisticated Databricks, agents, APIs
    - Adds dependency injection for better component management
    - Configuration-based switching for different environments
    - Clean separation of concerns with repository interfaces
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable[[], Any]] = {}
        self._singletons: Dict[str, Any] = {}
        
        logger.info("Enhanced DI Container initialized")
        self._configure_for_environment()
    
    def _configure_for_environment(self):
        """
        Configure components based on environment - ENHANCES your existing setup
        
        Environments:
        - databricks: Your sophisticated Databricks + Delta tables
        - local_files: File-based development with your existing CSV/Excel logic
        - sqlite: Future SQLite migration (preserves all your agent logic)
        """
        env = os.getenv('DEPLOYMENT_ENV', 'databricks')
        database_type = os.getenv('DATABASE_TYPE', 'databricks')
        
        logger.info(f"Configuring enhanced container for environment: {env}, database: {database_type}")
        
        # Configure data access based on environment
        if database_type == 'databricks':
            logger.info("Configuring with your existing DatabricksDataManager")
            self._configure_databricks_components()
            
        elif database_type == 'files':
            logger.info("Configuring with file-based repositories (preserves your CSV/Excel logic)")
            self._configure_file_components()
            
        elif database_type == 'sqlite':
            logger.info("Future SQLite configuration (preserves all your agents)")
            # Future: SQLite repository implementations
            self._configure_sqlite_components()
            
        # Always configure your existing sophisticated agents
        self._configure_your_existing_agents()
        
        # Configure enhanced services that coordinate everything
        self._configure_enhanced_services()
    
    def _configure_databricks_components(self):
        """Configure with your existing sophisticated Databricks architecture"""
        
        # Your existing DatabricksDataManager (sophisticated!)
        self.register_singleton('databricks_manager', lambda: DatabricksDataManager())
        
        # Enhanced repository that USES your DatabricksDataManager  
        self.register_singleton('company_repository', 
                              lambda: DatabricksCompanyRepository())
        
        logger.info("Configured Databricks components using your existing data manager")
    
    def _configure_file_components(self):
        """Configure file-based components (preserves your CSV/Excel logic)"""
        
        # File repository that preserves your existing file handling logic
        self.register_singleton('company_repository', 
                              lambda: FileCompanyRepository())
        
        logger.info("Configured file-based components preserving your existing logic")
    
    def _configure_sqlite_components(self):
        """Future SQLite configuration (will preserve all your agent logic)"""
        
        # Future: SQLite repository implementations
        # All your existing agents will work unchanged!
        pass
    
    def _configure_your_existing_agents(self):
        """Configure your existing sophisticated AI agents (NO CHANGES)"""
        
        # Your existing sophisticated agents - used AS-IS
        self.register_singleton('sector_agent', 
                              lambda: SectorClassificationAgent())
        
        self.register_singleton('reasoning_agent', 
                              lambda: AIReasoningAgent())
        
        self.register_singleton('financial_agent', 
                              lambda: SmartFinancialExtractionAgent())
        
        self.register_singleton('orchestrator', 
                              lambda: MultiAgentOrchestrator())
        
        logger.info("Configured your existing sophisticated agents")
    
    def _configure_enhanced_services(self):
        """Configure enhanced services that coordinate your existing components"""
        
        # Enhanced service that coordinates your agents with modular repositories
        self.register_singleton('company_service', lambda: CompanyService(
            company_repository=self.get('company_repository')
        ))
        
        # Future: Enhanced service that uses ALL your existing agents
        # self.register_singleton('enhanced_company_service', lambda: EnhancedCompanyService(
        #     company_repository=self.get('company_repository'),
        #     sector_agent=self.get('sector_agent'),
        #     reasoning_agent=self.get('reasoning_agent'),
        #     financial_agent=self.get('financial_agent'),
        #     orchestrator=self.get('orchestrator')
        # ))
        
        logger.info("Configured enhanced services that coordinate your existing components")
    
    def register_singleton(self, name: str, factory: Callable[[], T]) -> None:
        """Register a singleton service (created once, reused)"""
        self._factories[name] = factory
        logger.debug(f"Registered singleton: {name}")
    
    def register_transient(self, name: str, factory: Callable[[], T]) -> None:
        """Register a transient service (created each time)"""
        self._services[name] = factory
        logger.debug(f"Registered transient: {name}")
    
    def get(self, name: str) -> Any:
        """Get service instance with dependency injection"""
        try:
            # Check singletons first
            if name in self._singletons:
                return self._singletons[name]
            
            if name in self._factories:
                instance = self._factories[name]()
                self._singletons[name] = instance
                logger.debug(f"Created singleton instance: {name}")
                return instance
            
            # Check transient services
            if name in self._services:
                instance = self._services[name]()
                logger.debug(f"Created transient instance: {name}")
                return instance
            
            raise KeyError(f"Service not registered: {name}")
            
        except Exception as e:
            logger.error(f"Error creating service '{name}': {e}")
            raise
    
    def get_company_repository(self) -> CompanyRepositoryInterface:
        """Get company repository (file-based, Databricks, or future SQLite)"""
        return self.get('company_repository')
    
    def get_company_service(self) -> CompanyService:
        """Get enhanced company service that coordinates your components"""
        return self.get('company_service')
    
    def get_databricks_manager(self) -> Optional[DatabricksDataManager]:
        """Get your existing sophisticated DatabricksDataManager"""
        try:
            return self.get('databricks_manager')
        except KeyError:
            return None  # Not configured for Databricks environment
    
    def get_sector_agent(self) -> SectorClassificationAgent:
        """Get your existing sophisticated SectorClassificationAgent"""
        return self.get('sector_agent')
    
    def get_reasoning_agent(self) -> AIReasoningAgent:
        """Get your existing sophisticated AIReasoningAgent"""
        return self.get('reasoning_agent')
    
    def get_financial_agent(self) -> SmartFinancialExtractionAgent:
        """Get your existing sophisticated SmartFinancialExtractionAgent"""
        return self.get('financial_agent')
    
    def get_orchestrator(self) -> MultiAgentOrchestrator:
        """Get your existing sophisticated MultiAgentOrchestrator"""
        return self.get('orchestrator')
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for all configured components"""
        try:
            health = {
                'container_status': 'healthy',
                'environment': os.getenv('DEPLOYMENT_ENV', 'databricks'),
                'database_type': os.getenv('DATABASE_TYPE', 'databricks'),
                'configured_services': list(self._factories.keys()) + list(self._services.keys()),
                'singleton_instances': list(self._singletons.keys())
            }
            
            # Test key components
            try:
                company_repo = self.get_company_repository()
                health['company_repository'] = 'available'
                health['repository_type'] = type(company_repo).__name__
            except Exception as e:
                health['company_repository'] = f'error: {e}'
            
            try:
                sector_agent = self.get_sector_agent()
                health['sector_agent'] = 'available'
                health['sector_agent_type'] = type(sector_agent).__name__
            except Exception as e:
                health['sector_agent'] = f'error: {e}'
            
            try:
                company_service = self.get_company_service()
                health['company_service'] = 'available'
                health['service_type'] = type(company_service).__name__
            except Exception as e:
                health['company_service'] = f'error: {e}'
                
            return health
            
        except Exception as e:
            logger.error(f"Container health check failed: {e}")
            return {
                'container_status': 'unhealthy',
                'error': str(e)
            }


# Global enhanced container instance
_enhanced_container: Optional[EnhancedDIContainer] = None


def get_enhanced_container() -> EnhancedDIContainer:
    """Get global enhanced DI container instance"""
    global _enhanced_container
    if _enhanced_container is None:
        _enhanced_container = EnhancedDIContainer()
    return _enhanced_container


def get_company_repository() -> CompanyRepositoryInterface:
    """Convenience: Get company repository from enhanced container"""
    return get_enhanced_container().get_company_repository()


def get_company_service() -> CompanyService:
    """Convenience: Get enhanced company service from container"""
    return get_enhanced_container().get_company_service()


def get_databricks_manager() -> Optional[DatabricksDataManager]:
    """Convenience: Get your existing DatabricksDataManager"""
    return get_enhanced_container().get_databricks_manager()


def get_sector_agent() -> SectorClassificationAgent:
    """Convenience: Get your existing SectorClassificationAgent"""
    return get_enhanced_container().get_sector_agent()


def get_reasoning_agent() -> AIReasoningAgent:
    """Convenience: Get your existing AIReasoningAgent"""
    return get_enhanced_container().get_reasoning_agent()


def get_financial_agent() -> SmartFinancialExtractionAgent:
    """Convenience: Get your existing SmartFinancialExtractionAgent"""
    return get_enhanced_container().get_financial_agent()


def get_orchestrator() -> MultiAgentOrchestrator:
    """Convenience: Get your existing MultiAgentOrchestrator"""
    return get_enhanced_container().get_orchestrator()


# Configuration helpers for better management
def configure_for_databricks():
    """Configure container for Databricks environment (uses your existing components)"""
    os.environ['DATABASE_TYPE'] = 'databricks'
    global _enhanced_container
    _enhanced_container = None  # Reset to reconfigure
    logger.info("Configured for Databricks (using your existing sophisticated data layer)")


def configure_for_local_files():
    """Configure container for local file development (preserves your CSV/Excel logic)"""
    os.environ['DATABASE_TYPE'] = 'files'
    global _enhanced_container
    _enhanced_container = None  # Reset to reconfigure
    logger.info("Configured for local files (preserving your existing file logic)")


def configure_for_sqlite():
    """Configure container for future SQLite migration (preserves all your agents)"""
    os.environ['DATABASE_TYPE'] = 'sqlite'
    global _enhanced_container
    _enhanced_container = None  # Reset to reconfigure
    logger.info("Configured for SQLite (future - preserves all your sophisticated agents)")