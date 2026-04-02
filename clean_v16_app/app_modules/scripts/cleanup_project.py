#!/usr/bin/env python3
"""
Comprehensive Project Cleanup Script

This script removes temporary files, test files, and other clutter from the project
while preserving the core application structure and important files.

Usage: python cleanup_project.py [--dry-run] [--aggressive]
"""

import os
import shutil
import glob
from pathlib import Path
from typing import List, Set
import argparse
import subprocess

# Files and directories to ALWAYS keep (core application)
KEEP_FILES = {
    'main.py',
    'startup.py',
    'Dockerfile', 
    'requirements-dev.txt',
    'README.md',
    '.gitignore',
    '.dockerignore',
    '.zipignore'
}

KEEP_DIRS = {
    'app_modules',
    'modular_static', 
    'modular_templates',
    'data',
    'config',
    'docs',
    'tests',  # Keep organized test directory
    'logs',   # Keep for debugging
    '.git',
    '.github',
    '.azure',
    '.vscode'
}

# Patterns for files to remove
REMOVE_PATTERNS = [
    # Test files scattered in root
    'test_*.py',
    'debug_*.py', 
    'demo_*.py',
    'verify_*.py',
    'analyze_*.py',
    'clean_*.py',
    'fix_*.py',
    'migrate_*.py',
    'monitor_*.py',
    'optimization_*.py',
    'performance_*.py',
    'diagnose_*.py',
    'final_*.py',
    'create_*.py',
    'reprocess_*.py',
    
    # Temporary and generated files
    '*.log',
    '*_status*.py',
    '*_success*.py',
    '*_summary*.py',
    'api_response.json',
    'revenue_response.json',
    '*.html',  # test HTML files
    
    # Python cache
    '__pycache__',
    '*.pyc',
    '*.pyo',
    '*.pyd',
    '.pytest_cache',
    
    # OS files
    '.DS_Store',
    '*.tmp',
    '*.temp',
    
    # Backup directories
    'backups',
    'checkpoints'
]

# Markdown files to remove (keeping only README.md)
REMOVE_MD_PATTERNS = [
    '*_COMPLETE*.md',
    '*_SUMMARY*.md', 
    '*_ANALYSIS*.md',
    '*_STATUS*.md',
    '*_IMPLEMENTATION*.md',
    '*_RESOLUTION*.md',
    '*_FIX*.md',
    'CHUNK_LIMIT*.md',
    'CORRECTED_*.md',
    'COST_*.md',
    'ENHANCED_*.md',
    'GAAP_*.md',
    'JAVASCRIPT_*.md',
    'OCR_*.md',
    'OPENAI_*.md',
    'OPTIMIZED_*.md',
    'QA_*.md',
    'REVENUE_*.md',
    'TEST_*.md',
    'TIMEOUT_*.md'
]

