/**
 * Modular Core JavaScript - Foundation for Modular Architecture Frontend
 * Handles API communication, component initialization, and architecture status
 */

class ModularCore {
    constructor() {
        this.baseApiUrl = '/api/modular';
        this.componentStatus = {};
        this.performanceMetrics = {
            apiCalls: [],
            averageResponseTime: 0
        };
        
        this.initialized = false;
        
        // Bind methods
        this.makeApiCall = this.makeApiCall.bind(this);
        this.updateComponentStatus = this.updateComponentStatus.bind(this);
    }

    /**
     * Initialize the modular core system
     */
    async initialize() {
        if (this.initialized) {
            console.log('🔄 ModularCore already initialized');
            return;
        }

        console.log('🚀 ModularCore: Initializing...');
        
        try {
            // Check architecture health (non-blocking)
            await this.checkArchitectureHealth();
            
            // Load component statistics (non-blocking)
            await this.loadComponentStats();
            
            // Initialize UI components
            this.initializeUIComponents();
            
            // Setup event listeners
            this.setupEventListeners();
            
            this.initialized = true;
            console.log('✅ ModularCore: Initialization complete!');
            
            // Hide error banner if initialization succeeds
            this.hideErrorBanner();
            
        } catch (error) {
            console.error('❌ ModularCore: Initialization failed:', error);
            
            // Continue with basic functionality even if some parts fail
            this.initialized = true;
            this.initializeUIComponents();
            this.setupEventListeners();
            
            console.log('⚠️ ModularCore: Running in degraded mode');
        }
    }

    /**
     * Make API calls to modular endpoints with performance tracking
     */
    async makeApiCall(endpoint, options = {}) {
        const startTime = performance.now();
        // Ensure proper URL construction - baseApiUrl already has leading slash
        const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
        const url = `${this.baseApiUrl}${cleanEndpoint}`;
        
        console.log(`🔧 URL Construction Debug:`);
        console.log(`  baseApiUrl: "${this.baseApiUrl}"`);
        console.log(`  endpoint: "${endpoint}"`);
        console.log(`  cleanEndpoint: "${cleanEndpoint}"`);
        console.log(`  final URL: "${url}"`);
        
        try {
            console.log(`📡 API Call: ${options.method || 'GET'} ${url}`);
            
            const defaultOptions = {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            };
            
            const response = await fetch(url, { ...defaultOptions, ...options });
            const endTime = performance.now();
            const responseTime = endTime - startTime;
            
            // Track performance
            this.performanceMetrics.apiCalls.push({
                endpoint,
                method: options.method || 'GET',
                responseTime,
                status: response.status,
                timestamp: new Date()
            });
            
            this.updateAverageResponseTime();
            
            if (!response.ok) {
                let errorMessage = response.statusText;
                try {
                    // Read response as text first to avoid "body stream already read" error
                    const responseText = await response.text();
                    try {
                        // Try to parse as JSON
                        const errorData = JSON.parse(responseText);
                        errorMessage = errorData.error || response.statusText;
                    } catch (parseError) {
                        // If JSON parsing fails, the response is probably HTML
                        console.error('❌ Non-JSON error response:', responseText.substring(0, 200));
                        errorMessage = `Server error: ${response.status} ${response.statusText}`;
                    }
                } catch (readError) {
                    console.error('❌ Failed to read error response:', readError);
                    errorMessage = `Server error: ${response.status} ${response.statusText}`;
                }
                throw new Error(`API Error: ${errorMessage}`);
            }
            
            // Read response as text first, then parse as JSON
            const responseText = await response.text();
            let data;
            try {
                data = JSON.parse(responseText);
            } catch (parseError) {
                console.error('❌ JSON Parse Error - Server returned HTML instead of JSON:', responseText.substring(0, 200));
                throw new Error('Server error: Expected JSON response but received HTML. Please check server logs.');
            }
            
            console.log(`✅ API Success: ${endpoint} (${responseTime.toFixed(1)}ms)`);
            
            return data;
            
        } catch (error) {
            const endTime = performance.now();
            const responseTime = endTime - startTime;
            
            this.performanceMetrics.apiCalls.push({
                endpoint,
                method: options.method || 'GET',
                responseTime,
                status: 'error',
                error: error.message,
                timestamp: new Date()
            });
            
            console.error(`❌ API Error: ${endpoint}`, error);
            throw error;
        }
    }

