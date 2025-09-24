"""
Phase 2 Integration Layer for Streamlit App

This module provides the bridge between Phase 1 UI and Phase 2 real agent functionality.
It allows toggling between mock and real agent execution while maintaining the same UI.
"""
import os
import sys
import streamlit as st
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import json
import time
import base64
from io import BytesIO

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Visualization libraries
try:
    import graphviz
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    # Phase 2 imports - real functionality
    from ..workflows.sic_prediction_workflow import SICPredictionWorkflow
    from ..apis.companies_house_client import create_companies_house_client
    from ..apis.web_scraper import create_web_scraper
    PHASE2_AVAILABLE = True
except ImportError:
    # Fallback if Phase 2 dependencies not available
    PHASE2_AVAILABLE = False

class Phase2Integration:
    """
    Integration layer for Phase 2 functionality
    
    Handles:
    - Real LangGraph workflow execution
    - Companies House API integration
    - Web scraping for business intelligence
    - Progress tracking and status updates
    """
    
    def _check_api_keys(self) -> Dict[str, bool]:
        """Check which API keys are configured"""
        status = {
            'openai_configured': False,
            'companies_house_configured': False,
            'azure_openai': False
        }
        
        # Check OpenAI configuration (both standard and Azure)
        openai_key = os.getenv('OPENAI_API_KEY')
        openai_endpoint = os.getenv('OPENAI_ENDPOINT')
        
        if openai_key and openai_key != 'your_openai_api_key_here':
            if openai_endpoint and openai_endpoint != 'your_openai_endpoint_here':
                # Azure OpenAI configuration
                status['openai_configured'] = True
                status['azure_openai'] = True
            elif openai_key.startswith('sk-'):
                # Standard OpenAI configuration
                status['openai_configured'] = True
                status['azure_openai'] = False
        
        # Check Companies House API
        ch_key = os.getenv('COMPANIES_HOUSE_API_KEY')
        if ch_key and ch_key != 'your_companies_house_api_key_here':
            status['companies_house_configured'] = True
        
        return status
    
    def __init__(self, use_real_agents: bool = False):
        # Check API configuration
        self.api_keys_configured = self._check_api_keys()
        self.use_real_agents = use_real_agents and PHASE2_AVAILABLE and self.api_keys_configured.get('openai_configured', False)
        
        if self.use_real_agents:
            try:
                # Initialize real components
                self.sic_workflow = SICPredictionWorkflow()
                self.companies_house_client = create_companies_house_client()
                self.web_scraper = create_web_scraper()
            except Exception as e:
                st.error(f"Error initializing Phase 2 components: {e}")
                self.use_real_agents = False
                self._initialize_mock_components()
        else:
            self._initialize_mock_components()
    
    def _initialize_mock_components(self):
        """Initialize mock components for demo mode"""
        self.sic_workflow = None
        self.companies_house_client = None
        self.web_scraper = None
    
    def execute_sic_prediction_workflow(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute SIC prediction workflow - real or mock
        
        Args:
            company_data: Company information to process
            
        Returns:
            Workflow execution results
        """
        if self.use_real_agents and self.sic_workflow:
            # Execute real LangGraph workflow
            return self._execute_real_workflow(company_data)
        else:
            # Execute mock workflow for demo
            return self._execute_mock_workflow(company_data)

    def render_langgraph_visual_flow(self) -> Optional[str]:
        """
        Create a professional LangGraph visual flow diagram matching the attached image style
        Returns base64 encoded image for Streamlit display
        """
        if not VISUALIZATION_AVAILABLE:
            return None
            
        # Create figure with professional styling
        fig, ax = plt.subplots(figsize=(12, 14))
        fig.patch.set_facecolor('white')
        ax.set_facecolor('white')
        
        # Define the workflow nodes with positions matching LangGraph style
        nodes = [
            {"name": "__start__", "pos": (6, 12), "type": "start", "color": "#FFD700"},
            {"name": "data_ingestion", "pos": (6, 10), "type": "process", "color": "#E8BBE8"},
            {"name": "document_retrieval", "pos": (6, 8), "type": "process", "color": "#E8BBE8"},
            {"name": "nlp_processing", "pos": (6, 6), "type": "process", "color": "#E8BBE8"},
            {"name": "sic_classification", "pos": (3, 4), "type": "process", "color": "#E8BBE8"},
            {"name": "validation", "pos": (6, 2), "type": "process", "color": "#E8BBE8"},
            {"name": "__end__", "pos": (6, 0), "type": "end", "color": "#90EE90"}
        ]
        
        # Define edges with conditional flows
        edges = [
            {"from": 0, "to": 1, "type": "solid"},  # start -> data_ingestion
            {"from": 1, "to": 2, "type": "solid"},  # data_ingestion -> document_retrieval
            {"from": 2, "to": 3, "type": "solid"},  # document_retrieval -> nlp_processing
            {"from": 3, "to": 4, "type": "solid"},  # nlp_processing -> sic_classification
            {"from": 4, "to": 5, "type": "solid"},  # sic_classification -> validation
            {"from": 5, "to": 6, "type": "solid"},  # validation -> end
            {"from": 3, "to": 5, "type": "dotted"},  # conditional: nlp_processing -> validation (bypass)
        ]
        
        # Draw edges first (so they appear behind nodes)
        for edge in edges:
            start_node = nodes[edge["from"]]
            end_node = nodes[edge["to"]]
            start_pos = start_node["pos"]
            end_pos = end_node["pos"]
            
            # Calculate arrow positions
            dx = end_pos[0] - start_pos[0]
            dy = end_pos[1] - start_pos[1]
            length = (dx**2 + dy**2)**0.5
            
            if length > 0:
                # Offset to node edges
                offset = 0.7
                start_x = start_pos[0] + offset * (dx / length)
                start_y = start_pos[1] - offset * (abs(dy) / length) if dy < 0 else start_pos[1] - offset
                end_x = end_pos[0] - offset * (dx / length)
                end_y = end_pos[1] + offset * (abs(dy) / length) if dy < 0 else end_pos[1] + offset
                
                # Draw arrow based on type
                if edge["type"] == "solid":
                    ax.annotate('', xy=(end_x, end_y), xytext=(start_x, start_y),
                               arrowprops=dict(arrowstyle='->', lw=2, color='#333333'))
                else:  # dotted
                    ax.annotate('', xy=(end_x, end_y), xytext=(start_x, start_y),
                               arrowprops=dict(arrowstyle='->', lw=2, color='#666666', 
                                             linestyle='dotted', alpha=0.7))
        
        # Draw nodes
        for i, node in enumerate(nodes):
            x, y = node["pos"]
            
            if node["type"] == "start":
                # Square start node
                from matplotlib.patches import Rectangle
                rect = Rectangle((x-0.8, y-0.4), 1.6, 0.8,
                               facecolor=node["color"], edgecolor='#333333', linewidth=2)
                ax.add_patch(rect)
                ax.text(x, y, node["name"], fontsize=11, ha='center', va='center',
                       fontweight='bold', color='#333333')
                       
            elif node["type"] == "end":
                # Square end node
                from matplotlib.patches import Rectangle
                rect = Rectangle((x-0.8, y-0.4), 1.6, 0.8,
                               facecolor=node["color"], edgecolor='#333333', linewidth=2)
                ax.add_patch(rect)
                ax.text(x, y, node["name"], fontsize=11, ha='center', va='center',
                       fontweight='bold', color='#333333')
                       
            else:  # process nodes
                # Rounded rectangle for process nodes (like in the image)
                from matplotlib.patches import FancyBboxPatch
                box = FancyBboxPatch((x-1.2, y-0.5), 2.4, 1.0,
                                   boxstyle="round,pad=0.1",
                                   facecolor=node["color"],
                                   edgecolor='#333333',
                                   linewidth=2)
                ax.add_patch(box)
                
                # Node text
                ax.text(x, y, node["name"], fontsize=10, ha='center', va='center',
                       fontweight='bold', color='#333333')
        
        # Add title
        ax.text(6, 13.5, 'LangGraph SIC Prediction Workflow', 
               fontsize=16, ha='center', va='center', fontweight='bold', color='#333333')
        
        # Add workflow description
        ax.text(6, 13, 'Multi-Agent Credit Risk Analysis Pipeline', 
               fontsize=12, ha='center', va='center', style='italic', color='#666666')
        
        # Add legend
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], color='#333333', lw=2, label='Sequential Flow'),
            Line2D([0], [0], color='#666666', lw=2, linestyle='dotted', label='Conditional Flow'),
            mpatches.Patch(color='#FFD700', label='Start Node'),
            mpatches.Patch(color='#E8BBE8', label='Process Node'),
            mpatches.Patch(color='#90EE90', label='End Node')
        ]
        ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.15, 1))
        
        # Set axis properties
        ax.set_xlim(0, 12)
        ax.set_ylim(-1, 14)
        ax.set_aspect('equal')
        ax.axis('off')
        
        # Convert to base64 for Streamlit
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=200, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return img_base64

    def get_real_langgraph_visualization(self) -> Optional[str]:
        """
        Get the actual LangGraph built-in visualization if workflow is available
        """
        if not self.use_real_agents or not self.sic_workflow:
            return None
            
        try:
            # Try to get the LangGraph built-in mermaid diagram
            if hasattr(self.sic_workflow, 'compiled_workflow'):
                # Get the graph structure
                graph_dict = self.sic_workflow.compiled_workflow.get_graph()
                
                # Create a mermaid diagram from the graph
                mermaid_code = "graph TD\n"
                
                # Add nodes
                for node in graph_dict.nodes:
                    node_id = node.replace("_", "")
                    node_label = node.replace("_", " ").title()
                    if node == "__start__":
                        mermaid_code += f"    START[{node_label}]\n"
                    elif node == "__end__":
                        mermaid_code += f"    END[{node_label}]\n"
                    else:
                        mermaid_code += f"    {node_id}({node_label})\n"
                
                # Add edges
                for edge in graph_dict.edges:
                    start = edge.source.replace("_", "") if edge.source != "__start__" else "START"
                    end = edge.target.replace("_", "") if edge.target != "__end__" else "END"
                    if start == "START":
                        start = "START"
                    if end == "END":
                        end = "END"
                    mermaid_code += f"    {start} --> {end}\n"
                
                # Add styling
                mermaid_code += """
    classDef startEnd fill:#FFD700,stroke:#333,stroke-width:2px,color:#333
    classDef process fill:#E8BBE8,stroke:#333,stroke-width:2px,color:#333
    
    class START,END startEnd
    class dataingestio,documentretriev,nlpprocessing,sicclassificat,validation process
                """
                
                return mermaid_code
                
        except Exception as e:
            st.warning(f"Could not generate real LangGraph visualization: {e}")
            return None
            
        return None

    def create_mermaid_diagram(self) -> str:
        """
        Create a professional Mermaid diagram for the LangGraph workflow
        """
        mermaid_code = """
        graph TD
            START[__start__] --> DI[data_ingestion]
            DI --> DR[document_retrieval]
            DR --> NLP[nlp_processing]
            NLP --> SIC[sic_classification]
            SIC --> VAL[validation]
            VAL --> END[__end__]
            NLP -.-> VAL
            
            classDef startEnd fill:#FFD700,stroke:#333,stroke-width:3px,color:#333
            classDef process fill:#E8BBE8,stroke:#333,stroke-width:2px,color:#333
            classDef conditional stroke-dasharray: 5 5
            
            class START,END startEnd
            class DI,DR,NLP,SIC,VAL process
        """
        return mermaid_code
    
    def _execute_real_workflow(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute real Phase 2 LangGraph workflow"""
        try:
            # Progress tracking
            progress_placeholder = st.empty()
            
            with progress_placeholder.container():
                st.info("🚀 Executing Real LangGraph Workflow...")
                progress_bar = st.progress(0)
                status_text = st.empty()
            
            # Execute workflow with progress updates
            status_text.text("Starting workflow...")
            progress_bar.progress(10)
            
            # Run the actual workflow
            if self.sic_workflow:
                results = self.sic_workflow.execute_workflow(company_data)
            else:
                # Fallback to mock if workflow not available
                results = self._execute_mock_workflow(company_data)
            
            # Update progress
            progress_bar.progress(100)
            status_text.text("Workflow completed!")
            time.sleep(1)
            progress_placeholder.empty()
            
            return {
                "success": results.get("success", False),
                "workflow_type": "real_langgraph" if self.sic_workflow else "mock_fallback",
                "agent_results": results.get("agent_results", {}),
                "confidence_scores": results.get("confidence_scores", {}),
                "execution_time": results.get("execution_time", 0),
                "errors": results.get("errors", []),
                "enhanced_data": results.get("company_data", {}),
                "workflow_id": results.get("workflow_id", "")
            }
            
        except Exception as e:
            return {
                "success": False,
                "workflow_type": "real_langgraph",
                "error": f"Real workflow execution failed: {str(e)}",
                "execution_time": 0
            }
    
    def _execute_mock_workflow(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute mock workflow for demonstration"""
        import time
        import random
        
        # Mock agent execution with realistic timing
        mock_agents = [
            ("Data Ingestion", 2),
            ("Document Retrieval", 3),
            ("NLP Processing", 4),
            ("SIC Classification", 3),
            ("Validation", 2)
        ]
        
        progress_placeholder = st.empty()
        agent_results = {}
        confidence_scores = {}
        
        with progress_placeholder.container():
            st.info("🔄 Executing Mock Agent Workflow...")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, (agent_name, duration) in enumerate(mock_agents):
                status_text.text(f"Running {agent_name}...")
                
                # Simulate processing time
                for j in range(duration * 10):
                    time.sleep(0.1)
                    progress = (i * 100 + (j + 1) * 100 / (duration * 10)) / len(mock_agents)
                    progress_bar.progress(int(progress))
                
                # Mock results
                confidence = random.uniform(0.7, 0.95)
                agent_results[agent_name.lower().replace(" ", "_")] = {
                    "agent_name": f"{agent_name}Agent",
                    "timestamp": datetime.now().isoformat(),
                    "success": True,
                    "confidence": confidence,
                    "data": f"Mock {agent_name.lower()} results",
                    "error_message": None
                }
                confidence_scores[agent_name.lower().replace(" ", "_")] = confidence
            
            status_text.text("Workflow completed!")
            time.sleep(0.5)
        
        progress_placeholder.empty()
        
        return {
            "success": True,
            "workflow_type": "mock",
            "agent_results": agent_results,
            "confidence_scores": confidence_scores,
            "execution_time": sum(duration for _, duration in mock_agents),
            "errors": [],
            "enhanced_data": company_data,
            "workflow_id": f"mock_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
    
    def get_enhanced_company_data(self, company_number: str) -> Dict[str, Any]:
        """
        Get enhanced company data from Companies House API
        
        Args:
            company_number: Companies House company number
            
        Returns:
            Enhanced company data
        """
        if self.use_real_agents and self.companies_house_client:
            return self.companies_house_client.get_enhanced_company_data(company_number)
        else:
            # Return mock enhanced data
            return {
                "success": True,
                "data": {
                    "profile": {
                        "CompanyNumber": company_number,
                        "CompanyName": f"Enhanced Company {company_number}",
                        "data_source": "mock_api"
                    }
                }
            }
    
    def scrape_company_website(self, company_name: str, website_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Scrape company website for business intelligence
        
        Args:
            company_name: Company name
            website_url: Optional website URL
            
        Returns:
            Scraped content and business intelligence
        """
        if self.use_real_agents and self.web_scraper:
            return self.web_scraper.scrape_company_website(company_name, website_url)
        else:
            # Return mock scraped data
            from ..apis.web_scraper import MockWebContentScraper
            mock_scraper = MockWebContentScraper()
            return mock_scraper.scrape_company_website(company_name, website_url)

# Streamlit UI Components for Phase 2
def render_phase2_controls():
    """Render Phase 2 control panel in sidebar"""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🚀 **Phase 2 Controls**")
    
    # Phase 2 availability status
    if PHASE2_AVAILABLE:
        st.sidebar.success("✅ Phase 2 Dependencies Available")

def render_langgraph_visualization():
    """Render LangGraph workflow visualization in Streamlit"""
    st.markdown("### 🔄 LangGraph Workflow Visualization")
    
    # Create tabs for different visualization types
    tab1, tab2, tab3, tab4 = st.tabs(["🎨 Professional Flow", "� Real LangGraph", "�📊 Mermaid Diagram", "📈 Live Status"])
    
    with tab1:
        st.markdown("#### Professional LangGraph Workflow")
        
        # Initialize Phase 2 integration
        try:
            integration = Phase2Integration(use_real_agents=True)
            
            # Render professional matplotlib flow diagram
            flow_image = integration.render_langgraph_visual_flow()
            if flow_image:
                st.markdown(f'<img src="data:image/png;base64,{flow_image}" style="width:100%; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">', 
                          unsafe_allow_html=True)
                
                # Add workflow description
                st.markdown("""
                **Workflow Description:**
                - **Start**: Initialize the workflow with company data
                - **Data Ingestion**: Validate and prepare company information
                - **Document Retrieval**: Fetch company documents from Companies House API
                - **NLP Processing**: Analyze business content using RAG techniques
                - **SIC Classification**: Predict appropriate SIC codes using AI
                - **Validation**: Verify predictions and calculate confidence scores
                - **End**: Complete workflow with results
                
                The dotted line shows a conditional bypass route for cases where documents are unavailable.
                """)
            else:
                st.warning("Visualization dependencies not available. Install matplotlib and graphviz.")
                render_text_workflow_fallback()
                
        except Exception as e:
            st.error(f"Error rendering flow diagram: {e}")
            render_text_workflow_fallback()
    
    with tab2:
        st.markdown("#### Real LangGraph Structure")
        
        try:
            integration = Phase2Integration(use_real_agents=True)
            real_graph = integration.get_real_langgraph_visualization()
            
            if real_graph:
                st.markdown("**Live LangGraph Structure from Compiled Workflow:**")
                st.code(real_graph, language="mermaid")
                
                # Add execution button
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🚀 Execute Real Workflow", type="primary"):
                        st.info("Real workflow execution would start here...")
                        
                with col2:
                    st.metric("Workflow Status", "Ready" if integration.use_real_agents else "Mock Mode")
                        
            else:
                st.info("Real LangGraph not available. Enable real agents to see live workflow structure.")
                
        except Exception as e:
            st.error(f"Error getting real LangGraph: {e}")
    
    with tab3:
        st.markdown("#### Mermaid Workflow Diagram")
        
        try:
            integration = Phase2Integration(use_real_agents=True)
            mermaid_code = integration.create_mermaid_diagram()
            
            # Display enhanced mermaid diagram
            st.markdown("**Enhanced Mermaid Diagram (Copy to any Mermaid viewer):**")
            st.code(mermaid_code, language="text")
            
            st.markdown("🔗 **Try it online:** [Mermaid Live Editor](https://mermaid.live/)")
            
        except Exception as e:
            st.error(f"Error creating Mermaid diagram: {e}")
    
    with tab4:
        st.markdown("#### Live Agent Status")
        
        # Real-time status simulation with enhanced styling
        st.markdown("**Current Workflow State:**")
        
        # Status with progress indicators
        agents = [
            {"name": "Data Ingestion", "status": "🟢 Ready", "progress": 100, "description": "Company data validation"},
            {"name": "Document Retrieval", "status": "🟡 Waiting", "progress": 0, "description": "Companies House API calls"},
            {"name": "NLP Processing", "status": "🟡 Waiting", "progress": 0, "description": "Business content analysis"},
            {"name": "SIC Classification", "status": "🟡 Waiting", "progress": 0, "description": "AI-powered SIC prediction"},
            {"name": "Validation", "status": "🟡 Waiting", "progress": 0, "description": "Result verification"}
        ]
        
        for i, agent in enumerate(agents):
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 1, 2])
                
                with col1:
                    st.markdown(f"**{agent['name']}**")
                    st.caption(agent['description'])
                    
                with col2:
                    st.write(agent['status'])
                    
                with col3:
                    st.progress(agent['progress'] / 100)
                    
                with col4:
                    if i == 0:  # First agent ready
                        st.button(f"▶️ Run", key=f"run_{i}", disabled=False)
                    else:
                        st.button(f"⏸️ Wait", key=f"wait_{i}", disabled=True)
                
                if i < len(agents) - 1:
                    st.divider()

