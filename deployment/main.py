"""
Main entry point for the Credit Risk Analysis Application
Production-ready Databricks-compliant structure
"""

import sys
import os
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

# Set up logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Main application entry point"""
    logger.info("Starting Credit Risk Analysis Application")
    
    # Import and run the Streamlit app
    try:
        from app.core.streamlit_app_langgraph_viz import main as streamlit_main
        streamlit_main()
    except ImportError as e:
        logger.error(f"Failed to import Streamlit app: {e}")
        raise
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise

if __name__ == "__main__":
    main()
