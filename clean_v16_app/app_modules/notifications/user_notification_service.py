"""
Real-Time User Notification System for Agentic Workflow
Provides comprehensive user feedback with progress bars and status updates
"""

import time
import sys
from typing import Optional, Any
from datetime import datetime


class UserNotificationService:
    """Real-time user notification service with progress bars and status updates."""
    
    def __init__(self):
        """Initialize notification service."""
        self.current_operation = ""
        self.start_time = None
        self.total_steps = 0
        self.current_step = 0
        
    def start_operation(self, operation_name: str, total_steps: int = 100):
        """Start a new operation with user notification."""
        self.current_operation = operation_name
        self.total_steps = total_steps
        self.current_step = 0
        self.start_time = time.time()
        
        print(f"\n🚀 Starting: {operation_name}")
        print("=" * 60)
        print("⏱️  This may take around 5-8 minutes for document processing and vectorization")
        print("📊 Progress will be shown below:")
        print()
        
    def update_progress(self, step: int, message: str, details: Optional[str] = None):
        """Update progress with real-time feedback."""
        self.current_step = step
        percentage = (step / self.total_steps) * 100
        
        # Create progress bar
        bar_length = 40
        filled_length = int(bar_length * step // self.total_steps)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        # Calculate elapsed time
        elapsed = time.time() - self.start_time if self.start_time else 0
        elapsed_str = f"{elapsed:.1f}s"
        
        # Print progress update
        print(f"\r[{bar}] {percentage:6.1f}% | {elapsed_str} | {message}", end="")
        
        if details:
            print(f"\n   └── {details}")
            
        sys.stdout.flush()
        
    def show_embedding_notification(self, document_name: str, page_count: int):
        """Show specific notification about document embedding process."""
        print(f"\n📄 Document Analysis Starting: {document_name}")
        print(f"📋 Document Size: {page_count} pages")
        print("🔄 Starting vectorization process...")
        print("   ├── Step 1: OCR text extraction (2-3 minutes)")
        print("   ├── Step 2: Text chunking and preprocessing (30 seconds)")  
        print("   ├── Step 3: Vector embedding generation (2-3 minutes)")
        print("   └── Step 4: Vector database storage (30 seconds)")
        print("\n⏳ Please wait while the document is being processed...")
        print("💡 The document will be available for RAG queries once processing completes")
        print()
        
    def show_completion(self, success: bool = True, result_summary: Optional[str] = None):
        """Show operation completion notification."""
        elapsed = time.time() - self.start_time if self.start_time else 0
        elapsed_str = f"{elapsed:.1f}s"
        
        print(f"\n\n{'✅' if success else '❌'} Operation Complete!")
        print(f"⏱️  Total Time: {elapsed_str}")
        
        if result_summary:
            print(f"📊 Result: {result_summary}")
            
        if success:
            print("🎉 The document has been successfully vectorized and is ready for RAG queries!")
        else:
            print("⚠️  There were issues during processing. Please check the logs.")
            
        print("=" * 60)
        print()
        
    def show_vector_db_status(self, is_clean: bool, existing_count: int = 0):
        """Show vector database status."""
        if is_clean:
            print("🗄️  Vector Database: Clean (no existing vectors)")
            print("📝 All documents will be processed and vectorized from scratch")
        else:
            print(f"🗄️  Vector Database: Contains {existing_count} existing vectors")
            print("📝 Checking for existing document vectors before processing")
        print()
        
    def show_error(self, error_message: str, suggestion: Optional[str] = None):
        """Show error notification with helpful suggestions."""
        print(f"\n❌ Error: {error_message}")
        
        if suggestion:
            print(f"💡 Suggestion: {suggestion}")
            
        print("🔧 Please check the logs for more details")
        print()


# Global notification service instance
notification_service = UserNotificationService()