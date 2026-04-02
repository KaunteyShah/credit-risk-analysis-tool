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
        // Call the backend to open DB Browser for SQLite
        fetch('/api/open-sqlite-browser', { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                console.log('✅ SQLite Browser opening...');
            } else {
                console.error('❌ Failed to open SQLite Browser:', data.error);
                alert('Failed to open SQLite Browser: ' + data.error);
            }
        })
        .catch(error => {
            console.error('❌ Error:', error);
            alert('Error opening SQLite Browser');
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
window.ModularCore = new ModularCore();

// Auto-initialize when DOM is ready
$(document).ready(function() {
    window.ModularCore.initialize();
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ModularCore;
}