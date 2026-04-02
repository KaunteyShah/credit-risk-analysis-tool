/**
 * Resizable Panels JavaScript
 * Handles draggable separators for responsive panel layouts
 */

console.log('🔄 RESIZABLE PANELS JS LOADED - Version 20251108225000');

class ResizablePanels {
    constructor() {
        console.log('🏗️ RESIZABLE PANELS CONSTRUCTOR CALLED');
        this.isResizing = false;
        this.currentResizer = null;
        this.startX = 0;
        this.startY = 0;
        this.startWidth = 0;
        this.startHeight = 0;
        
        this.init();
    }
    
    init() {
        this.setupVerticalResizer();
        this.setupHorizontalResizer();
        
        // Prevent text selection during resize
        document.addEventListener('selectstart', (e) => {
            if (this.isResizing) {
                e.preventDefault();
            }
        });
    }
    
    setupVerticalResizer() {
        const verticalResizer = document.getElementById('vertical-resizer');
        const sidebar = document.getElementById('sidebar');
        const contentArea = document.getElementById('content-area');
        
        if (!verticalResizer || !sidebar || !contentArea) return;
        
        verticalResizer.addEventListener('mousedown', (e) => {
            this.isResizing = true;
            this.currentResizer = 'vertical';
            this.startX = e.clientX;
            this.startWidth = parseInt(getComputedStyle(sidebar).width, 10);
            
            document.body.classList.add('resizing-vertical');
            e.preventDefault();
        });
        
        document.addEventListener('mousemove', (e) => {
            if (!this.isResizing || this.currentResizer !== 'vertical') return;
            
            const width = this.startWidth + (e.clientX - this.startX);
            const minWidth = 250;
            const maxWidth = window.innerWidth * 0.4; // Max 40% of screen width
            
            if (width >= minWidth && width <= maxWidth) {
                sidebar.style.width = `${width}px`;
                // Update CSS variable for responsive behavior
                document.documentElement.style.setProperty('--sidebar-width', `${width}px`);
            }
        });
        
        document.addEventListener('mouseup', () => {
            if (this.currentResizer === 'vertical') {
                this.isResizing = false;
                this.currentResizer = null;
                document.body.classList.remove('resizing-vertical');
            }
        });
    }
    
