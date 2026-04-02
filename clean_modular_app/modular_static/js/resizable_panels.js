/**
 * Resizable Panels JavaScript
 * Handles draggable separators for responsive panel layouts
 */

class ResizablePanels {
    constructor() {
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
        
        if (!horizontalResizer || !topPanel || !bottomPanel) return;
        
        horizontalResizer.addEventListener('mousedown', (e) => {
            this.isResizing = true;
            this.currentResizer = 'horizontal';
            this.startY = e.clientY;
            this.startHeight = parseInt(getComputedStyle(bottomPanel).height, 10);
            
            document.body.classList.add('resizing-horizontal');
            e.preventDefault();
        });
        
        document.addEventListener('mousemove', (e) => {
            if (!this.isResizing || this.currentResizer !== 'horizontal') return;
            
            const height = this.startHeight - (e.clientY - this.startY);
            const minHeight = 200;  // Minimum height for bottom panel
            const maxHeight = 600;  // Maximum height for bottom panel
            
            if (height >= minHeight && height <= maxHeight) {
                bottomPanel.style.flexBasis = `${height}px`;
                bottomPanel.style.height = `${height}px`;
                bottomPanel.style.minHeight = `${height}px`;
                
                // Update tab content height accordingly
                const tabContent = bottomPanel.querySelector('.tab-content');
                if (tabContent) {
                    tabContent.style.height = `calc(100% - 60px)`;
                }
            }
        });
        
        document.addEventListener('mouseup', () => {
            if (this.currentResizer === 'horizontal') {
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
            bottomPanelHeight: bottomPanel ? (bottomPanel.style.height || '350px') : '350px'
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
            
            if (bottomPanel && layout.bottomPanelHeight) {
                bottomPanel.style.flexBasis = layout.bottomPanelHeight;
                bottomPanel.style.height = layout.bottomPanelHeight;
            }
        } catch (e) {
            console.warn('Failed to restore panel layout:', e);
        }
    }
}

// Initialize resizable panels when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.ResizablePanels = new ResizablePanels();
    
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