def render_text_workflow_fallback():
    """Fallback text-based workflow visualization"""
    st.markdown("""
    ```
    📥 Data Ingestion Agent
         ↓
    📄 Document Retrieval Agent
         ↓
    🔍 NLP Processing Agent
         ↓
    🏷️ SIC Classification Agent
         ↓
    ⚠️ Validation Agent
    ```
    """)
    
    st.info("💡 Install matplotlib and graphviz for enhanced visualizations")

def render_workflow_results(results: Dict[str, Any]):
    """Render workflow execution results"""
    if not results:
        return
        
    st.markdown("### 📊 Workflow Results")
    
    # Success indicator
    if results.get("success"):
        st.success("✅ Workflow executed successfully!")
    else:
        st.error("❌ Workflow execution failed")
        if "error" in results:
            st.error(f"Error: {results['error']}")
        return
    
    # Execution metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Execution Time", f"{results.get('execution_time', 0):.2f}s")
    with col2:
        st.metric("Workflow Type", results.get('workflow_type', 'N/A'))
    with col3:
        confidence = results.get('average_confidence', 0)
        st.metric("Confidence", f"{confidence:.1%}")
    
    # Agent results
    if "agent_results" in results:
        st.markdown("#### Agent Results")
        for agent_name, agent_result in results["agent_results"].items():
            with st.expander(f"{agent_name.replace('_', ' ').title()} Results"):
                st.json(agent_result)