    setupHorizontalResizer() {
        const horizontalResizer = document.getElementById('horizontal-resizer');
        const topPanel = document.querySelector('.split-panel-top');
        const bottomPanel = document.querySelector('.split-panel-bottom');
        
        console.log('🔧 Resizer setup:', {
            horizontalResizer: !!horizontalResizer,
            topPanel: !!topPanel,
            bottomPanel: !!bottomPanel
        });
        
        if (!horizontalResizer || !topPanel || !bottomPanel) {
            console.warn('❌ Resizer elements not found - panel resizing disabled');
            return;
        }
        
        horizontalResizer.addEventListener('mousedown', (e) => {
            this.isResizing = true;
            this.currentResizer = 'horizontal';
            this.startY = e.clientY;
            this.startHeight = parseInt(getComputedStyle(bottomPanel).height, 10);
            
            console.log('🔽 Starting horizontal resize:', {
                startY: this.startY,
                startHeight: this.startHeight
            });
            
            document.body.classList.add('resizing-horizontal');
            e.preventDefault();
        });
        
        document.addEventListener('mousemove', (e) => {
            if (!this.isResizing || this.currentResizer !== 'horizontal') return;
            
            console.log('🚀 RESIZE EVENT TRIGGERED - Panel resize in progress!');
            
            // CORRECT calculation: dragging UP increases height, dragging DOWN decreases height
            const height = this.startHeight - (e.clientY - this.startY);
            const minHeight = Math.max(200, window.innerHeight * 0.15);  // 15% of screen or 200px minimum
            const maxHeight = window.innerHeight * 0.7;  // Maximum 70% of available screen height
            
            // Debug logging
            console.log('📏 Resize calculation:', {
                startY: this.startY,
                currentY: e.clientY,
                deltaY: e.clientY - this.startY,
                startHeight: this.startHeight,
                newHeight: height,
                direction: (e.clientY - this.startY) < 0 ? 'UP (taller)' : 'DOWN (shorter)'
            });
            
            if (height >= minHeight && height <= maxHeight) {
                console.log(`✅ Height ${height}px is within valid range (${minHeight}-${maxHeight})`);
                
                // Use flex-based sizing instead of hardcoded pixels
                bottomPanel.style.flex = `0 0 ${height}px`;
                bottomPanel.style.minHeight = `${minHeight}px`;
                bottomPanel.style.maxHeight = `${maxHeight}px`;
                
                // Update tab content to use full available space
                const tabContent = bottomPanel.querySelector('.tab-content');
                if (tabContent) {
                    tabContent.style.height = `100%`;
                    tabContent.style.flex = `1`;
                    console.log('📂 Tab content using full flex space');
                }
                
                // DEBUG: Check what's in the bottom panel
                console.log('🔍 Searching for revenue panel elements...');
                console.log('Bottom panel:', bottomPanel);
                console.log('Revenue panel exists?', !!bottomPanel.querySelector('#revenue-panel'));
                
                // Update Revenue panel containers to match current panel height
                const revenuePanel = bottomPanel.querySelector('#revenue-panel');
                if (revenuePanel) {
                    console.log(`🎯 Found Revenue panel - updating containers for height: ${height}px`);
                    
                    // Update main Revenue containers (they use calc() heights that need to be refreshed)
                    const revenueAgentResults = revenuePanel.querySelector('.agent-results');
                    const revenueWorkflowContainer = revenuePanel.querySelector('.agent-workflow-container');
                    
                    if (revenueAgentResults) {
                        // Use flex-based sizing to fill available space with scrolling
                        revenueAgentResults.style.height = 'auto';
                        revenueAgentResults.style.flex = '1';
                        revenueAgentResults.style.display = 'flex';
                        revenueAgentResults.style.flexDirection = 'column';
                        revenueAgentResults.style.minHeight = '0';  // Enable scrolling in flex children
                        console.log(`🔷 Revenue agent-results using flex layout with scrolling`);
                    }
                    
                    if (revenueWorkflowContainer) {
                        // Use flex-based sizing to fill available space with scrolling
                        revenueWorkflowContainer.style.height = 'auto';
                        revenueWorkflowContainer.style.flex = '1';
                        revenueWorkflowContainer.style.display = 'flex';
                        revenueWorkflowContainer.style.flexDirection = 'column';
                        revenueWorkflowContainer.style.minHeight = '0';  // Enable scrolling in flex children
                        console.log(`🔷 Revenue workflow container using flex layout`);
                    }
                    
                    // Update results containers within Revenue panel to have proper scrolling
                    const revenueResultsContainers = revenuePanel.querySelectorAll('.results-container');
                    revenueResultsContainers.forEach(container => {
                        container.style.setProperty('height', 'calc(100% - 45px)', 'important');
                        container.style.setProperty('max-height', 'calc(100% - 45px)', 'important');
                        container.style.setProperty('overflow-y', 'auto', 'important');
                        container.style.setProperty('overflow-x', 'hidden', 'important');
                        console.log(`📋 Revenue results container updated with scrolling`);
                    });
                } else {
                    console.log(`⚠️ Revenue panel not found in current tab`);
                }
                
                // Update inner results containers (scrollable content areas) - use !important to override CSS
                const resultsContainers = bottomPanel.querySelectorAll('.results-container');
                resultsContainers.forEach(container => {
                    container.style.setProperty('height', `calc(100% - 10px)`, 'important');
                    container.style.setProperty('max-height', `calc(100% - 10px)`, 'important');
                    container.style.setProperty('overflow-y', 'auto', 'important');
                    console.log(`📋 Results container resized: ${container.id || container.className} → calc(100% - 10px) !important with scroll`);
                });
                
                // Update revenue modal heights dynamically
                const revenueModals = bottomPanel.querySelectorAll('.revenue-option-content, .modal-body, .card-body');
                console.log(`📏 Resizing ${revenueModals.length} modal elements to maxHeight: ${height - 150}px`);
                revenueModals.forEach((modal, index) => {
                    modal.style.maxHeight = `${height - 150}px`;
                    modal.style.overflowY = 'auto';
                    console.log(`  ✅ Modal ${index + 1}: ${modal.className} - height set to ${height - 150}px`);
                });
                
                // Target revenue options container specifically
                const revenueOptionsContainer = bottomPanel.querySelector('#revenueOptionsContainer');
                if (revenueOptionsContainer) {
                    revenueOptionsContainer.style.maxHeight = `${height - 200}px`;
                    revenueOptionsContainer.style.overflowY = 'auto';
                    console.log(`📦 Revenue options container resized to: ${height - 200}px`);
                }
                
                // Target individual revenue option cards  
                const revenueCards = bottomPanel.querySelectorAll('.col-md-4 > div, .revenue-option-card');
                revenueCards.forEach((card, index) => {
                    if (card.classList.contains('border') || card.classList.contains('rounded')) {
                        card.style.maxHeight = `${height - 250}px`;
                        card.style.overflowY = 'auto';
                        console.log(`  💳 Revenue card ${index + 1} resized to: ${height - 250}px`);
                    }
                });
            }
        });
        
        document.addEventListener('mouseup', () => {
            if (this.currentResizer === 'horizontal') {
                console.log('🔼 Finished horizontal resize');
                this.isResizing = false;
                this.currentResizer = null;
                document.body.classList.remove('resizing-horizontal');
            }
        });
    }
    