    /**
     * Check the health of the modular architecture
     */
    async checkArchitectureHealth() {
        try {
            const healthData = await this.makeApiCall('/health');
            
            this.componentStatus = {
                overall: 'healthy',
                components: healthData.components || {},
                data: healthData.data || {},
                timestamp: healthData.timestamp || new Date().toISOString()
            };
            
            this.updateComponentStatus();
            console.log('🏥 Architecture Health: All components operational');
            
        } catch (error) {
            console.warn('⚠️ Health check failed, continuing with degraded mode:', error.message);
            this.componentStatus = {
                overall: 'degraded',
                error: error.message,
                timestamp: new Date().toISOString()
            };
            
            this.updateComponentStatus();
            // Don't throw error - continue with degraded functionality
        }
    }

    /**
     * Load component statistics
     */
    async loadComponentStats() {
        try {
            const statsData = await this.makeApiCall('/stats');
            
            this.componentStats = statsData;
            this.updateStatsDisplay(statsData);
            console.log('📊 Component Stats loaded successfully');
            
        } catch (error) {
            console.error('📊 Failed to load component stats:', error);
        }
    }

    /**
     * Update component status in UI
     */
    updateComponentStatus() {
        const statusElement = document.getElementById('component-status');
        if (!statusElement) return;

        if (this.componentStatus.overall === 'healthy') {
            statusElement.innerHTML = `
                <i class="fas fa-check-circle"></i> 
                ${this.componentStatus.data?.companies_loaded || 0} Companies Loaded
            `;
            statusElement.className = 'badge bg-success';
        } else {
            statusElement.innerHTML = `
                <i class="fas fa-exclamation-triangle"></i> 
                Architecture Error
            `;
            statusElement.className = 'badge bg-danger';
        }
    }

    /**
     * Update statistics display
     */
    updateStatsDisplay(stats) {
        // Update API endpoint count
        const endpointCountElement = document.getElementById('api-endpoint-count');
        if (endpointCountElement) {
            endpointCountElement.textContent = stats.endpoints?.total_modular_endpoints || 0;
        }

        // Update average response time
        const responseTimeElement = document.getElementById('avg-response-time');
        if (responseTimeElement) {
            responseTimeElement.textContent = this.performanceMetrics.averageResponseTime.toFixed(0);
        }
    }

    /**
     * Update average response time calculation
     */
    updateAverageResponseTime() {
        const recentCalls = this.performanceMetrics.apiCalls.slice(-10); // Last 10 calls
        const totalTime = recentCalls.reduce((sum, call) => sum + call.responseTime, 0);
        this.performanceMetrics.averageResponseTime = recentCalls.length > 0 ? totalTime / recentCalls.length : 0;
        
        // Update UI
        const responseTimeElement = document.getElementById('avg-response-time');
        if (responseTimeElement) {
            responseTimeElement.textContent = this.performanceMetrics.averageResponseTime.toFixed(0);
        }
    }

    /**
     * Initialize UI components
     */
    initializeUIComponents() {
        // Initialize sidebar toggle
        this.initializeSidebarToggle();
        
        // Initialize loading states
        this.initializeLoadingStates();
        
        // Initialize tooltips
        this.initializeTooltips();
        
        console.log('🎨 UI Components initialized');
    }

    /**
     * Setup global event listeners
     */
    setupEventListeners() {
        // Sidebar toggle
        $(document).on('click', '#toggleFilters', () => {
            this.toggleSidebar();
        });

        // Database browser button
        $(document).on('click', '#openDatabase', () => {
            this.openSQLiteBrowser();
        });

        // VectorDB browser button
        $(document).on('click', '#openVectorDB', () => {
            this.openVectorSQLiteBrowser();
        });

        // Refresh buttons
        $(document).on('click', '#refreshData, .btn-refresh', () => {
            this.refreshAllData();
        });

        console.log('👂 Event listeners setup complete');
    }