def render_enhanced_company_analysis(company_data: Dict[str, Any]):
    """Render enhanced company analysis using Phase 2 capabilities"""
    st.markdown("### 🏢 Enhanced Company Analysis")
    
    if not company_data:
        st.info("Select a company to see enhanced analysis")
        return
    
    # Company overview
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Basic Information")
        st.write(f"**Company:** {company_data.get('Company Name', 'N/A')}")
        st.write(f"**Sector:** {company_data.get('Sector', 'N/A')}")
        st.write(f"**Risk Score:** {company_data.get('Risk Score', 'N/A')}")
    
    with col2:
        st.markdown("#### AI Analysis")
        st.info("🤖 AI-powered insights would appear here with real agents")
        
    # Phase 2 specific analysis
    if PHASE2_AVAILABLE:
        st.markdown("#### 🚀 Phase 2 Analysis")
        try:
            integration = Phase2Integration(use_real_agents=True)
            
            # Enhanced analysis placeholder
            st.success("✅ Real AI agents available for analysis")
            st.info("💡 Click 'Execute Workflow' to run comprehensive analysis")
            
        except Exception as e:
            st.warning(f"Phase 2 analysis not available: {e}")

def initialize_phase2_integration():
    """Initialize Phase 2 integration for Streamlit app"""
    if 'phase2_integration' not in st.session_state:
        st.session_state.phase2_integration = Phase2Integration(use_real_agents=True)
    
    return st.session_state.phase2_integration