    // Public method to reset panels to default sizes
    resetToDefaults() {
        const sidebar = document.getElementById('sidebar');
        const bottomPanel = document.querySelector('.split-panel-bottom');
        
        if (sidebar) {
            sidebar.style.width = '';
            document.documentElement.style.setProperty('--sidebar-width', '300px');
        }
        
        if (bottomPanel) {
            bottomPanel.style.flexBasis = '';
            bottomPanel.style.height = '';
        }
    }
    
    // Public method to save current layout to localStorage
    saveLayout() {
        const sidebar = document.getElementById('sidebar');
        const bottomPanel = document.querySelector('.split-panel-bottom');
        
        const layout = {
            sidebarWidth: sidebar ? sidebar.style.width || '300px' : '300px',
            bottomPanelHeight: bottomPanel ? (bottomPanel.style.flex || 'auto') : 'auto'
        };
        
        localStorage.setItem('modular-panel-layout', JSON.stringify(layout));
    }
    
    // Public method to restore layout from localStorage
    restoreLayout() {
        const savedLayout = localStorage.getItem('modular-panel-layout');
        if (!savedLayout) return;
        
        try {
            const layout = JSON.parse(savedLayout);
            const sidebar = document.getElementById('sidebar');
            const bottomPanel = document.querySelector('.split-panel-bottom');
            
            if (sidebar && layout.sidebarWidth) {
                sidebar.style.width = layout.sidebarWidth;
                const width = parseInt(layout.sidebarWidth, 10);
                document.documentElement.style.setProperty('--sidebar-width', `${width}px`);
            }
            
            if (bottomPanel && layout.bottomPanelHeight && layout.bottomPanelHeight !== 'auto') {
                // Only restore if it's a specific size, otherwise let it be flexible
                bottomPanel.style.flex = `0 0 ${layout.bottomPanelHeight}`;
            }
        } catch (e) {
            console.warn('Failed to restore panel layout:', e);
        }
    }
}

// Initialize resizable panels when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('📋 DOM CONTENT LOADED - Initializing ResizablePanels');
    window.ResizablePanels = new ResizablePanels();
    console.log('✅ ResizablePanels instance created:', !!window.ResizablePanels);
    
    // ADD DEBUG FUNCTION TO MANUALLY TEST REVENUE PANEL TARGETING
    window.testRevenueResize = function() {
        const bottomPanel = document.querySelector('.split-panel-bottom');
        console.log('🧪 TESTING REVENUE RESIZE TARGETING');
        console.log('Bottom panel found:', !!bottomPanel);
        
        if (bottomPanel) {
            const revenuePanel = bottomPanel.querySelector('#revenue-panel');
            console.log('Revenue panel found:', !!revenuePanel);
            
            if (revenuePanel) {
                const revenueAgentResults = revenuePanel.querySelector('.agent-results');
                const revenueWorkflowContainer = revenuePanel.querySelector('.agent-workflow-container');
                
                console.log('Revenue containers found:', {
                    revenueAgentResults: !!revenueAgentResults,
                    revenueWorkflowContainer: !!revenueWorkflowContainer
                });
                
                if (revenueAgentResults) {
                    console.log('Current agent-results height:', getComputedStyle(revenueAgentResults).height);
                    revenueAgentResults.style.setProperty('height', '600px', 'important');
                    revenueAgentResults.style.setProperty('max-height', '600px', 'important');
                    console.log('Set agent-results height to 600px');
                }
                
                if (revenueWorkflowContainer) {
                    console.log('Current workflow-container height:', getComputedStyle(revenueWorkflowContainer).height);
                    revenueWorkflowContainer.style.setProperty('height', '600px', 'important');
                    revenueWorkflowContainer.style.setProperty('max-height', '600px', 'important');
                    console.log('Set workflow-container height to 600px');
                }
            }
        }
    };
    
    // Restore saved layout
    window.ResizablePanels.restoreLayout();
    
    // Save layout on page unload
    window.addEventListener('beforeunload', () => {
        window.ResizablePanels.saveLayout();
    });
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ResizablePanels;
}