class ProjectCleaner:
    def __init__(self, project_root: Path, dry_run: bool = False, aggressive: bool = False):
        self.project_root = project_root
        self.dry_run = dry_run
        self.aggressive = aggressive
        self.removed_files: List[Path] = []
        self.removed_dirs: List[Path] = []
        
    def log(self, message: str):
        """Log cleanup actions"""
        prefix = "[DRY RUN] " if self.dry_run else ""
        print(f"{prefix}{message}")
        
    def should_keep_file(self, file_path: Path) -> bool:
        """Check if a file should be kept"""
        # Always keep certain files
        if file_path.name in KEEP_FILES:
            return True
            
        # Keep files in protected directories
        for keep_dir in KEEP_DIRS:
            if keep_dir in file_path.parts:
                return True
                
        return False
        
    def should_keep_dir(self, dir_path: Path) -> bool:
        """Check if a directory should be kept"""
        return dir_path.name in KEEP_DIRS
        
    def remove_file_patterns(self):
        """Remove files matching cleanup patterns"""
        for pattern in REMOVE_PATTERNS:
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file() and not self.should_keep_file(file_path):
                    self.log(f"Removing file: {file_path}")
                    if not self.dry_run:
                        file_path.unlink()
                    self.removed_files.append(file_path)
                elif file_path.is_dir() and not self.should_keep_dir(file_path):
                    self.log(f"Removing directory: {file_path}")
                    if not self.dry_run:
                        shutil.rmtree(file_path)
                    self.removed_dirs.append(file_path)
                    
    def remove_markdown_files(self):
        """Remove temporary markdown files"""
        for pattern in REMOVE_MD_PATTERNS:
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file() and not self.should_keep_file(file_path):
                    self.log(f"Removing markdown: {file_path}")
                    if not self.dry_run:
                        file_path.unlink()
                    self.removed_files.append(file_path)
                    
    def clean_python_cache(self):
        """Remove Python cache files recursively"""
        for pycache_dir in self.project_root.rglob('__pycache__'):
            if pycache_dir.is_dir():
                self.log(f"Removing Python cache: {pycache_dir}")
                if not self.dry_run:
                    shutil.rmtree(pycache_dir)
                self.removed_dirs.append(pycache_dir)
                
        # Remove .pyc files
        for pyc_file in self.project_root.rglob('*.pyc'):
            if pyc_file.is_file():
                self.log(f"Removing .pyc file: {pyc_file}")
                if not self.dry_run:
                    pyc_file.unlink()
                self.removed_files.append(pyc_file)
                
    def update_gitignore(self):
        """Update .gitignore to prevent files from coming back"""
        gitignore_path = self.project_root / '.gitignore'
        
        # Additional entries to prevent test files from coming back
        additional_entries = [
            "",
            "# === PREVENT TEMPORARY FILES FROM COMING BACK ===",
            "",
            "# Test files in root directory (move to tests/ instead)",
            "test_*.py",
            "debug_*.py",
            "demo_*.py", 
            "verify_*.py",
            "analyze_*.py",
            "clean_*.py",
            "fix_*.py",
            "migrate_*.py",
            "monitor_*.py",
            "optimization_*.py",
            "performance_*.py",
            "diagnose_*.py",
            "final_*.py",
            "create_*.py",
            "reprocess_*.py",
            "",
            "# Temporary status and summary files",
            "*_status*.py",
            "*_success*.py", 
            "*_summary*.py",
            "",
            "# Temporary markdown files",
            "*_COMPLETE*.md",
            "*_SUMMARY*.md",
            "*_ANALYSIS*.md", 
            "*_STATUS*.md",
            "*_IMPLEMENTATION*.md",
            "*_RESOLUTION*.md",
            "*_FIX*.md",
            "CHUNK_LIMIT*.md",
            "CORRECTED_*.md",
            "COST_*.md",
            "ENHANCED_*.md",
            "GAAP_*.md",
            "JAVASCRIPT_*.md",
            "OCR_*.md",
            "OPENAI_*.md",
            "OPTIMIZED_*.md",
            "QA_*.md",
            "REVENUE_*.md", 
            "TEST_*.md",
            "TIMEOUT_*.md",
            "",
            "# Backup and checkpoint directories",
            "backups/",
            "checkpoints/",
            "",
            "# Temporary HTML files", 
            "test_*.html",
            "debug_*.html",
            "",
            "# Flask log files",
            "flask*.log",
            ""
        ]
        
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                current_content = f.read()
                
            # Check if we've already added our section
            if "PREVENT TEMPORARY FILES FROM COMING BACK" not in current_content:
                self.log("Updating .gitignore to prevent temporary files")
                if not self.dry_run:
                    with open(gitignore_path, 'a') as f:
                        f.write('\n'.join(additional_entries))
                        
    def organize_remaining_tests(self):
        """Move any remaining test files to tests/ directory"""
        tests_dir = self.project_root / 'tests'
        if not tests_dir.exists() and not self.dry_run:
            tests_dir.mkdir()
            
        # Look for test files that weren't removed (in subdirectories)
        for test_file in self.project_root.rglob('test_*.py'):
            if 'tests/' not in str(test_file) and test_file.parent == self.project_root:
                target = tests_dir / test_file.name
                self.log(f"Moving test file to tests/: {test_file} -> {target}")
                if not self.dry_run and test_file.exists():
                    shutil.move(str(test_file), str(target))
                    
    def clean_utilities_dir(self):
        """Clean up utilities directory if it exists"""
        utilities_dir = self.project_root / 'utilities'
        if utilities_dir.exists() and utilities_dir.is_dir():
            # Check if it's mostly empty or contains only temporary files
            files = list(utilities_dir.glob('*'))
            if len(files) == 0 or all(f.name.startswith(('test_', 'debug_', 'temp_')) for f in files):
                self.log(f"Removing empty/temporary utilities directory")
                if not self.dry_run:
                    shutil.rmtree(utilities_dir)
                self.removed_dirs.append(utilities_dir)
                
    def run_cleanup(self):
        """Run the complete cleanup process"""
        self.log(f"Starting cleanup of: {self.project_root}")
        self.log(f"Mode: {'DRY RUN' if self.dry_run else 'ACTUAL CLEANUP'}")
        
        # 1. Remove file patterns
        self.log("\n=== Removing temporary files ===")
        self.remove_file_patterns()
        
        # 2. Remove markdown files
        self.log("\n=== Removing temporary markdown files ===")
        self.remove_markdown_files()
        
        # 3. Clean Python cache
        self.log("\n=== Cleaning Python cache ===")
        self.clean_python_cache()
        
        # 4. Clean utilities if needed
        self.log("\n=== Cleaning utilities directory ===")
        self.clean_utilities_dir()
        
        # 5. Organize remaining tests
        self.log("\n=== Organizing test files ===")
        self.organize_remaining_tests()
        
        # 6. Update gitignore
        self.log("\n=== Updating .gitignore ===")
        self.update_gitignore()
        
        # 7. Summary
        self.log(f"\n=== CLEANUP SUMMARY ===")
        self.log(f"Files removed: {len(self.removed_files)}")
        self.log(f"Directories removed: {len(self.removed_dirs)}")
        
        if self.dry_run:
            self.log("\nThis was a DRY RUN. Run without --dry-run to perform actual cleanup.")
        else:
            self.log("\nCleanup completed! Your project is now organized.")

def main():
    parser = argparse.ArgumentParser(description="Clean up the project directory")
    parser.add_argument('--dry-run', action='store_true', 
                      help='Show what would be removed without actually removing')
    parser.add_argument('--aggressive', action='store_true',
                      help='More aggressive cleanup (use with caution)')
    
    args = parser.parse_args()
    
    project_root = Path(__file__).parent
    cleaner = ProjectCleaner(project_root, dry_run=args.dry_run, aggressive=args.aggressive)
    cleaner.run_cleanup()

if __name__ == "__main__":
    main()