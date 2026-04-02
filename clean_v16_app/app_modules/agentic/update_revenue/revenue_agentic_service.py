"""
Revenue Agentic Service

Main orchestration service for intelligent agentic revenue extraction workflow.
Coordinates LangGraph workflow execution, manages dependencies, and provides 
clean API interface for integration with existing update_revenue functionality.

Core Responsibilities:
- Orchestrate complete revenue extraction workflow using LangGraph
- Manage service dependencies and dependency injection  
- Handle workflow configuration and customization
- Provide clean API for revenue extraction
- Integrate with existing update_revenue infrastructure
- Monitor workflow performance and results

Integration Strategy:
- Zero-impact deployment alongside existing update_revenue endpoint
- Leverages existing Companies House, document, and extraction agents
- Maintains backward compatibility with current update_revenue API
- Provides enhanced agentic capabilities while preserving functionality
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import json
import numpy as np

from .revenue_workflow_state import RevenueWorkflowState
from .nodes.company_data_ingestion_node import CompanyDataIngestionNode
from .nodes.financial_extraction_node import FinancialExtractionNode  
from .nodes.turnover_estimation_node import TurnoverEstimationNode

from ...utils.logger import get_logger

logger = get_logger(__name__)

def sanitize_for_json(obj):
    """Convert numpy types to native Python types for JSON serialization."""
    try:
        # Try direct JSON encoding first
        json.dumps(obj)
        return obj
    except TypeError:
        pass
    
    if hasattr(obj, 'dtype'):  # numpy array or scalar
        if obj.dtype == bool or 'bool' in str(obj.dtype):
            return bool(obj)
        elif obj.dtype.kind in ['i', 'u']:  # integer types
            return int(obj)
        elif obj.dtype.kind in ['f', 'c']:  # float and complex types
            return float(obj)
        else:
            return str(obj)
    elif str(type(obj)).startswith("<class 'numpy"):  # any numpy type
        return obj.item() if hasattr(obj, 'item') else str(obj)
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [sanitize_for_json(item) for item in obj]
    else:
        return obj

# Enable LangGraph for enhanced workflow orchestration
try:
    import langgraph
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

class AgenticRevenueService:
    """
    Main orchestration service for intelligent agentic revenue extraction.
    
    Provides high-level interface for running complete revenue extraction workflow
    while managing node coordination, state management, and error handling.
    
    Workflow Steps:
    1. Company Data Ingestion (dual lookup methodology)
    2. Document Processing (PDF download and vectorization) 
    3. Revenue Extraction (multi-strategy approach)
    4. Market Validation (optional business logic validation)
    5. Result Compilation (structured output for API)
    """
    
    def __init__(self, services_container: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Initialize the agentic revenue extraction service.
        
        Args:
            services_container: Container with all required service dependencies
                Required services:
                - companies_house_client: CompaniesHouseClient
                - document_download_agent: DocumentDownloadAgent
                - rag_document_agent: RAGDocumentAgent
                - smart_financial_extraction_agent: SmartFinancialExtractionAgent
                - turnover_estimation_agent: TurnoverEstimationAgent
                - filing_history_repository: FilingHistoryRepositoryInterface
                
                Optional services:
                - vector_store: For document vectorization storage
                - ai_reasoning_service: For enhanced validation
                
            config: Optional workflow configuration and customization options
        """
        self.services_container = services_container
        self.config = config or {}
        self.logger = logger.getChild(self.__class__.__name__)
        
        # Get filing history repository for database updates
        self.filing_history_repository = services_container.get('filing_history_repository')
        self.logger.info(f"📊 Filing history repository initialized: {self.filing_history_repository is not None}")
        
        # Initialize workflow nodes
        self.company_ingestion_node = CompanyDataIngestionNode(
            companies_house_client=services_container.get('companies_house_client'),
            filing_service=services_container.get('filing_repository')
        )
        
        self.financial_extraction_node = FinancialExtractionNode(
            document_agent=services_container.get('document_download_agent'),
            document_processor=None  # Let it use default AgenticDocumentProcessor
        )
        
        self.turnover_estimation_node = TurnoverEstimationNode(
            smart_extraction_agent=services_container.get('smart_financial_extraction_agent'),
            turnover_agent=services_container.get('turnover_estimation_agent')
        )
        
        # Workflow compilation
        self.compiled_workflow = None
        
        # Performance tracking
        self.execution_stats = {
            'total_extractions': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'average_execution_time': 0.0,
            'last_execution_time': None,
            'method_usage': {
                'rag_vector': 0,
                'smart_agent': 0, 
                'regex': 0,
                'manual': 0
            }
        }
        
        # Check LangGraph availability
        if not LANGGRAPH_AVAILABLE:
            self.logger.warning("⚠️ LangGraph not available - using sequential node execution")
        
        self.logger.info("💰 AgenticRevenueService initialized")
    
    def extract_revenue_agentic(
        self,
        company_name: str = "",
        company_number: str = "",
        address: str = "",
        transaction_id: str = "",  # ✅ NEW: Accept transaction_id for direct document processing
        workflow_config: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Execute intelligent agentic revenue extraction for a company.
        
        Main entry point for agentic revenue extraction, providing enhanced
        capabilities while maintaining compatibility with existing update_revenue API.
        
        Args:
            company_name: Name of the company for revenue extraction
            company_number: Optional Companies House number for direct lookup
            address: Optional company address for improved matching
            workflow_config: Optional configuration overrides for this extraction
            
        Returns:
            Comprehensive revenue extraction result:
            {
                'extracted_revenue': float,
                'revenue_currency': str,
                'confidence_score': float,
                'extraction_method': str,
                'alternative_revenues': List[Dict],
                'workflow_summary': Dict,
                'companies_house_data': Dict,
                'document_processing_summary': Dict,
                'agentic_insights': Dict,
                'execution_time': float,
                'workflow_steps': List[Dict],
                'validation_results': Dict
            }
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"💰 Starting agentic revenue extraction for: {company_name or f'transaction_id:{transaction_id}'}")
            
            # Update execution stats
            self.execution_stats['total_extractions'] += 1
            
            # Merge configuration
            effective_config = {**self.config, **(workflow_config or {})}
            
            # Progress tracking callback
            if progress_callback:
                progress_callback({
                    'stage': 'initialization',
                    'progress': 0,
                    'message': f'🚀 Starting agentic revenue extraction for {company_name or f"transaction_id:{transaction_id}"}',
                    'timestamp': datetime.now().isoformat()
                })
            
            # Check if LangGraph workflow is available
            if LANGGRAPH_AVAILABLE:
                result = self._execute_langgraph_workflow(
                    company_name, company_number, address, transaction_id, effective_config, start_time, progress_callback
                )
            else:
                result = self._execute_sequential_workflow(
                    company_name, company_number, address, transaction_id, effective_config, start_time, progress_callback
                )
            
            # Update execution statistics
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_execution_stats(result, execution_time)
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Revenue extraction failed for {company_name}: {str(e)}")
            
            # Update failure stats
            self.execution_stats['failed_extractions'] += 1
            
            # Return structured error response
            return self._create_error_response(company_name, str(e), start_time)
    
    def _execute_langgraph_workflow(
        self,
        company_name: str,
        company_number: str,
        address: str,
        transaction_id: Optional[str],
        config: Dict[str, Any],
        start_time: datetime,
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Execute revenue extraction using LangGraph workflow orchestration.
        """
        self.logger.info("🔄 Executing LangGraph revenue extraction workflow")
        
        # Compile workflow if needed
        if not hasattr(self, 'compiled_workflow') or not self.compiled_workflow:
            self.compiled_workflow = self._build_langgraph_workflow()
        
        # Check if compilation was successful
        if not self.compiled_workflow:
            self.logger.warning("🔄 LangGraph workflow compilation failed - falling back to sequential")
            return self._execute_sequential_workflow(
                company_name, company_number, address, transaction_id, config, start_time
            )
        
        # Prepare initial state matching our TypedDict schema
        initial_state = {
            'company_id': '',  # Will be populated during execution
            'unique_id': transaction_id or '',
            'company_name': company_name,
            'company_number': company_number or '',
            
            # Workflow data stores
            'company_filing_data': {},
            'document_processing_data': {},
            'revenue_extraction_data': {},
            
            # Workflow metadata  
            'current_stage': 'company_data_ingestion',
            'node_execution_times': {},
            'workflow_decisions': [],
            'fallback_triggers': [],
            'errors': [],
            
            # Processing flags
            'document_download_success': False,
            'vectorization_success': False,
            'extraction_complete': False
        }
        
        # Execute workflow
        try:
            self.logger.info("🚀 Starting LangGraph workflow execution")
            # Write an initial progress entry immediately so the frontend poller
            # has something to show before the first node wrapper fires.
            progress_key = company_number or company_name or 'unknown'
            self.write_progress(progress_key, 'company_data_ingestion', 1,
                                'Contacting Companies House...', 8)
            final_state = self.compiled_workflow.invoke(initial_state)
            self.logger.info("✅ LangGraph workflow execution completed successfully")
            return self._format_workflow_result(final_state, start_time)
            
        except Exception as e:
            self.logger.error(f"❌ LangGraph workflow execution failed: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Fallback to sequential execution
            self.logger.warning("🔄 Falling back to sequential workflow execution")
            return self._execute_sequential_workflow(
                company_name, company_number, address, transaction_id, config, start_time
            )
    
    def _execute_sequential_workflow(
        self,
        company_name: str,
        company_number: str,
        address: str,
        transaction_id: Optional[str],  # ✅ NEW: Accept transaction_id parameter
        config: Dict[str, Any],
        start_time: datetime,
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Execute revenue extraction using sequential node execution.
        
        Fallback method when LangGraph is not available.
        """
        self.logger.info("⏩ Executing sequential revenue extraction workflow")

        # Write an initial progress entry so the frontend poller sees activity immediately
        progress_key = company_number or company_name or 'unknown'
        self.write_progress(progress_key, 'company_data_ingestion', 1,
                            'Contacting Companies House...', 8)

        # Initialize workflow state
        state = {
            'company_name': company_name,
            'company_number': company_number or '',
            'company_address': address or '',
            'transaction_id': transaction_id or '',  # ✅ NEW: Include transaction_id in workflow state
            'workflow_config': config,
            'current_node': 'company_data_ingestion' if not transaction_id else 'financial_extraction',  # ✅ Skip company lookup if transaction_id provided
            'workflow_decisions': [],
            'node_execution_times': {},
            'node_confidence_scores': {},
            'errors': [],
            'fallback_triggers': ['langgraph_unavailable']
        }
        
        try:
            # ✅ NEW: Skip company data ingestion if transaction_id is provided
            if transaction_id:
                self.logger.info("⚡ FAST PATH: Using provided transaction_id, skipping company data ingestion")

                # Look up document_id from DB using transaction_id + company_number
                document_id = None
                try:
                    from app_modules.database.connection import DatabaseConnection
                    _db = DatabaseConnection()
                    _rows = _db.execute_query(
                        "SELECT document_id, unique_id FROM company_filing_history_accounts "
                        "WHERE transaction_id = ? AND company_registration_number = ? LIMIT 1",
                        (transaction_id, company_number or '')
                    )
                    if not _rows and company_number:
                        # Fallback: match on transaction_id alone
                        _rows = _db.execute_query(
                            "SELECT document_id, unique_id FROM company_filing_history_accounts "
                            "WHERE transaction_id = ? LIMIT 1",
                            (transaction_id,)
                        )
                    if _rows:
                        document_id = _rows[0][0]
                        unique_id = _rows[0][1]
                        self.logger.info(f"✅ Found document_id={document_id} for transaction_id={transaction_id}")
                    else:
                        self.logger.warning(f"⚠️ No document_id found for transaction_id={transaction_id}")
                except Exception as _db_err:
                    self.logger.warning(f"⚠️ DB lookup for document_id failed: {_db_err}")

                # Create minimal company filing data using transaction_id + document_id
                state.update({
                    'transaction_id': transaction_id,
                    'document_id': document_id,
                    'company_filing_data': {
                        'company_name': company_name or 'Direct Transaction',
                        'company_number': company_number or '',
                        'transaction_id': transaction_id,
                        'document_id': document_id,
                        'unique_id': unique_id if '_rows' in dir() and _rows else '',
                        'lookup_method': 'direct_transaction_id',
                        'lookup_confidence': 1.0
                    }
                })
                # Add workflow decision for direct transaction processing
                state['workflow_decisions'].append({
                    'decision_point': 'company_data_ingestion',
                    'decision_type': 'routing',
                    'decision_result': 'direct_transaction_id',
                    'confidence': 1.0,
                    'reasoning': 'Used provided transaction_id, skipping lookup',
                    'timestamp': datetime.now().isoformat()
                })
                
            else:
                # Step 1: Company Data Ingestion (original path)
                self.logger.info("📊 Step 1: Company data ingestion")
                if progress_callback:
                    progress_callback({
                        'stage': 'company_ingestion',
                        'progress': 25,
                        'message': '📊 Extracting company data from Companies House',
                        'timestamp': datetime.now().isoformat()
                    })
                
                step_start = datetime.now()
                # Execute company ingestion directly (no signal timeout in Flask threading)
                try:
                    state = self.company_ingestion_node(state)
                    
                except Exception as e:
                    self.logger.warning(f"⚠️ Company ingestion failed: {str(e)}")
                    # Continue with minimal company data
                    state.update({
                        'errors': state.get('errors', []) + [f"Company ingestion error: {str(e)}"],
                        'company_filing_data': {
                            'company_name': company_name,
                            'company_number': company_number or '',
                            'lookup_method': 'error_fallback',
                            'lookup_confidence': 0.1
                        }
                    })
                
            step_duration = (datetime.now() - step_start).total_seconds()
            
            if progress_callback:
                progress_callback({
                    'stage': 'company_ingestion_complete',
                    'progress': 33,
                    'message': f'✅ Company data extracted in {step_duration:.1f}s',
                    'timestamp': datetime.now().isoformat(),
                    'step_duration': step_duration
                })
            
            # Step 2: Financial Document Extraction
            self.logger.info("📄 Step 2: Financial document processing")
            if progress_callback:
                progress_callback({
                    'stage': 'document_processing',
                    'progress': 50,
                    'message': '📄 Processing financial documents with 3-tier OCR',
                    'timestamp': datetime.now().isoformat()
                })
            
            step_start = datetime.now()
            state = self.financial_extraction_node(state)
            step_duration = (datetime.now() - step_start).total_seconds()
            
            if progress_callback:
                progress_callback({
                    'stage': 'document_processing_complete',
                    'progress': 75,
                    'message': f'✅ Document processing completed in {step_duration:.1f}s',
                    'timestamp': datetime.now().isoformat(),
                    'step_duration': step_duration
                })
            
            # Step 3: Revenue Extraction
            self.logger.info("💰 Step 3: Revenue extraction and estimation")
            if progress_callback:
                progress_callback({
                    'stage': 'revenue_extraction',
                    'progress': 85,
                    'message': '💰 Extracting revenue using smart financial analysis',
                    'timestamp': datetime.now().isoformat()
                })
            
            step_start = datetime.now()
            state = self.turnover_estimation_node(state)
            step_duration = (datetime.now() - step_start).total_seconds()
            
            if progress_callback:
                progress_callback({
                    'stage': 'revenue_extraction_complete',
                    'progress': 95,
                    'message': f'✅ Revenue extraction completed in {step_duration:.1f}s',
                    'timestamp': datetime.now().isoformat(),
                    'step_duration': step_duration
                })
            
            # Step 4: Format results
            result = self._format_workflow_result(state, start_time)
            
            if progress_callback:
                total_duration = (datetime.now() - start_time).total_seconds()
                progress_callback({
                    'stage': 'complete',
                    'progress': 100,
                    'message': f'🎉 Revenue extraction completed successfully in {total_duration:.1f}s',
                    'timestamp': datetime.now().isoformat(),
                    'total_duration': total_duration,
                    'extracted_revenue': result.get('extracted_revenue'),
                    'confidence_score': result.get('confidence_score')
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Sequential workflow execution failed: {str(e)}")
            
            # Add error to state
            state['errors'].append(f"Sequential workflow failed: {str(e)}")
            
            # Return partial results with error
            return self._format_workflow_result(state, start_time)
    
    def _build_langgraph_workflow(self) -> Any:
        """
        Build and compile LangGraph workflow for revenue extraction.
        
        Returns:
            Compiled LangGraph workflow or None if compilation fails
        """
        if not LANGGRAPH_AVAILABLE:
            self.logger.warning("🔄 LangGraph not available - workflow compilation skipped")
            return None
            
        try:
            # Import LangGraph components
            from langgraph.graph import StateGraph, END, START
            from typing import TypedDict
            
            # Define workflow state matching our existing state structure
            class RevenueWorkflowState(TypedDict):
                """State schema for revenue extraction workflow"""
                # Core identification
                company_id: str
                unique_id: str
                company_name: str
                company_number: str
                
                # Workflow data stores
                company_filing_data: dict
                document_processing_data: dict
                revenue_extraction_data: dict
                
                # Workflow metadata
                current_stage: str
                node_execution_times: dict
                workflow_decisions: list
                fallback_triggers: list
                errors: list
                
                # Processing flags
                document_download_success: bool
                vectorization_success: bool
                extraction_complete: bool
            
            # Create workflow graph
            workflow = StateGraph(RevenueWorkflowState)
            
            # Add workflow nodes using our existing node implementations
            workflow.add_node("company_data_ingestion", self._langgraph_company_ingestion_wrapper)
            workflow.add_node("financial_extraction", self._langgraph_financial_extraction_wrapper)  
            workflow.add_node("turnover_estimation", self._langgraph_turnover_estimation_wrapper)
            
            # Define workflow edges
            workflow.add_edge(START, "company_data_ingestion")
            workflow.add_edge("company_data_ingestion", "financial_extraction")
            workflow.add_edge("financial_extraction", "turnover_estimation") 
            workflow.add_edge("turnover_estimation", END)
            
            # Compile and return workflow
            compiled_workflow = workflow.compile()
            
            self.logger.info("✅ LangGraph workflow compiled successfully")
            return compiled_workflow
            
        except Exception as e:
            self.logger.error(f"❌ LangGraph workflow compilation failed: {str(e)}")
            return None
    
    # ── Real-time progress tracking ───────────────────────────────────────────
    @staticmethod
    def _progress_path(company_number: str) -> str:
        import re
        safe = re.sub(r'[^A-Za-z0-9_-]', '_', company_number or 'unknown')
        return f'/tmp/revenue_progress_{safe}.json'

    @staticmethod
    def write_progress(company_number: str, node: str, step: int, message: str, percentage: int, log: bool = True) -> None:
        """Write current node progress. If log=True (default), append message to the running log list.
        Pass log=False for heartbeat ticks — updates the progress bar only, no duplicate log spam."""
        try:
            import json as _json, os as _os
            path = AgenticRevenueService._progress_path(company_number)
            # Preserve existing log history
            existing = {}
            try:
                with open(path) as _f:
                    existing = _json.load(_f)
            except Exception:
                pass
            logs = existing.get('logs', [])
            if log:
                logs.append({'ts': datetime.now().strftime('%H:%M:%S'), 'level': 'info', 'msg': message})
            if len(logs) > 60:
                logs = logs[-60:]
            data = {
                'node': node,
                'step': step,
                'message': message,
                'percentage': percentage,
                'ts': datetime.now().isoformat(),
                'logs': logs
            }
            # Write atomically via temp file
            tmp = path + '.tmp'
            with open(tmp, 'w') as _f:
                _json.dump(data, _f)
            _os.replace(tmp, path)
        except Exception:
            pass  # progress tracking must never crash the workflow

    @staticmethod
    def append_log(company_number: str, message: str, level: str = 'info') -> None:
        """Append a log line to the progress file without changing node/step/percentage."""
        try:
            import json as _json, os as _os
            path = AgenticRevenueService._progress_path(company_number)
            existing = {}
            try:
                with open(path) as _f:
                    existing = _json.load(_f)
            except Exception:
                pass
            logs = existing.get('logs', [])
            logs.append({'ts': datetime.now().strftime('%H:%M:%S'), 'level': level, 'msg': message})
            if len(logs) > 60:
                logs = logs[-60:]
            existing['logs'] = logs
            tmp = path + '.tmp'
            with open(tmp, 'w') as _f:
                _json.dump(existing, _f)
            _os.replace(tmp, path)
        except Exception:
            pass  # progress tracking must never crash the workflow

    def _run_node_with_heartbeat(
        self,
        node_fn,
        state: dict,
        company_number: str,
        node_name: str,
        step: int,
        start_pct: int,
        end_pct: int,
        heartbeat_messages: list,
        page_count: int = 0,
    ) -> dict:
        """
        Run a LangGraph node function while writing a live heartbeat every 5 s.
        This keeps the frontend progress bar moving even during long downloads/OCR.
        No timeout — some documents are 200+ pages and must be allowed to finish.
        """
        import threading

        result_holder = {}
        exc_holder = {}
        start_time = datetime.now()
        stop_event = threading.Event()

        pages_label = f' ({page_count} pages)' if page_count > 0 else ''

        def _heartbeat():
            tick = 0
            while not stop_event.wait(5):  # every 5 seconds — no upper time limit
                elapsed = int((datetime.now() - start_time).total_seconds())
                msg_template = heartbeat_messages[tick % len(heartbeat_messages)]
                # inject page count into the message if the placeholder is present
                msg = msg_template.replace('{pages}', str(page_count) if page_count else '?')
                if '{pages}' not in msg_template and page_count > 0 and tick == 0:
                    msg = f'{msg}{pages_label}'
                # Gently advance percentage — no hard cap based on time
                progress_span = end_pct - start_pct - 5
                pct = min(start_pct + int(progress_span * elapsed / max(progress_span * 3, 60)),
                          end_pct - 5)
                self.write_progress(company_number, node_name, step,
                                    f'{msg} — {elapsed}s', pct, log=False)
                tick += 1

        def _worker():
            try:
                result_holder['result'] = node_fn(state)
            except Exception as e:
                exc_holder['exc'] = e

        t_worker = threading.Thread(target=_worker, daemon=True)
        t_heartbeat = threading.Thread(target=_heartbeat, daemon=True)
        t_heartbeat.start()
        t_worker.start()
        t_worker.join()  # no timeout — let the node run as long as it needs
        stop_event.set()
        t_heartbeat.join(timeout=1)

        if 'exc' in exc_holder:
            raise exc_holder['exc']
        return result_holder.get('result', state)

    def _langgraph_company_ingestion_wrapper(self, state):
        """LangGraph wrapper for company data ingestion node"""
        company_number = (state.get('company_number') or
                          state.get('company_filing_data', {}).get('company_number') or
                          state.get('company_name') or 'unknown')
        try:
            self.write_progress(company_number, 'company_data_ingestion', 1,
                                'Retrieving company information from Companies House…', 10)
            node_start = datetime.now()
            result = self._run_node_with_heartbeat(
                self.company_ingestion_node, state, company_number,
                node_name='company_data_ingestion', step=1,
                start_pct=10, end_pct=22,
                heartbeat_messages=[
                    'Looking up company on Companies House…',
                    'Fetching filing history…',
                    'Checking accounts transactions…',
                    'Retrieving company registration details…',
                ]
            )
            execution_time = (datetime.now() - node_start).total_seconds()
            self.write_progress(company_number, 'company_data_ingestion', 1,
                                f'Company data retrieved ({execution_time:.0f}s)', 22)

            if 'node_execution_times' not in result:
                result['node_execution_times'] = {}
            result['node_execution_times']['company_data_ingestion'] = execution_time
            return result

        except Exception as e:
            self.logger.error(f"Company ingestion node failed: {str(e)}")
            self.write_progress(company_number, 'company_data_ingestion', 1,
                                f'Company lookup failed: {str(e)}', 10)
            state['errors'] = state.get('errors', []) + [f"Company ingestion failed: {str(e)}"]
            return state

    def _langgraph_financial_extraction_wrapper(self, state):
        """LangGraph wrapper for financial extraction node"""
        company_number = (state.get('company_number') or
                          state.get('company_filing_data', {}).get('company_number') or
                          state.get('company_name') or 'unknown')
        try:
            self.write_progress(company_number, 'financial_extraction', 2,
                                'Downloading financial accounts from Companies House…', 25)
            node_start = datetime.now()
            result = self._run_node_with_heartbeat(
                self.financial_extraction_node, state, company_number,
                node_name='financial_extraction', step=2,
                start_pct=25, end_pct=68,
                heartbeat_messages=[
                    'Downloading PDF accounts from Companies House…',
                    'Running OCR / Azure Document Intelligence on {pages}-page document…',
                    'Extracting text from {pages} pages…',
                    'Splitting {pages}-page document into text chunks…',
                    'Generating vector embeddings for document chunks…',
                    'Storing embeddings in vector database…',
                    'Still processing — large {pages}-page document, please wait…',
                ]
            )
            execution_time = (datetime.now() - node_start).total_seconds()
            doc_data = result.get('document_processing_data', {})
            page_count = doc_data.get('page_count', 0)
            pages_label = f' ({page_count} pages)' if page_count > 0 else ''
            if doc_data.get('download_success'):
                chunk_count = doc_data.get('chunk_count', 0)
                self.write_progress(company_number, 'financial_extraction_vectorized', 3,
                                    f'Document vectorised{pages_label} — {chunk_count} chunks ready ({execution_time:.0f}s)', 68)
            else:
                self.write_progress(company_number, 'financial_extraction_vectorized', 3,
                                    f'Using cached vectors — fast path ({execution_time:.0f}s)', 68)

            if 'node_execution_times' not in result:
                result['node_execution_times'] = {}
            result['node_execution_times']['financial_extraction'] = execution_time
            return result

        except Exception as e:
            self.logger.error(f"Financial extraction node failed: {str(e)}")
            self.write_progress(company_number, 'financial_extraction', 2,
                                f'Document processing failed: {str(e)}', 25)
            state['errors'] = state.get('errors', []) + [f"Financial extraction failed: {str(e)}"]
            return state

    def _langgraph_turnover_estimation_wrapper(self, state):
        """LangGraph wrapper for turnover estimation node"""
        company_number = (state.get('company_number') or
                          state.get('company_filing_data', {}).get('company_number') or
                          state.get('company_name') or 'unknown')
        try:
            self.write_progress(company_number, 'turnover_estimation', 4,
                                'Running RAG search for revenue figures…', 72)
            node_start = datetime.now()
            result = self._run_node_with_heartbeat(
                self.turnover_estimation_node, state, company_number,
                node_name='turnover_estimation', step=4,
                start_pct=72, end_pct=95,
                heartbeat_messages=[
                    'Searching document for turnover and revenue figures…',
                    'Scoring candidate revenue values…',
                    'Validating extracted figures…',
                    'Finalising revenue extraction result…',
                ]
            )
            execution_time = (datetime.now() - node_start).total_seconds()
            rev_data = result.get('revenue_extraction_data', {})
            rev = rev_data.get('extracted_revenue')
            conf = rev_data.get('extraction_confidence', 0)
            msg = (f'Revenue extracted: £{rev:,.0f} (confidence {conf*100:.0f}%) in {execution_time:.0f}s'
                   if rev else f'Turnover estimation complete ({execution_time:.0f}s)')
            self.write_progress(company_number, 'turnover_estimation', 4, msg, 95)

            if 'node_execution_times' not in result:
                result['node_execution_times'] = {}
            result['node_execution_times']['turnover_estimation'] = execution_time
            return result

        except Exception as e:
            self.logger.error(f"Turnover estimation node failed: {str(e)}")
            self.write_progress(company_number, 'turnover_estimation', 4,
                                f'Revenue estimation failed: {str(e)}', 72)
            state['errors'] = state.get('errors', []) + [f"Turnover estimation failed: {str(e)}"]
            return state
    
    def _format_workflow_result(self, state: Dict[str, Any], start_time: datetime) -> Dict[str, Any]:
        """
        Format workflow state into standardized API response.
        
        Compatible with existing update_revenue endpoint expectations.
        """
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Extract key data from workflow state
        company_data = state.get('company_filing_data', {})
        document_data = state.get('document_processing_data', {})
        revenue_data = state.get('revenue_extraction_data', {})
        
        # Format response
        result = {
            # Core revenue extraction results
            'extracted_revenue': revenue_data.get('extracted_revenue'),
            'revenue_currency': revenue_data.get('revenue_currency', 'GBP'),
            'confidence_score': revenue_data.get('extraction_confidence', 0.0),
            'extraction_method': revenue_data.get('extraction_method', 'unknown'),
            'alternative_revenues': revenue_data.get('alternative_revenues', []),
            'revenue_source_text': revenue_data.get('revenue_source_text', []),

            # Portal display fields expected by JS
            'company_name': company_data.get('company_name'),
            'workflow_status': 'success' if len(state.get('errors', [])) == 0 and revenue_data.get('extracted_revenue') else 'completed',
            'revenue_year': revenue_data.get('revenue_year'),
            'period_type': revenue_data.get('period_type', 'Annual'),
            
            # Workflow metadata
            'workflow_summary': {
                'execution_time': execution_time,
                'total_nodes': len(state.get('node_execution_times', {})),
                'workflow_decisions': len(state.get('workflow_decisions', [])),
                'fallback_triggers': state.get('fallback_triggers', []),
                'errors_count': len(state.get('errors', []))
            },
            
            # Companies House data
            'companies_house_data': {
                'company_name': company_data.get('company_name'),
                'company_number': company_data.get('company_number'),
                'filing_date': company_data.get('filing_date'),
                'transaction_id': company_data.get('transaction_id'),
                'lookup_method': company_data.get('lookup_method'),
                'validation_passed': company_data.get('validation_passed', False)
            },
            
            # Document processing summary
            'document_processing_summary': {
                'document_downloaded': document_data.get('document_downloaded', False),
                'text_extracted': document_data.get('text_extracted', False),
                'vector_stored': document_data.get('vector_db_stored', False),
                'chunk_count': document_data.get('chunk_count', 0),
                'processing_method': document_data.get('processing_method', 'unknown')
            },
            
            # Agentic insights
            'agentic_insights': {
                'workflow_decisions': state.get('workflow_decisions', []),
                'node_confidence_scores': state.get('node_confidence_scores', {}),
                'validation_notes': revenue_data.get('validation_notes', []),
                'similarity_scores': revenue_data.get('similarity_scores', [])
            },
            
            # Performance metrics
            'execution_time': execution_time,
            'workflow_steps': self._extract_workflow_steps(state),
            'validation_results': {
                'validation_passed': bool(revenue_data.get('validation_passed', False)),
                'fallback_used': bool(revenue_data.get('fallback_used', False)),
                'source_text_available': bool(revenue_data.get('revenue_source_text'))
            },
            
            # Error handling
            'success': len(state.get('errors', [])) == 0,
            'errors': state.get('errors', []),
            'warnings': self._extract_warnings(state)
        }
        
        # Only update database if auto_save is enabled (for approval workflow compatibility)
        auto_save = self.config.get('auto_save', False)
        if auto_save:
            self._update_extracted_revenue_database(result, state)
        else:
            self.logger.info("📋 Auto-save disabled - revenue extracted but not saved. Use approval workflow to save.")
        
        # Sanitize result for JSON serialization
        return sanitize_for_json(result)

    def _extract_workflow_steps(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract workflow steps summary from state."""
        steps = []
        
        decisions = state.get('workflow_decisions', [])
        execution_times = state.get('node_execution_times', {})
        confidence_scores = state.get('node_confidence_scores', {})
        
        for decision in decisions:
            step = {
                'step_name': decision.get('decision_point', 'unknown'),
                'execution_time': execution_times.get(decision.get('decision_point', ''), 0.0),
                'confidence': confidence_scores.get(decision.get('decision_point', ''), 0.0),
                'result': decision.get('decision_result', 'unknown'),
                'reasoning': decision.get('reasoning', '')
            }
            steps.append(step)
        
        return steps
    
    def _extract_warnings(self, state: Dict[str, Any]) -> List[str]:
        """Extract warnings from workflow state."""
        warnings = []
        
        # Check for fallback usage
        fallback_triggers = state.get('fallback_triggers', [])
        if fallback_triggers:
            warnings.append(f"Fallbacks triggered: {', '.join(fallback_triggers)}")
        
        # Check for low confidence
        confidence_scores = state.get('node_confidence_scores', {})
        low_confidence_nodes = [
            node for node, score in confidence_scores.items() 
            if score < 0.5
        ]
        if low_confidence_nodes:
            warnings.append(f"Low confidence in nodes: {', '.join(low_confidence_nodes)}")
        
        return warnings
    
    def _update_execution_stats(self, result: Dict[str, Any], execution_time: float):
        """Update internal execution statistics."""
        if result.get('success', False):
            self.execution_stats['successful_extractions'] += 1
        else:
            self.execution_stats['failed_extractions'] += 1
        
        # Update method usage
        method = result.get('extraction_method', 'unknown')
        if method in self.execution_stats['method_usage']:
            self.execution_stats['method_usage'][method] += 1
        
        # Update timing
        total_extractions = self.execution_stats['total_extractions']
        current_avg = self.execution_stats['average_execution_time']
        
        new_avg = ((current_avg * (total_extractions - 1)) + execution_time) / total_extractions
        self.execution_stats['average_execution_time'] = new_avg
        self.execution_stats['last_execution_time'] = datetime.now().isoformat()
    
    def _create_error_response(self, company_name: str, error_message: str, start_time: datetime) -> Dict[str, Any]:
        """Create standardized error response."""
        execution_time = (datetime.now() - start_time).total_seconds()
        
        response = {
            'extracted_revenue': None,
            'revenue_currency': 'GBP',
            'confidence_score': 0.0,
            'extraction_method': 'failed',
            'alternative_revenues': [],
            'workflow_summary': {
                'execution_time': execution_time,
                'total_nodes': 0,
                'workflow_decisions': 0,
                'fallback_triggers': ['service_error'],
                'errors_count': 1
            },
            'companies_house_data': {
                'company_name': company_name,
                'validation_passed': False
            },
            'document_processing_summary': {
                'document_downloaded': False,
                'text_extracted': False,
                'vector_stored': False,
                'chunk_count': 0
            },
            'agentic_insights': {
                'workflow_decisions': [],
                'node_confidence_scores': {},
                'validation_notes': [f'Service error: {error_message}']
            },
            'execution_time': execution_time,
            'workflow_steps': [],
            'validation_results': {
                'validation_passed': False,
                'fallback_used': True
            },
            'success': False,
            'errors': [error_message],
            'warnings': ['Revenue extraction service failed']
        }
        return sanitize_for_json(response)
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get current execution statistics for monitoring."""
        return dict(self.execution_stats)
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the agentic revenue service."""
        health_status = {
            'service_healthy': True,
            'langgraph_available': LANGGRAPH_AVAILABLE,
            'nodes_initialized': True,
            'dependencies_available': {},
            'last_execution': self.execution_stats.get('last_execution_time'),
            'total_extractions': self.execution_stats.get('total_extractions', 0)
        }
        
        # Check node dependencies
        try:
            health_status['dependencies_available']['companies_house_client'] = bool(
                self.services_container.get('companies_house_client')
            )
            health_status['dependencies_available']['document_download_agent'] = bool(
                self.services_container.get('document_download_agent')
            )
            health_status['dependencies_available']['rag_document_agent'] = bool(
                self.services_container.get('rag_document_agent')
            )
            health_status['dependencies_available']['smart_financial_extraction_agent'] = bool(
                self.services_container.get('smart_financial_extraction_agent')
            )
            health_status['dependencies_available']['turnover_estimation_agent'] = bool(
                self.services_container.get('turnover_estimation_agent')
            )
        except Exception as e:
            health_status['service_healthy'] = False
            health_status['health_check_error'] = str(e)
        
        return health_status

    def _update_extracted_revenue_database(self, result: Dict[str, Any], state: Dict[str, Any]) -> None:
        """
        Update the database with extracted revenue information.
        
        Saves the extracted revenue to both:
        1. company_filing_history_accounts.extracted_revenue (filing history)
        2. company_financials.latest_revenue (main financials table)
        
        Args:
            result: The formatted workflow result containing extracted revenue
            state: The workflow state containing company and filing information
        """
        if not self.filing_history_repository:
            self.logger.warning("⚠️ Filing history repository not available - cannot update database")
            return
            
        try:
            # Extract data from state and result
            company_data = state.get('company_filing_data', {})
            unique_id = company_data.get('unique_id')
            transaction_id = company_data.get('transaction_id') 
            extracted_revenue = result.get('extracted_revenue')
            extracted_profit = result.get('extracted_profit', 0)
            revenue_year = result.get('revenue_year')
            period_type = result.get('period_type', 'Annual')
            extraction_confidence = result.get('extraction_confidence', 0.8)
            
            # Only update if we have all required data
            if not all([unique_id, transaction_id, extracted_revenue]):
                self.logger.warning(f"⚠️ Insufficient data for database update - unique_id: {unique_id}, transaction_id: {transaction_id}, revenue: {extracted_revenue}")
                return
                
            # 1. Update filing history table (existing functionality)
            success = self.filing_history_repository.update_extracted_revenue(
                unique_id=unique_id,
                transaction_id=transaction_id,
                extracted_revenue=str(extracted_revenue)
            )
            
            if success:
                self.logger.info(f"✅ Successfully updated extracted revenue in filing history: {extracted_revenue} for company {unique_id}")
            else:
                self.logger.error(f"❌ Failed to update extracted revenue in filing history for company {unique_id}")
            
            # 2. Update company_financials table (auto-approval)
            # Convert extracted_revenue to float and handle None values
            from datetime import datetime
            revenue_value = float(extracted_revenue) if extracted_revenue is not None else 0.0
            profit_value = float(extracted_profit) if extracted_profit is not None else 0.0
            year_value = int(revenue_year) if revenue_year is not None else datetime.now().year
            
            self._update_company_financials_table(
                company_id=unique_id,
                latest_revenue=revenue_value,
                latest_profit=profit_value,
                revenue_year=year_value,
                period_type=period_type,
                extraction_confidence=extraction_confidence
            )
                
        except Exception as e:
            self.logger.error(f"❌ Error updating extracted revenue in database: {e}")
            # Don't raise - this shouldn't break the main workflow

    def _update_company_financials_table(self, company_id: str, latest_revenue: float, 
                                       latest_profit: float, revenue_year: int, 
                                       period_type: str, extraction_confidence: float) -> None:
        """
        Update the company_financials table with extracted revenue data.
        
        This provides automatic approval functionality, bypassing the manual approval step.
        """
        try:
            import sqlite3
            import os
            from datetime import datetime
            
            # Get database path
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                'data', 
                'credit_risk.db'
            )
            
            # Validate inputs
            if not revenue_year:
                revenue_year = datetime.now().year
            
            extraction_date = datetime.now().isoformat()
            
            # Update the company_financials table
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Check if company exists in company_financials table
                cursor.execute("""
                    SELECT COUNT(*) FROM company_financials WHERE company_id = ?
                """, (company_id,))
                
                exists = cursor.fetchone()[0] > 0
                
                if exists:
                    # Update existing record
                    cursor.execute("""
                        UPDATE company_financials 
                        SET latest_revenue = ?, 
                            latest_profit = ?, 
                            revenue_year = ?, 
                            period_type = ?, 
                            extraction_confidence = ?, 
                            extraction_date = ?
                        WHERE company_id = ?
                    """, (latest_revenue, latest_profit, revenue_year, period_type, 
                         extraction_confidence, extraction_date, company_id))
                else:
                    # Insert new record - provide defaults for required fields
                    cursor.execute("""
                        INSERT INTO company_financials 
                        (company_id, latest_revenue, latest_profit, revenue_year, 
                         period_type, extraction_confidence, extraction_date,
                         sales_gbp, cost_usd, net_profit_usd, profit_margin_percent)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0)
                    """, (company_id, latest_revenue, latest_profit, revenue_year, 
                         period_type, extraction_confidence, extraction_date))
                
                conn.commit()
                rows_affected = cursor.rowcount
                
                self.logger.info(f"✅ Auto-approved revenue updates for company_id {company_id}: "
                               f"£{latest_revenue:,.0f} revenue, £{latest_profit:,.0f} profit "
                               f"({period_type} {revenue_year}, confidence: {extraction_confidence:.1%}, rows: {rows_affected})")
                
        except Exception as e:
            self.logger.error(f"❌ Error updating company_financials table: {e}")
            # Don't raise - this shouldn't break the main workflow