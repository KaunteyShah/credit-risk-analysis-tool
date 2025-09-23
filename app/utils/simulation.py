"""
Simulation and Demo Code Module

This module contains all simulation logic and random data generation
used for demonstration purposes. It can be enabled/disabled using the
DEMO_MODE environment variable.
"""

import os
import random
import time
import numpy as np
from typing import Dict, Any, List, Optional

# Demo mode flag - can be controlled via environment variable
DEMO_MODE = os.getenv('DEMO_MODE', 'true').lower() in ('true', '1', 'yes', 'on')

class SimulationService:
    """Service for generating simulation data and delays"""
    
    def __init__(self, seed: int = 42):
        """Initialize with optional random seed for reproducibility"""
        if DEMO_MODE:
            random.seed(seed)
            np.random.seed(seed)
    
    def generate_sic_accuracy(self, count: int) -> np.ndarray:
        """Generate random SIC accuracy values for demonstration"""
        if not DEMO_MODE:
            raise RuntimeError("Simulation methods only available in DEMO_MODE")
        
        return np.random.uniform(0.7, 0.99, count)
    
    def simulate_prediction_delay(self, min_delay: float = 0.5, max_delay: float = 1.5) -> None:
        """Simulate processing delay for realistic demo experience"""
        if DEMO_MODE:
            time.sleep(random.uniform(min_delay, max_delay))
    
    def generate_mock_sic_prediction(self) -> Dict[str, Any]:
        """Generate mock SIC prediction result"""
        if not DEMO_MODE:
            raise RuntimeError("Simulation methods only available in DEMO_MODE")
        
        mock_sics = ['2834', '3571', '7372', '5045', '6282']
        return {
            'predicted_sic': random.choice(mock_sics),
            'confidence': random.uniform(0.75, 0.95),
            'timestamp': time.time()
        }
    
    def generate_mock_revenue_update(self, current_revenue: Optional[float] = None) -> Dict[str, Any]:
        """Generate mock revenue update"""
        if not DEMO_MODE:
            raise RuntimeError("Simulation methods only available in DEMO_MODE")
        
        if current_revenue and current_revenue > 0:
            # Vary existing revenue by 10%
            variation = random.uniform(0.9, 1.1)
            new_revenue = current_revenue * variation
        else:
            # Generate completely new revenue
            new_revenue = random.uniform(100000, 50000000)
        
        return {
            'new_revenue': new_revenue,
            'confidence': random.uniform(0.8, 0.95),
            'source': 'simulation',
            'timestamp': time.time()
        }
    
    def simulate_workflow_processing(self, min_delay: float = 0.3, max_delay: float = 1.0) -> None:
        """Simulate workflow processing delay"""
        if DEMO_MODE:
            time.sleep(random.uniform(min_delay, max_delay))
    
    def is_demo_mode(self) -> bool:
        """Check if demo mode is enabled"""
        return DEMO_MODE
    
    def require_demo_mode(self) -> None:
        """Raise error if not in demo mode"""
        if not DEMO_MODE:
            raise RuntimeError("This operation is only available in DEMO_MODE")

# Global simulation service instance
simulation_service = SimulationService()

def get_simulation_service() -> SimulationService:
    """Get the global simulation service instance"""
    return simulation_service

def is_demo_mode() -> bool:
    """Check if demo mode is enabled globally"""
    return DEMO_MODE

def demo_mode_only(func):
    """Decorator to restrict functions to demo mode only"""
    def wrapper(*args, **kwargs):
        if not DEMO_MODE:
            raise RuntimeError(f"Function {func.__name__} is only available in DEMO_MODE")
        return func(*args, **kwargs)
    return wrapper

# Demo data constants
DEMO_SECRET_KEY = 'credit-risk-analysis-demo-key'
DEMO_SIC_CODES = ['2834', '3571', '7372', '5045', '6282']
DEMO_COMPANY_LIMIT = 5  # Limit processing to 5 companies in demo mode

if __name__ == "__main__":
    # Test the simulation service
    sim = SimulationService()
    
    if is_demo_mode():
        print("Demo mode is enabled")
        print(f"Sample SIC prediction: {sim.generate_mock_sic_prediction()}")
        print(f"Sample revenue update: {sim.generate_mock_revenue_update(500000)}")
    else:
        print("Demo mode is disabled")