# Additional render functions for Phase 2 controls
def render_phase2_sidebar_controls():
    """Render complete Phase 2 controls in sidebar"""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🚀 **Phase 2 Controls**")
    
    # Phase 2 availability status
    if PHASE2_AVAILABLE:
        st.sidebar.success("✅ Phase 2 Dependencies Available")
    else:
        st.sidebar.warning("⚠️ Phase 2 Dependencies Not Installed")
        st.sidebar.markdown("Run: `pip install -r requirements_phase2.txt`")
    
    # Real agents toggle
    use_real_agents = st.sidebar.checkbox(
        "🤖 Use Real Agents",
        value=False,
        disabled=not PHASE2_AVAILABLE,
        help="Toggle between mock and real LangGraph agents"
    )
    
    # API configuration status
    st.sidebar.markdown("#### 🔑 **API Configuration**")
    
    # Check API keys
    openai_key = os.getenv('OPENAI_API_KEY')
    companies_house_key = os.getenv('COMPANIES_HOUSE_API_KEY')
    
    st.sidebar.markdown(f"OpenAI API: {'✅' if openai_key else '❌'}")
    st.sidebar.markdown(f"Companies House API: {'✅' if companies_house_key else '❌'}")
    
    if not openai_key or not companies_house_key:
        st.sidebar.info("💡 Set API keys in environment variables for full functionality")
    
    return use_real_agents

# Export key functions
__all__ = [
    'Phase2Integration',
    'render_phase2_controls',
    'render_langgraph_visualization',
    'render_workflow_results',
    'render_enhanced_company_analysis',
    'render_phase2_sidebar_controls',
    'initialize_phase2_integration',
    'PHASE2_AVAILABLE'
]