    /**
     * Initialize sidebar toggle functionality
     */
    initializeSidebarToggle() {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            // Add toggle functionality
            window.ModularCore.toggleSidebar = () => {
                sidebar.classList.toggle('collapsed');
                
                // Update button icon
                const toggleBtn = document.getElementById('toggleFilters');
                if (toggleBtn) {
                    const icon = toggleBtn.querySelector('i');
                    if (sidebar.classList.contains('collapsed')) {
                        icon.className = 'fas fa-chevron-right';
                    } else {
                        icon.className = 'fas fa-filter';
                    }
                }
            };
        }
    }

    /**
     * Initialize loading states
     */
    initializeLoadingStates() {
        // Hide any existing loading modals
        $('.modal').modal('hide');
        $('.modal-backdrop').remove();
        $('body').removeClass('modal-open');
    }

    /**
     * Initialize tooltips
     */
    initializeTooltips() {
        // Bootstrap tooltips
        if (typeof bootstrap !== 'undefined') {
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        }
    }

    /**
     * Toggle sidebar visibility
     */
    toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            sidebar.classList.toggle('collapsed');
            
            // Update button icon
            const toggleBtn = document.getElementById('toggleFilters');
            if (toggleBtn) {
                const icon = toggleBtn.querySelector('i');
                if (sidebar.classList.contains('collapsed')) {
                    icon.className = 'fas fa-chevron-right';
                } else {
                    icon.className = 'fas fa-filter';
                }
            }
        }
    }

    /**
     * Refresh all data components
     */
    async refreshAllData() {
        console.log('🔄 Refreshing all data components...');
        
        try {
            // Show loading state
            this.showLoadingState();
            
            // Refresh architecture health
            await this.checkArchitectureHealth();
            
            // Refresh component stats
            await this.loadComponentStats();
            
            // Trigger refresh event for dashboard if it exists
            if (window.ModularDashboard) {
                await window.ModularDashboard.loadCompaniesData();
            }
            
            console.log('✅ All data refreshed successfully');
            this.showSuccessBanner('Data refreshed successfully');
            
        } catch (error) {
            console.error('❌ Failed to refresh data:', error);
            this.showErrorBanner('Failed to refresh data');
        } finally {
            this.hideLoadingState();
        }
    }

    /**
     * Show loading state
     */
    showLoadingState() {
        // Add loading class to body
        document.body.classList.add('loading');
        
        // Show loading indicators
        $('.spinner-border').show();
    }

    /**
     * Hide loading state
     */
    hideLoadingState() {
        // Remove loading class from body
        document.body.classList.remove('loading');
        
        // Hide loading indicators
        $('.spinner-border').hide();
    }

    /**
     * Show success banner
     */
    showSuccessBanner(message) {
        this.showBanner(message, 'success');
    }

    /**
     * Show error banner
     */
    showErrorBanner(message) {
        this.showBanner(message, 'danger');
    }

    /**
     * Show banner message
     */
    showBanner(message, type = 'info') {
        const banner = $(`
            <div class="alert alert-${type} alert-dismissible fade show position-fixed" 
                 style="top: 70px; right: 20px; z-index: 1050; max-width: 300px;">
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                ${message}
            </div>
        `);
        
        $('body').append(banner);
        
        // Auto-dismiss after 3 seconds
        setTimeout(() => {
            if (banner.length) {
                banner.fadeOut(() => banner.remove());
            }
        }, 3000);
    }

    /**
     * Hide error banner
     */
    hideErrorBanner() {
        $('.alert[style*="position-fixed"]').fadeOut(() => {
            $('.alert[style*="position-fixed"]').remove();
        });
    }

    /**
     * Open SQLite Browser application
     */
    openSQLiteBrowser() {
        // Show loading indicator
        const originalButton = document.querySelector('.view-database-btn');
        if (originalButton) {
            originalButton.textContent = 'Opening SQLite Browser...';
            originalButton.disabled = true;
        }

        // Call the backend to open DB Browser for SQLite
        fetch('/api/open-sqlite-browser', { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            // Reset button
            if (originalButton) {
                originalButton.textContent = 'View Database';
                originalButton.disabled = false;
            }

            if (data.status === 'success') {
                console.log('✅ SQLite Browser opening...');
                
                // Different handling for local vs Azure
                if (data.action === 'local_app_launched') {
                    alert(`✅ ${data.message}\n\nThe database file is located at:\n${data.database_path}`);
                } else {
                    alert(data.message || 'SQLite Browser is opening...');
                }
            
            } else if (data.status === 'ready') {
                console.log('✅ SQLite Browser container ready!');
                
                // Open the container URL in a new tab
                if (data.container_url) {
                    window.open(data.container_url, '_blank');
                    alert('SQLite Browser opened in new tab!\n\nURL: ' + data.container_url);
                } else {
                    alert(data.message || 'SQLite Browser container is ready!');
                }
                
            } else if (data.status === 'starting') {
                console.log('ℹ️ SQLite Browser container starting...');
                alert(data.message + (data.estimated_wait ? '\n\nEstimated wait: ' + data.estimated_wait : ''));
                
                // Check status after a delay
                setTimeout(() => this.checkSQLiteBrowserStatus(), 5000);
                
            } else if (data.status === 'info') {
                console.log('ℹ️ SQLite Browser info:', data.message);
                alert(data.message + (data.alternative ? '\n\nAlternative: ' + data.alternative : ''));
                
            } else {
                console.error('❌ Failed to open SQLite Browser:', data.error || data.message);
                alert('Failed to open SQLite Browser: ' + (data.error || data.message || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('❌ Error:', error);
            alert('Error opening SQLite Browser');
            
            // Reset button on error
            if (originalButton) {
                originalButton.textContent = 'View Database';
                originalButton.disabled = false;
            }
        });
    }

    openVectorSQLiteBrowser() {
        // Show loading indicator
        const originalButton = document.getElementById('openVectorDB');
        if (originalButton) {
            originalButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Opening Vector DB...';
            originalButton.disabled = true;
        }

        // Call the backend to open Vector DB Browser for SQLite
        fetch('/api/open-vector-sqlite-browser', { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            // Reset button
            if (originalButton) {
                originalButton.innerHTML = '<i class="fas fa-vector-square"></i> VectorDB';
                originalButton.disabled = false;
            }

            if (data.status === 'success') {
                console.log('✅ Vector SQLite Browser opening...');
                
                // Different handling for local vs Azure
                if (data.action === 'local_app_launched') {
                    alert(`✅ ${data.message}\n\nThe vector database file is located at:\n${data.database_path}`);
                } else {
                    alert(data.message || 'Vector SQLite Browser is opening...');
                }
            
            } else if (data.status === 'ready') {
                console.log('✅ Vector SQLite Browser container ready!');
                
                // Open the container URL in a new tab
                if (data.container_url) {
                    window.open(data.container_url, '_blank');
                    alert('Vector SQLite Browser opened in new tab!\n\nURL: ' + data.container_url);
                } else {
                    alert(data.message || 'Vector SQLite Browser container is ready!');
                }
                
            } else if (data.status === 'starting') {
                console.log('ℹ️ Vector SQLite Browser container starting...');
                alert(data.message + (data.estimated_wait ? '\n\nEstimated wait: ' + data.estimated_wait : ''));
                
            } else if (data.status === 'info') {
                console.log('ℹ️ Vector SQLite Browser info:', data.message);
                alert(data.message + (data.alternative ? '\n\nAlternative: ' + data.alternative : ''));
                
            } else {
                console.error('❌ Failed to open Vector SQLite Browser:', data.error || data.message);
                alert('Failed to open Vector SQLite Browser: ' + (data.error || data.message || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('❌ Error:', error);
            alert('Error opening Vector SQLite Browser');
            
            // Reset button on error
            if (originalButton) {
                originalButton.innerHTML = '<i class="fas fa-vector-square"></i> VectorDB';
                originalButton.disabled = false;
            }
        });
    }

    /**
     * Check SQLite Browser container status
     */
    checkSQLiteBrowserStatus() {
        fetch('/api/sqlite-browser-status')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (data.container_status === 'running' && data.container_url) {
                    console.log('✅ SQLite Browser container now ready!');
                    
                    // Ask user if they want to open it
                    const openNow = confirm('SQLite Browser container is now ready!\n\nWould you like to open it?');
                    if (openNow) {
                        window.open(data.container_url, '_blank');
                    }
                    
                } else if (data.container_status === 'starting') {
                    console.log('ℹ️ SQLite Browser container still starting...');
                    // Check again after another delay
                    setTimeout(() => this.checkSQLiteBrowserStatus(), 10000);
                    
                } else {
                    console.log('ℹ️ SQLite Browser container status:', data.container_status);
                }
            } else {
                console.error('❌ Error checking container status:', data.error);
            }
        })
        .catch(error => {
            console.error('❌ Error checking container status:', error);
        });
    }

    /**
     * Get performance metrics
     */
    getPerformanceMetrics() {
        return {
            ...this.performanceMetrics,
            componentStatus: this.componentStatus,
            initialized: this.initialized
        };
    }

    /**
     * Get component status
     */
    getComponentStatus() {
        return this.componentStatus;
    }
}

// Create and expose global instance
window.ModularCore = new ModularCore();

// Also create window.ModularDashboard when dashboard script loads
window.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 ModularCore ready for initialization');
});

// Auto-initialize when DOM is ready
$(document).ready(function() {
    window.ModularCore.initialize();
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ModularCore;
}