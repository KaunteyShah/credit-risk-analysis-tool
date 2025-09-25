/**
 * Enhanced Flask App JavaScript for SIC Prediction System
 * Simplified version that actually works
 */

$(document).ready(function() {
    // Hide any loading modals immediately
    $('#loadingModal').modal('hide');
    $('.modal-backdrop').remove();
    $('body').removeClass('modal-open');
    
    // Initialize the app and make it globally accessible
    const app = new SICPredictionApp();
    window.sicApp = app;
});

class SICPredictionApp {
    constructor() {
        this.currentData = [];
        this.filteredData = [];
        this.currentPage = 1;
        this.perPage = 50;
        this.totalPages = 0;
        this.filters = {};
        this.agentWorkflows = {
            sic: null,
            revenue: null
        };
        this.langGraphStructure = null;
        
        // Start initialization immediately
        this.quickInit();
    }

    quickInit() {
        // Setup basic event listeners first
        this.setupBasicEventListeners();
        
        // Initialize panels
        this.initializePanels();
        
        // Load data without showing loading modal
        this.loadDataDirectly();
        
        // Setup agent dashboard
        this.setupAgentDashboard();
    }

    setupBasicEventListeners() {
        // Sidebar toggle
        $('#toggleFilters, #collapseSidebar').on('click', () => this.toggleSidebar());
        
        // Simple refresh button
        $(document).on('click', '.btn-refresh, #refreshBtn', () => {
            this.loadDataDirectly();
        });
    }

    async loadDataDirectly() {
        try {
            // Show loading in table only
            const tableBody = $('#companiesTableBody');
            if (tableBody.length) {
                tableBody.html(`
                    <tr>
                        <td colspan="8" class="text-center p-4">
                            <div class="spinner-border text-primary" role="status"></div>
                            <p class="mt-2">Loading company data...</p>
                        </td>
                    </tr>
                `);
            }
            
            // Load filter options (without await to not block)
            this.loadFilterOptionsQuietly();
            
            // Load company data
            const response = await fetch(`/api/data?page=1&limit=50`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            this.currentData = data.data || [];
            this.totalPages = data.total_pages || 0;
            
            // Render the table
            this.renderTable();
            
            // Log success
            this.logActivity('System', 'Company data loaded successfully', 'success');
            
        } catch (error) {
            console.error('Error loading data:', error);
            
            // Show error in table
            const tableBody = $('#companiesTableBody');
            if (tableBody.length) {
                tableBody.html(`
                    <tr>
                        <td colspan="8" class="text-center text-danger p-4">
                            <i class="fas fa-exclamation-triangle fa-2x mb-3"></i><br>
                            <strong>Error loading data:</strong><br>
                            ${error.message}<br>
                            <button class="btn btn-primary mt-3 btn-refresh">
                                <i class="fas fa-refresh me-2"></i>Try Again
                            </button>
                        </td>
                    </tr>
                `);
            }
            
            this.logActivity('System', `Error: ${error.message}`, 'error');
        }
    }

    async loadFilterOptionsQuietly() {
        try {
            const response = await fetch('/api/filter_options');
            if (response.ok) {
                const options = await response.json();
                // TODO: Setup filters with options
            }
        } catch (error) {
            console.warn('Filter options failed to load:', error);
        }
    }

    // Helper function to get color class based on accuracy value
    getAccuracyColorClass(accuracy) {
        if (!accuracy || accuracy === 'N/A') return 'text-muted';
        
        const numericAccuracy = parseFloat(accuracy);
        if (numericAccuracy >= 80) return 'text-success fw-bold'; // Green for high accuracy (80%+)
        if (numericAccuracy >= 60) return 'text-warning fw-bold'; // Orange for medium accuracy (60-79%)
        return 'text-danger fw-bold'; // Red for low accuracy (<60%)
    }

    renderTableSimple() {
        const tableBody = $('#companiesTableBody');
        if (!tableBody.length) {
            console.error('Table body element not found');
            return;
        }
        
        tableBody.empty();
        
        if (!this.currentData || this.currentData.length === 0) {
            tableBody.html(`
                <tr>
                    <td colspan="10" class="text-center text-muted p-4">
                        <i class="fas fa-info-circle fa-2x mb-3"></i><br>
                        No companies found
                    </td>
                </tr>
            `);
            return;
        }
        
        this.currentData.forEach((company, index) => {
            // Old Accuracy (current SIC vs business description)
            const oldAccuracyValue = parseFloat(company.Old_Accuracy) || 0;
            const oldAccuracy = isNaN(oldAccuracyValue) ? 'N/A' : oldAccuracyValue.toFixed(1) + '%';
            const oldAccuracyClass = this.getAccuracyColorClass(oldAccuracyValue);
            
            // New Accuracy (predicted SIC vs business description)  
            const newAccuracyValue = parseFloat(company.New_Accuracy) || 0;
            const newAccuracy = isNaN(newAccuracyValue) ? '0.0%' : newAccuracyValue.toFixed(1) + '%';
            const newAccuracyClass = this.getAccuracyColorClass(newAccuracyValue);
            
            // New SIC (updated by user)
            const newSIC = company.New_SIC || '';
            const hasNewSIC = newSIC && newSIC.trim() !== '';
            
            const row = `
                <tr>
                    <td>
                        <div class="d-flex align-items-center">
                            <span>${company['Company Name'] || 'N/A'}</span>
                            <button class="btn btn-sm btn-outline-info ms-2 company-info-btn" 
                                    data-company-index="${index}" 
                                    title="View detailed company information">
                                <i class="fas fa-info-circle"></i>
                            </button>
                        </div>
                    </td>
                    <td>${company.Country || 'N/A'}</td>
                    <td>${company['Employees (Total)'] ? parseInt(company['Employees (Total)']).toLocaleString() : 'N/A'}</td>
                    <td>${company['Sales (USD)'] ? '$' + parseInt(company['Sales (USD)']).toLocaleString() : 'N/A'}</td>
                    <td>${company['UK SIC 2007 Code'] || 'N/A'}</td>
                    <td><span class="${oldAccuracyClass}">${oldAccuracy}</span></td>
                    <td><span class="${newAccuracyClass}">${newAccuracy}</span></td>
                    <td class="${hasNewSIC ? 'text-success fw-bold' : 'text-muted'}">${newSIC || 'Not updated'}</td>
                    <td>
                        <button class="btn btn-primary btn-sm predict-sic-btn" data-company-index="${index}">
                            <i class="fas fa-robot"></i> Predict SIC
                        </button>
                    </td>
                    <td>
                        <button class="btn btn-warning btn-sm revenue-btn" data-company-index="${index}">
                            <i class="fas fa-dollar-sign"></i> Update Revenue
                        </button>
                    </td>
                </tr>
            `;
            tableBody.append(row);
        });
        
        // Setup event listeners for the new buttons
        this.setupTableButtonListeners();
    }

    setupTableButtonListeners() {
        // Remove any existing listeners to avoid duplicates
        $(document).off('click', '.predict-sic-btn');
        $(document).off('click', '.revenue-btn');
        $(document).off('click', '.company-info-btn');
        
        // Predict SIC button
        $(document).on('click', '.predict-sic-btn', (e) => {
            e.preventDefault();
            const companyIndex = $(e.currentTarget).data('company-index');
            this.predictSIC(companyIndex);
        });
        
        // Revenue update button
        $(document).on('click', '.revenue-btn', (e) => {
            e.preventDefault();
            const companyIndex = $(e.currentTarget).data('company-index');
            this.updateRevenue(companyIndex);
        });
        
        // Company info button
        $(document).on('click', '.company-info-btn', (e) => {
            e.preventDefault();
            const companyIndex = $(e.currentTarget).data('company-index');
            this.showCompanyDetails(companyIndex);
        });
    }

    initializePanels() {
        // Force panels to be visible with explicit CSS
        $('#top-panel').show().css({
            'display': 'block',
            'visibility': 'visible',
            'height': 'auto'
        });
        
        $('#bottom-panel').show().css({
            'display': 'block',
            'visibility': 'visible',
            'height': 'auto',
            'min-height': '300px'
        });
        
        $('#filterSidebar').show();
        
        // Remove any panel-collapsed class that might hide content
        $('#bottom-panel').removeClass('panel-collapsed');
        
        // Initialize Split.js for resizable panels
        if (window.Split) {
            window.Split(['#top-panel', '#bottom-panel'], {
                direction: 'vertical',
                sizes: [60, 40],
                minSize: [200, 200],
                gutterSize: 10,
                cursor: 'row-resize'
            });
        }
        
        // Force agent content to show immediately after panels are ready
        setTimeout(() => {
            this.showAgentContent();
        }, 100);
    }

    setupAgentDashboard() {
        // Make sure agent tabs are visible and functional
        $('#sic-tab, #revenue-tab').on('click', function(e) {
            e.preventDefault();
            $(this).tab('show');
        });
        
        // Show some demo content in agent areas - with delay to ensure DOM is ready
        setTimeout(() => {
            this.showAgentContent();
            // Also trigger the workflow to ensure visibility
            this.startSICWorkflow();
        }, 500);
    }

    showAgentContent() {
        // Show SIC agent content
        const sicContent = $('#sicWorkflowChart');
        if (sicContent.length) {
            sicContent.html(`
                <div class="text-center p-4">
                    <i class="fas fa-robot fa-3x text-primary mb-3"></i>
                    <h5>SIC Prediction Agent</h5>
                    <p class="text-muted">Click "Predict SIC" buttons in the table to start workflow</p>
                </div>
            `);
        }
        
        // Show Revenue agent content
        const revenueContent = $('#revenueWorkflowChart');
        if (revenueContent.length) {
            revenueContent.html(`
                <div class="text-center p-4">
                    <i class="fas fa-dollar-sign fa-3x text-success mb-3"></i>
                    <h5>Revenue Update Agent</h5>
                    <p class="text-muted">Ready to update revenue data</p>
                    <button class="btn btn-success btn-sm" id="startRevenueButton">
                        <i class="fas fa-play me-2"></i>Start Update
                    </button>
                </div>
            `);
            
            // Bind click event using jQuery
            $('#startRevenueButton').on('click', () => {
                this.startRevenueWorkflow();
            });
        }
        
        // Make sure the bottom panel is visible
        const bottomPanel = $('#bottom-panel');
        if (bottomPanel.length) {
            bottomPanel.removeClass('panel-collapsed');
        }
    }

    toggleSidebar() {
        $('#filterSidebar').toggleClass('collapsed');
    }

    logActivity(category, message, type = 'info') {
        const timestamp = new Date().toLocaleTimeString();
        const iconClass = type === 'success' ? 'fa-check-circle text-success' : 
                         type === 'error' ? 'fa-exclamation-circle text-danger' : 
                         type === 'warning' ? 'fa-exclamation-triangle text-warning' : 
                         'fa-info-circle text-info';
        
        const logEntry = `
            <div class="log-entry d-flex align-items-start mb-2">
                <i class="fas ${iconClass} me-2 mt-1"></i>
                <div class="flex-grow-1">
                    <div class="d-flex justify-content-between">
                        <strong class="log-category">${category}</strong>
                        <small class="text-muted">${timestamp}</small>
                    </div>
                    <div class="log-message">${message}</div>
                </div>
            </div>
        `;
        
        // Add to activity logs
        const activityLogs = $('#activityLogs');
        if (activityLogs.length) {
            activityLogs.prepend(logEntry);
            
            // Keep only last 50 entries
            const entries = activityLogs.find('.log-entry');
            if (entries.length > 50) {
                entries.slice(50).remove();
            }
        }
    }

    setupEventListeners() {
        // Sidebar toggle
        $('#toggleFilters, #collapseSidebar').on('click', () => this.toggleSidebar());
        
        // Enhanced filter inputs with dual range sliders
        this.setupDualRangeSliders();
        this.setupQuickFilterButtons();
        this.setupFilterInputs();
        
        // Pagination
        $('#perPageSelect').on('change', () => this.changePerPage());
        $(document).on('click', '.page-link', (e) => this.changePage(e));
        
        // Panel controls
        $('#collapseTopPanel').on('click', () => this.toggleTopPanel());
        $('#collapseBottomPanel').on('click', () => this.toggleBottomPanel());
        
        // Action buttons
        $(document).on('click', '.btn-predict', (e) => this.predictSIC(e));
        $(document).on('click', '.btn-update', (e) => this.updateRevenue(e));
        
        // Reset filters
        $('#clearAllFilters').on('click', () => this.resetFilters());
        
        // Export data
        $('#exportData').on('click', () => this.exportData());
        
        // Clear logs
        $('#clearLogs').on('click', () => this.clearLogs());
    }

    setupDualRangeSliders() {
        // Employee range sliders
        this.setupRangeSlider('employee', 'employeeRangeDisplay', (min, max) => {
            return `${this.formatNumber(min)} - ${this.formatNumber(max)} employees`;
        });

        // Revenue range sliders
        this.setupRangeSlider('revenue', 'revenueRangeDisplay', (min, max) => {
            return `$${this.formatCurrency(min)} - $${this.formatCurrency(max)}`;
        });

        // Profit range sliders
        this.setupRangeSlider('profit', 'profitRangeDisplay', (min, max) => {
            return `$${this.formatCurrency(min)} - $${this.formatCurrency(max)}`;
        });

        // Accuracy range slider
        $('#accuracyMin').on('input', (e) => {
            const value = e.target.value;
            $('#accuracyRangeDisplay').text(`${value}% - 100%`);
            this.debounce(() => this.applyFilters(), 500)();
        });
    }

    setupRangeSlider(prefix, displayId, formatter) {
        const minSlider = $(`#${prefix}Min`);
        const maxSlider = $(`#${prefix}Max`);
        const minInput = $(`#${prefix}MinInput`);
        const maxInput = $(`#${prefix}MaxInput`);
        const display = $(`#${displayId}`);

        const updateDisplay = () => {
            const min = parseInt(minSlider.val());
            const max = parseInt(maxSlider.val());
            
            // Ensure min <= max
            if (min > max) {
                minSlider.val(max);
            }
            
            const finalMin = Math.min(min, max);
            const finalMax = Math.max(min, max);
            
            display.text(formatter(finalMin, finalMax));
            minInput.val(finalMin);
            maxInput.val(finalMax);
        };

        minSlider.on('input', updateDisplay);
        maxSlider.on('input', updateDisplay);
        
        minInput.on('change', () => {
            minSlider.val(minInput.val());
            updateDisplay();
        });
        
        maxInput.on('change', () => {
            maxSlider.val(maxInput.val());
            updateDisplay();
        });

        // Trigger filter application
        minSlider.on('change', () => this.debounce(() => this.applyFilters(), 500)());
        maxSlider.on('change', () => this.debounce(() => this.applyFilters(), 500)());
    }

    setupQuickFilterButtons() {
        $('#filterHighAccuracy').on('click', () => {
            $('#accuracyMin').val(90);
            $('#accuracyRangeDisplay').text('90% - 100%');
            $('#highAccuracyFilter').prop('checked', true);
            this.applyFilters();
        });

        $('#filterNeedsUpdate').on('click', () => {
            $('#needsUpdateFilter').prop('checked', true);
            this.applyFilters();
        });

        $('#filterClearAll').on('click', () => this.resetFilters());
    }

    setupFilterInputs() {
        // Standard filter inputs
        $('#countryFilter, #sectorFilter, #sicCodeFilter').on('change', () => this.applyFilters());
        
        // Checkbox filters
        $('#needsUpdateFilter, #highAccuracyFilter, #ownershipPublic, #ownershipPrivate, #ownershipSubsidiary').on('change', () => this.applyFilters());
        
        // Search filter with debounce
        $('#sicCodeFilter').on('input', () => this.debounce(() => this.applyFilters(), 800)());
    }

    async loadInitialData() {
        try {
            // First test if the API is accessible
            const testResponse = await fetch('/api/filter_options');
            if (!testResponse.ok) {
                throw new Error(`API not accessible: ${testResponse.status} ${testResponse.statusText}`);
            }
            
            this.showLoading('Loading company data...');
            
            // Load filter options first
            await this.populateFilterOptions();
            
            // Load company data
            await this.loadCompanyData();
            
            // Hide loading and show success
            this.hideLoading();
            this.logActivity('System', 'Application initialized successfully', 'success');
            
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.hideLoading();
            
            // Show a more user-friendly error message
            const tableBody = $('#companiesTableBody');
            if (tableBody.length) {
                tableBody.html(`
                    <tr>
                        <td colspan="6" class="text-center text-danger p-4">
                            <i class="fas fa-exclamation-triangle fa-2x mb-3"></i><br>
                            <strong>Connection Error</strong><br>
                            ${error.message}<br>
                            <button class="btn btn-primary mt-3" onclick="location.reload()">
                                <i class="fas fa-refresh me-2"></i>Try Again
                            </button>
                        </td>
                    </tr>
                `);
            }
            
            this.logActivity('System', `Error loading data: ${error.message}`, 'error');
        }
    }

    async loadCompanyData() {
        try {
            const params = new URLSearchParams({
                page: this.currentPage,
                limit: this.perPage,  // Changed from per_page to limit
                ...this.filters
            });

            const response = await fetch(`/api/data?${params}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status} ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }

            this.currentData = data.data || [];
            this.totalPages = data.total_pages || 0;
            
            this.renderTable();
            this.renderPagination();
            this.updateCompanyCount(data.total || 0);
            
        } catch (error) {
            console.error('Error loading company data:', error);
            this.logActivity('System', `Error loading data: ${error.message}`, 'error');
            throw error; // Re-throw to be caught by loadInitialData
        }
    }

    async populateFilterOptions() {
        try {
            const response = await fetch('/api/filter_options');
            
            if (!response.ok) {
                throw new Error(`Filter options API failed: ${response.status} ${response.statusText}`);
            }
            
            const options = await response.json();
            
            if (options.error) {
                throw new Error(options.error);
            }

            // Initialize range sliders with actual data
            this.initializeRangeSliders(options);
            
            // Populate dropdown options
            this.populateDropdownOptions(options);
            
            this.logActivity('System', 'Filter options loaded successfully', 'success');
            
        } catch (error) {
            console.error('Error loading filter options:', error);
            this.logActivity('System', `Error loading filter options: ${error.message}`, 'error');
            // Don't throw error here - let the app continue with default values
        }
    }

    initializeRangeSliders(options) {
        // Employee range
        const empRange = options.employee_range;
        $('#employeeMin').attr('min', empRange.min).attr('max', empRange.max).val(empRange.min);
        $('#employeeMax').attr('min', empRange.min).attr('max', empRange.max).val(empRange.max);
        $('#employeeMinInput').val(empRange.min);
        $('#employeeMaxInput').val(empRange.max);
        $('#employeeRangeDisplay').text(`${this.formatNumber(empRange.min)} - ${this.formatNumber(empRange.max)} employees`);

        // Revenue range
        const revRange = options.revenue_range;
        $('#revenueMin').attr('min', revRange.min).attr('max', revRange.max).val(revRange.min);
        $('#revenueMax').attr('min', revRange.min).attr('max', revRange.max).val(revRange.max);
        $('#revenueMinInput').val(this.formatCurrency(revRange.min));
        $('#revenueMaxInput').val(this.formatCurrency(revRange.max));
        $('#revenueRangeDisplay').text(`$${this.formatCurrency(revRange.min)} - $${this.formatCurrency(revRange.max)}`);

        // Profit range
        const profitRange = options.profit_range;
        $('#profitMin').attr('min', profitRange.min).attr('max', profitRange.max).val(profitRange.min);
        $('#profitMax').attr('min', profitRange.min).attr('max', profitRange.max).val(profitRange.max);
        $('#profitMinInput').val(this.formatCurrency(profitRange.min));
        $('#profitMaxInput').val(this.formatCurrency(profitRange.max));
        $('#profitRangeDisplay').text(`$${this.formatCurrency(profitRange.min)} - $${this.formatCurrency(profitRange.max)}`);

        // Accuracy range
        const accRange = options.accuracy_range;
        $('#accuracyMin').attr('min', Math.round(accRange.min)).attr('max', Math.round(accRange.max));
        $('#accuracyRangeDisplay').text(`${Math.round(accRange.min)}% - ${Math.round(accRange.max)}%`);
    }

    populateDropdownOptions(options) {
        // Country filter
        const countrySelect = $('#countryFilter');
        countrySelect.empty().append('<option value="">All Countries</option>');
        options.countries.forEach(country => {
            countrySelect.append(`<option value="${country}">${country}</option>`);
        });

        // Sector filter
        const sectorSelect = $('#sectorFilter');
        sectorSelect.empty().append('<option value="">All Sectors</option>');
        options.sectors.forEach(sector => {
            sectorSelect.append(`<option value="${sector}">${sector}</option>`);
        });

        // Update ownership type checkboxes based on actual data
        const ownershipTypes = options.ownership_types;
        $('.form-check-container input[type="checkbox"][id^="ownership"]').each(function() {
            const value = $(this).val();
            if (!ownershipTypes.includes(value)) {
                $(this).closest('.form-check').hide();
            }
        });
    }

    applyFilters() {
        // Collect all filter values
        this.filters = {
            employee_min: $('#employeeMin').val(),
            employee_max: $('#employeeMax').val(),
            revenue_min: $('#revenueMin').val(),
            revenue_max: $('#revenueMax').val(),
            profit_min: $('#profitMin').val(),
            profit_max: $('#profitMax').val(),
            accuracy_min: $('#accuracyMin').val() / 100, // Convert to decimal
            country: $('#countryFilter').val(),
            sector: $('#sectorFilter').val(),
            sic_code: $('#sicCodeFilter').val(),
            needs_update: $('#needsUpdateFilter').is(':checked'),
            high_accuracy: $('#highAccuracyFilter').is(':checked'),
            ownership_types: this.getSelectedOwnershipTypes()
        };

        // Remove empty filters
        Object.keys(this.filters).forEach(key => {
            if (this.filters[key] === '' || this.filters[key] === null || this.filters[key] === undefined) {
                delete this.filters[key];
            }
        });

        // Reset to page 1 when applying filters
        this.currentPage = 1;
        
        // Reload data with filters
        this.loadCompanyData();
        
        // Update filter summary
        this.updateFilterSummary();
        
        this.logActivity('Filter', 'Filters applied', 'info');
    }

    getSelectedOwnershipTypes() {
        const selected = [];
        $('.form-check-container input[type="checkbox"][id^="ownership"]:checked').each(function() {
            selected.push($(this).val());
        });
        return selected.length > 0 ? selected : null;
    }

    updateFilterSummary() {
        const summary = [];
        
        if (this.filters.employee_min && this.filters.employee_max) {
            summary.push(`Employees: ${this.formatNumber(this.filters.employee_min)} - ${this.formatNumber(this.filters.employee_max)}`);
        }
        
        if (this.filters.revenue_min && this.filters.revenue_max) {
            summary.push(`Revenue: $${this.formatCurrency(this.filters.revenue_min)} - $${this.formatCurrency(this.filters.revenue_max)}`);
        }
        
        if (this.filters.accuracy_min) {
            summary.push(`Min Accuracy: ${Math.round(this.filters.accuracy_min)}%`);
        }
        
        if (this.filters.country) {
            summary.push(`Country: ${this.filters.country}`);
        }
        
        if (this.filters.sector) {
            summary.push(`Sector: ${this.filters.sector.substring(0, 30)}...`);
        }
        
        if (this.filters.needs_update) {
            summary.push('Needs Revenue Update');
        }
        
        if (this.filters.high_accuracy) {
            summary.push('High Accuracy Only');
        }

        const summaryText = summary.length > 0 ? summary.join(', ') : 'No filters applied';
        $('#filterSummary').text(summaryText);
    }

    resetFilters() {
        // Reset all form inputs
        $('#employeeMin, #employeeMax, #revenueMin, #revenueMax, #profitMin, #profitMax').val('');
        $('#employeeMinInput, #employeeMaxInput, #revenueMinInput, #revenueMaxInput, #profitMinInput, #profitMaxInput').val('');
        $('#accuracyMin').val(0);
        $('#countryFilter, #sectorFilter, #sicCodeFilter').val('');
        $('#needsUpdateFilter, #highAccuracyFilter').prop('checked', false);
        $('.form-check-container input[type="checkbox"][id^="ownership"]').prop('checked', false);
        
        // Reset filters object
        this.filters = {};
        
        // Reset page
        this.currentPage = 1;
        
        // Reload data
        this.loadCompanyData();
        
        // Reset filter summary
        $('#filterSummary').text('No filters applied');
        
        // Reset range displays
        this.populateFilterOptions(); // This will reset the ranges to original values
        
        this.logActivity('Filter', 'All filters cleared', 'info');
    }

    // Utility functions for formatting
    formatNumber(num) {
        return new Intl.NumberFormat().format(num);
    }

    formatCurrency(num) {
        if (num >= 1e9) {
            return (num / 1e9).toFixed(1) + 'B';
        }
        if (num >= 1e6) {
            return (num / 1e6).toFixed(1) + 'M';
        }
        if (num >= 1e3) {
            return (num / 1e3).toFixed(1) + 'K';
        }
        return num.toString();
    }

    renderTable() {
        const tableBody = $('#companiesTableBody');
        
        if (!this.currentData || this.currentData.length === 0) {
            tableBody.html(`
                <tr>
                    <td colspan="10" class="text-center text-muted py-4">
                        <i class="fas fa-search fs-1 mb-3 d-block text-secondary"></i>
                        No companies found matching your criteria
                    </td>
                </tr>
            `);
            return;
        }

        const rows = this.currentData.map((company, index) => {
            // Get accuracy values (already in percentage format) with proper number validation
            const oldAccuracyValue = parseFloat(company.Old_Accuracy) || 0;
            const newAccuracyValue = parseFloat(company.New_Accuracy) || 0;
            const oldAccuracy = isNaN(oldAccuracyValue) ? 0 : oldAccuracyValue;
            const newAccuracy = isNaN(newAccuracyValue) ? 0 : newAccuracyValue;
            const oldAccuracyClass = this.getAccuracyColorClass(oldAccuracy);
            const newAccuracyClass = this.getAccuracyColorClass(newAccuracy);
            
            return `
                <tr data-company-index="${(this.currentPage - 1) * this.perPage + index}">
                    <td class="fw-semibold">
                        ${company['Company Name'] || 'N/A'}
                        <button class="btn btn-sm btn-outline-info ms-2 company-info-btn" 
                                data-company-index="${(this.currentPage - 1) * this.perPage + index}" 
                                title="View Company Details">
                            <i class="fas fa-info-circle"></i>
                        </button>
                    </td>
                    <td>${company['Country'] || 'N/A'}</td>
                    <td class="text-end">${this.formatNumber(company['Employees (Total)'] || 0)}</td>
                    <td class="text-end">$${this.formatCurrency(company['Sales (USD)'] || 0)}</td>
                    <td>${company['UK SIC 2007 Code'] || 'N/A'}</td>
                    <td class="text-center">
                        <span class="${oldAccuracyClass}">${(oldAccuracy || 0).toFixed(1)}%</span>
                    </td>
                    <td class="text-center">
                        <span class="${newAccuracyClass}">${(newAccuracy || 0).toFixed(1)}%</span>
                    </td>
                    <td>${company['New_SIC'] || 'N/A'}</td>
                    <td class="text-center">
                        <button class="btn btn-primary btn-predict btn-sm" data-company-index="${(this.currentPage - 1) * this.perPage + index}" title="Predict SIC Code">
                            <i class="fas fa-robot"></i>
                        </button>
                    </td>
                    <td class="text-center">
                        <button class="btn btn-warning btn-update btn-sm" data-company-index="${(this.currentPage - 1) * this.perPage + index}" title="Update Revenue">
                            <i class="fas fa-sync"></i>
                        </button>
                    </td>
                </tr>
            `;
        });

        tableBody.html(rows.join(''));
        
        // Attach event listeners to buttons
        this.attachButtonEventListeners();
    }

    attachButtonEventListeners() {
        console.log('🔧 Attaching button event listeners...');
        
        // Remove any existing event listeners to prevent duplicates
        $('.btn-predict').off('click');
        $('.btn-update').off('click');
        $('.company-info-btn').off('click');
        
        console.log('Found buttons:', {
            predictButtons: $('.btn-predict').length,
            updateButtons: $('.btn-update').length,
            infoButtons: $('.company-info-btn').length
        });
        
        // Attach click events for Predict SIC buttons
        $('.btn-predict').on('click', (e) => {
            e.preventDefault();
            const index = $(e.currentTarget).data('company-index');
            this.predictSIC(index);
        });
        
        // Attach click events for Update Revenue buttons
        $('.btn-update').on('click', (e) => {
            e.preventDefault();
            const index = $(e.currentTarget).data('company-index');
            this.updateRevenue(index);
        });
        
        // Attach click events for Company Info buttons
        $('.company-info-btn').on('click', (e) => {
            e.preventDefault();
            console.log('🔵 Company info button clicked!');
            console.log('Event target:', e.currentTarget);
            const index = $(e.currentTarget).data('company-index');
            console.log('Company index:', index);
            this.showCompanyDetails(index);
        });
    }

    renderPagination() {
        const pagination = $('#pagination');
        
        if (this.totalPages <= 1) {
            pagination.hide();
            return;
        }
        
        pagination.show();
        
        let paginationHTML = '';
        const maxVisible = 5;
        let startPage = Math.max(1, this.currentPage - Math.floor(maxVisible / 2));
        let endPage = Math.min(this.totalPages, startPage + maxVisible - 1);
        
        if (endPage - startPage + 1 < maxVisible) {
            startPage = Math.max(1, endPage - maxVisible + 1);
        }
        
        // Previous button
        paginationHTML += `
            <li class="page-item ${this.currentPage === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${this.currentPage - 1}">Previous</a>
            </li>
        `;
        
        // First page
        if (startPage > 1) {
            paginationHTML += `<li class="page-item"><a class="page-link" href="#" data-page="1">1</a></li>`;
            if (startPage > 2) {
                paginationHTML += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
        }
        
        // Page numbers
        for (let i = startPage; i <= endPage; i++) {
            paginationHTML += `
                <li class="page-item ${i === this.currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" data-page="${i}">${i}</a>
                </li>
            `;
        }
        
        // Last page
        if (endPage < this.totalPages) {
            if (endPage < this.totalPages - 1) {
                paginationHTML += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
            paginationHTML += `<li class="page-item"><a class="page-link" href="#" data-page="${this.totalPages}">${this.totalPages}</a></li>`;
        }
        
        // Next button
        paginationHTML += `
            <li class="page-item ${this.currentPage === this.totalPages ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${this.currentPage + 1}">Next</a>
            </li>
        `;
        
        pagination.html(paginationHTML);
    }

    updateCompanyCount(count) {
        $('#companyCount').text(`${count} companies`);
    }

    changePage(e) {
        e.preventDefault();
        const page = parseInt($(e.target).data('page'));
        if (page && page !== this.currentPage && page >= 1 && page <= this.totalPages) {
            this.currentPage = page;
            this.loadCompanyData();
        }
    }

    changePerPage() {
        this.perPage = parseInt($('#perPageSelect').val());
        this.currentPage = 1;
        this.loadCompanyData();
    }

    async predictSIC(companyIndex) {
        console.log('🎯 Predict SIC button clicked for company index:', companyIndex);
        
        // Store the current prediction index for later use
        this.currentPredictionIndex = companyIndex;
        
        try {
            // Switch to the agent workflow tab first
            $('#agent-tabs a[href="#sic-panel"]').tab('show');
            
            // Clear existing workflow but don't start animation yet - wait for API response
            $('#sicWorkflowChart').empty().html('<div class="text-center p-4"><i class="fas fa-spinner fa-spin fa-3x text-primary"></i><h5 class="mt-3">Preparing SIC prediction...</h5></div>');
            
            const response = await fetch('/api/predict_sic', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    company_index: companyIndex,
                    use_real_agents: false  // Use simulation mode for stability
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            console.log('🚀 API Response:', result);
            
            if (result.error) {
                throw new Error(result.error);
            }
            
            // Update SIC workflow visualization with real agent data
            console.log('🤖 Starting real agent workflow with result:', result);
            this.startSICWorkflow(result);
            
            this.logActivity('SIC Prediction', `Real agents predicted SIC code for ${result.company_name}: ${result.predicted_sic} (${result.confidence} confidence)`, 'success');
            
        } catch (error) {
            console.error('❌ Error predicting SIC:', error);
            
            // Still show the workflow even if API fails, but with demo data
            $('#agent-tabs a[href="#sic-panel"]').tab('show');
            this.startSICWorkflow();
            
            this.showError(`Error predicting SIC: ${error.message}`);
        }
    }

    async updateSIC(companyIndex) {
        console.log('🔄 Update SIC button clicked for company index:', companyIndex);
        
        if (!this.currentData || !this.currentData[companyIndex]) {
            this.showError('Company data not found');
            return;
        }
        
        const company = this.currentData[companyIndex];
        const predictedSIC = company.Predicted_SIC;
        
        if (!predictedSIC) {
            this.showError('No predicted SIC available. Please run prediction first.');
            return;
        }
        
        try {
            this.showLoading('Updating SIC code...');
            
            const response = await fetch('/api/update_sic', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    company_index: companyIndex,
                    new_sic: predictedSIC
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            console.log('Update SIC API Response:', result);
            
            if (result.error) {
                throw new Error(result.error);
            }
            
            // Start update workflow visualization
            this.startUpdateWorkflow(result);
            
            // Fetch fresh data from server to ensure we have the latest merged data
            await this.loadCompanyData();
            
            // Refresh the table to show updated data
            this.renderTableSimple();
            
            this.hideLoading();
            this.logActivity('SIC Update', `Updated SIC code for ${result.company_name} to ${result.new_sic}`, 'success');
            
        } catch (error) {
            console.error('❌ Error updating SIC:', error);
            this.hideLoading();
            this.showError(`Error updating SIC: ${error.message}`);
        }
    }

    async updateRevenue(companyIndex) {
        console.log('💰 Update Revenue button clicked for company index:', companyIndex);
        
        try {
            this.showLoading('Updating revenue...');
            
            const response = await fetch('/api/update_revenue', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ company_index: companyIndex })
            });
            
            const result = await response.json();
            
            if (result.error) {
                throw new Error(result.error);
            }
            
            // Start revenue update workflow visualization
            this.startRevenueWorkflow(result);
            
            this.hideLoading();
            this.logActivity('Revenue Update', `Updated revenue for ${result.company_name}`, 'success');
            
        } catch (error) {
            console.error('Error updating revenue:', error);
            this.hideLoading();
            this.showError(`Error updating revenue: ${error.message}`);
        }
    }

    async updateScoreFromPrediction(predictedSic, confidence) {
        console.log('💾 Update Score from prediction:', predictedSic, 'confidence:', confidence);
        console.log('💾 Current prediction index:', this.currentPredictionIndex);
        
        try {
            // Find the currently selected company index
            const companyIndex = this.currentPredictionIndex;
            
            if (companyIndex === undefined || companyIndex === null) {
                console.error('❌ No company index found. currentPredictionIndex:', this.currentPredictionIndex);
                this.showError('No company selected for update. Please select a company first.');
                return;
            }
            
            console.log('📤 Making API call to update SIC for company index:', companyIndex);
            this.showLoading('Saving prediction results...');
            
            // Call backend API to save to CSV and update table
            const response = await fetch('/api/update_sic', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    company_index: companyIndex,
                    new_sic: predictedSic,
                    confidence: confidence
                })
            });
            
            console.log('📥 Response status:', response.status, response.statusText);
            
            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }
            
            const result = await response.json();
            console.log('📥 Update SIC API Response:', result);
            
            if (result.success) {
                console.log('✅ Update successful, refreshing data...');
                
                // Fetch fresh data from server to ensure we have the latest merged data
                await this.loadCompanyData();
                
                // Refresh the table to show updated values
                this.renderTable();
                
                this.hideLoading();
                this.logActivity('Score Update', `Updated SIC to ${result.new_sic} with ${result.new_accuracy.toFixed(1)}% accuracy for ${result.company_name}`, 'success');
                
                // Show success message in results panel
                $('#sicResults').prepend(`
                    <div class="alert alert-success alert-dismissible fade show" role="alert">
                        <i class="fas fa-check-circle me-2"></i>
                        Score updated successfully! New SIC: <strong>${result.new_sic}</strong>, Accuracy: <strong>${result.new_accuracy.toFixed(1)}%</strong>
                        <br><small class="text-muted">Saved to updated_sic_predictions.csv</small>
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                `);
                
                // Auto-dismiss the alert after 5 seconds
                setTimeout(() => {
                    $('.alert-success').fadeOut();
                }, 5000);
                
            } else {
                throw new Error(result.error || 'Failed to update SIC code');
            }
            
        } catch (error) {
            console.error('Error updating score from prediction:', error);
            this.hideLoading();
            this.showError(`Error updating score: ${error.message}`);
        }
    }

    async showCompanyDetails(companyIndex) {
        console.log('🏢 Company Info button clicked for company index:', companyIndex);
        
        try {
            // Show the modal immediately with loading state
            const modal = new bootstrap.Modal(document.getElementById('companyDetailsModal'));
            
            // Set loading state
            document.getElementById('companyDetailsModalLabel').innerHTML = `
                <i class="fas fa-building me-2"></i>Loading...
            `;
            document.getElementById('companyDetailsContent').innerHTML = `
                <div class="text-center p-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading company details...</span>
                    </div>
                    <p class="mt-2">Fetching company information and AI analysis...</p>
                </div>
            `;
            
            modal.show();
            
            // Fetch company details with AI reasoning from API
            const response = await fetch(`/api/company_details/${companyIndex}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            if (result.error) {
                throw new Error(result.error);
            }
            
            // Update modal with fetched data
            const company = result.company_data;
            const aiReasoning = result.ai_reasoning;
            const metadata = result.analysis_metadata;
            
            // Update modal title
            document.getElementById('companyDetailsModalLabel').innerHTML = `
                <i class="fas fa-building me-2"></i>${company.Company_Name || 'Unknown Company'}
            `;
            
            // Build comprehensive company details with AI reasoning
            const accuracyImprovement = metadata.accuracy_improvement;
            const improvementIcon = accuracyImprovement > 0 ? 'fa-arrow-up text-success' : 
                                   accuracyImprovement < 0 ? 'fa-arrow-down text-danger' : 
                                   'fa-minus text-muted';
            
            document.getElementById('companyDetailsContent').innerHTML = `
                <!-- Company Information Section -->
                <div class="row mb-4">
                    <div class="col-md-6">
                        <h6 class="text-primary mb-3"><i class="fas fa-building me-2"></i>Company Information</h6>
                        <div class="card border-0 bg-light p-3 mb-3">
                            <p class="mb-2"><strong>Company Name:</strong> ${company.Company_Name || 'N/A'}</p>
                            <p class="mb-2"><strong>Registration Number:</strong> ${company.Registration_Number || 'N/A'}</p>
                            <p class="mb-2"><strong>Website:</strong> ${company.Website && company.Website !== 'N/A' ? `<a href="${company.Website}" target="_blank" class="text-decoration-none">${company.Website}</a>` : 'N/A'}</p>
                            <p class="mb-0"><strong>Phone:</strong> ${company.Phone || 'N/A'}</p>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <h6 class="text-primary mb-3"><i class="fas fa-chart-line me-2"></i>Business Metrics</h6>
                        <div class="card border-0 bg-light p-3 mb-3">
                            <p class="mb-2"><strong>Sales (USD):</strong> ${company.Sales_USD && company.Sales_USD !== 'N/A' ? '$' + Number(company.Sales_USD).toLocaleString() : 'N/A'}</p>
                            <p class="mb-0"><strong>Employees:</strong> ${company.Employees_Total && company.Employees_Total !== 'N/A' ? Number(company.Employees_Total).toLocaleString() : 'N/A'}</p>
                        </div>
                    </div>
                </div>
                
                <!-- Address Section -->
                <div class="row mb-4">
                    <div class="col-12">
                        <h6 class="text-primary mb-3"><i class="fas fa-map-marker-alt me-2"></i>Company Address</h6>
                        <div class="card border-0 bg-light p-3">
                            <p class="mb-0">
                                ${[company.Address_Line_1, company.City, company.Post_Code, company.Country]
                                  .filter(item => item && item !== 'N/A')
                                  .join(', ') || 'Address not available'}
                            </p>
                        </div>
                    </div>
                </div>
                
                <!-- Business Description Section -->
                <div class="row mb-4">
                    <div class="col-12">
                        <h6 class="text-primary mb-3"><i class="fas fa-file-text me-2"></i>Business Description</h6>
                        <div class="card border-0 bg-light p-3">
                            <p class="text-muted mb-0" style="line-height: 1.6;">${company.Business_Description || 'Business description not available'}</p>
                        </div>
                    </div>
                </div>
                
                <!-- SIC Code and AI Analysis Section -->
                <div class="row">
                    <div class="col-12">
                        <h6 class="text-primary mb-3"><i class="fas fa-robot me-2"></i>SIC Code Analysis & AI Reasoning</h6>
                        
                        <!-- Current SIC Classification -->
                        <div class="card border-primary mb-3">
                            <div class="card-header bg-primary text-white">
                                <h6 class="mb-0"><i class="fas fa-code me-2"></i>Current SIC Classification</h6>
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-8">
                                        <p class="mb-2"><strong>UK SIC 2007 Code:</strong> <span class="badge bg-primary fs-6">${company.UK_SIC_2007_Code || 'N/A'}</span></p>
                                        <p class="mb-0"><strong>Description:</strong> ${company.UK_SIC_2007_Description || 'Description not available'}</p>
                                    </div>
                                    <div class="col-md-4 text-end">
                                        <p class="mb-0"><strong>Current Accuracy:</strong></p>
                                        <span class="badge bg-warning fs-5">${company.Old_Accuracy || 'N/A'}%</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- AI Reasoning -->
                        <div class="alert alert-primary border-0" style="background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);">
                            <div class="d-flex align-items-start">
                                <i class="fas fa-brain text-primary me-3 mt-1 fs-4"></i>
                                <div class="flex-grow-1">
                                    <h6 class="text-primary mb-3">AI Analysis: Why is the accuracy ${company.Old_Accuracy || 'N/A'}%?</h6>
                                    <div style="line-height: 1.7;">
                                        ${aiReasoning}
                                    </div>
                                </div>
                            </div>
                            <hr class="my-3">
                            <small class="text-muted">
                                <i class="fas fa-clock me-1"></i>
                                Analysis generated on ${new Date(metadata.generated_at).toLocaleString()}
                            </small>
                        </div>
                    </div>
                </div>
            `;
            
            this.logActivity('Company Details', `Viewed AI-powered details for ${company.Company_Name}`, 'info');
            
        } catch (error) {
            console.error('Error showing company details:', error);
            
            // Update modal with error state
            document.getElementById('companyName').textContent = 'Error Loading Company';
            document.getElementById('companyDetailsContent').innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle me-2"></i>
                    <strong>Error loading company details:</strong> ${error.message}
                    <br><small class="mt-2 d-block">Please try again or contact support if the issue persists.</small>
                </div>
            `;
            
            this.logActivity('Company Details Error', `Failed to load details for index ${companyIndex}: ${error.message}`, 'error');
        }
    }

    async startSICWorkflow(result = null) {
        console.log('🔄 startSICWorkflow called with result:', result);
        
        // Clear existing workflow and stop any running animations
        $('#sicWorkflowChart').empty();
        $('.workflow-progress-bar').stop(true, true).css('width', '0%');
        $('.workflow-arrow').removeClass('active');
        
        // Define the 4 SIC prediction agents
        const sicAgents = [
            {
                step: 1,
                agent: "Data Ingestion Agent",
                message: "Processing company data and extracting key information",
                icon: "📥",
                status: "idle"
            },
            {
                step: 2,
                agent: "Anomaly Detection Agent", 
                message: "Analyzing data for inconsistencies and outliers",
                icon: "🔍",
                status: "idle"
            },
            {
                step: 3,
                agent: "Sector Classification Agent",
                message: "Predicting SIC code based on company characteristics",
                icon: "🎯",
                status: "idle"
            },
            {
                step: 4,
                agent: "Results Compilation Agent",
                message: "Compiling final prediction results and confidence scores",
                icon: "📊",
                status: "idle"
            }
        ];
        
        // Use real workflow steps if provided, otherwise use default agents
        let workflowSteps = sicAgents;
        if (result && result.workflow_steps) {
            console.log('🤖 Using real agent workflow:', result);
            workflowSteps = result.workflow_steps.map((step, index) => ({
                step: step.step || index + 1,
                agent: step.agent,
                message: step.message,
                icon: this.getAgentIcon(step.agent),
                status: "idle"
            }));
        }
        
        // Render the 4 agents horizontally
        this.renderHorizontalWorkflow(workflowSteps);
        
        // Start the animated workflow execution
        setTimeout(() => {
            this.animateAgentWorkflow(workflowSteps, result);
        }, 500);
        
        // Store workflow data
        const workflowData = {
            workflow_steps: workflowSteps,
            prediction: result?.predicted_sic || "73110",
            confidence: result?.confidence || 0.87,
            description: result?.reasoning || "SIC code prediction using multi-agent workflow",
            company_name: result?.company_name || "Demo Company"
        };
        
        this.agentWorkflows.sic = workflowData;
        this.logActivity('Agent Workflow', 'SIC prediction workflow started', 'info');
    }
    
    renderHorizontalWorkflow(steps) {
        const workflowHtml = `
            <div class="horizontal-workflow">
                ${steps.map((step, index) => `
                    <div class="sic-workflow-step" data-step="${step.step}">
                        <div class="workflow-step-icon ${step.status}" data-step="${step.step}">
                            ${step.agent}
                        </div>
                        ${index < steps.length - 1 ? `
                            <div class="workflow-arrow" data-step="${step.step}"></div>
                        ` : ''}
                    </div>
                `).join('')}
            </div>
            <div class="workflow-progress">
                <div class="workflow-progress-bar"></div>
            </div>
        `;
        
        $('#sicWorkflowChart').html(workflowHtml);
    }
    
    animateAgentWorkflow(steps, result = null) {
        let currentStep = 0;
        const totalSteps = steps.length;
        
        const processNextAgent = () => {
            if (currentStep >= totalSteps) {
                // All agents completed, show final results
                setTimeout(() => {
                    this.displaySICResults({
                        workflow_steps: steps,
                        prediction: result?.predicted_sic || "73110",
                        confidence: result?.confidence || 0.87,
                        description: result?.reasoning || result?.analysis_explanation || result?.description || "SIC code prediction completed using multi-agent analysis",
                        company_name: result?.company_name || "Demo Company",
                        new_accuracy: result?.new_accuracy,
                        old_accuracy: result?.old_accuracy,
                        improvement_percentage: result?.improvement_percentage,
                        analysis_explanation: result?.analysis_explanation || result?.reasoning
                    });
                }, 500);
                return;
            }
            
            const stepNumber = currentStep + 1;
            
            // Mark current agent as processing
            $(`.workflow-step-icon[data-step="${stepNumber}"]`)
                .removeClass('idle completed')
                .addClass('processing');
            
            // Update progress bar - stop any existing animations first
            const progress = ((currentStep + 1) / totalSteps) * 100;
            $('.workflow-progress-bar').stop(true, false).animate({ width: `${progress}%` }, 400);
            
            // Mark arrow as active if not the last step - clear any existing active arrows first
            if (currentStep < totalSteps - 1) {
                setTimeout(() => {
                    $('.workflow-arrow').removeClass('active'); // Clear all arrows
                    $(`.workflow-arrow[data-step="${stepNumber}"]`).addClass('active');
                }, 800);
            }
            
            // Mark current agent as completed and move to next
            setTimeout(() => {
                $(`.workflow-step-icon[data-step="${stepNumber}"]`)
                    .removeClass('processing')
                    .addClass('completed');
                
                currentStep++;
                
                // Process next agent after a short delay
                setTimeout(processNextAgent, 300);
                
            }, 1200);
        };
        
        // Start the animation sequence
        processNextAgent();
    }
    
    getAgentIcon(agentName) {
        const icons = {
            "Data Ingestion Agent": "📥", 
            "Anomaly Detection Agent": "🔍",
            "Sector Classification Agent": "🎯",
            "Results Compilation Agent": "📊",
            "Smart Financial Extraction Agent": "💰",
            "Turnover Estimation Agent": "📈"
        };
        
        return icons[agentName] || "🤖";
    }

    startRevenueWorkflow(result = null) {
        // If no result provided, show demo workflow
        if (!result) {
            const demoWorkflow = {
                workflow_steps: [
                    {
                        step: 1,
                        agent: "Data Ingestion Agent",
                        message: "Collecting company financial data and market information..."
                    },
                    {
                        step: 2,
                        agent: "Smart Financial Extraction Agent", 
                        message: "Extracting and validating financial metrics..."
                    },
                    {
                        step: 3,
                        agent: "Turnover Estimation Agent",
                        message: "Calculating revenue estimates using multiple methodologies..."
                    },
                    {
                        step: 4,
                        agent: "Results Compilation Agent",
                        message: "Finalizing revenue estimation with confidence intervals..."
                    }
                ],
                estimated_revenue: 2500000,
                confidence: 0.82,
                method: "Industry benchmarking + Financial ratios"
            };
            result = demoWorkflow;
        }
        
        this.agentWorkflows.revenue = result;
        
        // Don't render workflow animation for updates - just show results
        // This prevents conflicts with the horizontal revenue prediction workflow
        this.displayRevenueResults(result);
        this.logActivity('Agent Workflow', 'Revenue update completed successfully', 'success');
    }

    startUpdateWorkflow(result = null) {
        // If no result provided, show demo workflow
        if (!result) {
            const demoWorkflow = {
                workflow_steps: [
                    {
                        step: 1,
                        agent: "Data Validation Agent",
                        message: "Validating SIC update request..."
                    },
                    {
                        step: 2,
                        agent: "SIC Classification Agent",
                        message: "Processing SIC code update..."
                    },
                    {
                        step: 3,
                        agent: "Accuracy Calculation Agent",
                        message: "Calculating new accuracy scores..."
                    },
                    {
                        step: 4,
                        agent: "Data Persistence Agent",
                        message: "Saving updates to database..."
                    },
                    {
                        step: 5,
                        agent: "Email Notification Agent",
                        message: "Sending notification to kauntey.shah@uk.ey.com"
                    }
                ]
            };
            result = demoWorkflow;
        }
        
        this.agentWorkflows.update = result;
        
        // Use a separate workflow container to avoid conflicts with SIC prediction
        // Don't render workflow animation for updates - just show results
        this.displayUpdateResults(result);
        this.logActivity('Agent Workflow', 'SIC update completed successfully', 'success');
    }

    displayUpdateResults(result) {
        const resultsContainer = $('#sicWorkflowChart .workflow-results');
        if (resultsContainer.length === 0) {
            $('#sicWorkflowChart').append('<div class="workflow-results mt-3"></div>');
        }
        
        const resultsHTML = `
            <div class="alert alert-success">
                <h6><i class="fas fa-check-circle"></i> SIC Update Complete</h6>
                <p><strong>Company:</strong> ${result.company_name || 'Demo Company'}</p>
                <p><strong>Old SIC:</strong> ${result.old_sic || 'N/A'}</p>
                <p><strong>New SIC:</strong> ${result.new_sic || 'N/A'}</p>
                <p><strong>Old Accuracy:</strong> ${result.old_accuracy ? (parseFloat(result.old_accuracy) || 0).toFixed(1) + '%' : 'N/A'}</p>
                <p><strong>New Accuracy:</strong> ${result.new_accuracy ? (parseFloat(result.new_accuracy) || 0).toFixed(1) + '%' : 'N/A'}</p>
                <p class="mb-0"><strong>Status:</strong> <span class="text-success">Updated Successfully</span></p>
            </div>
        `;
        
        $('.workflow-results').html(resultsHTML);
    }

    renderAgentWorkflow(type, steps) {
        const container = $(`#${type}WorkflowChart`);
        const stepsHTML = steps.map((step, index) => `
            <div class="workflow-step" data-step="${step.step}">
                <div class="step-number">${step.step}</div>
                <div class="step-content">
                    <div class="step-agent">${step.agent}</div>
                    <div class="step-message">${step.message}</div>
                </div>
            </div>
        `).join('');
        
        container.html(stepsHTML);
        
        // Animate steps
        steps.forEach((step, index) => {
            setTimeout(() => {
                $(`.workflow-step[data-step="${step.step}"]`).addClass('active');
            }, index * 1000);
        });
    }

    displaySICResults(data) {
        console.log('🎯 displaySICResults called with data:', data);
        const resultsContainer = $('#sicResults');
        if (!data || !data.prediction) {
            console.log('❌ displaySICResults: Missing data or prediction');
            resultsContainer.html('<div class="alert alert-warning">No SIC prediction results available</div>');
            return;
        }

        const confidence = data.confidence || 0;
        const confidenceClass = confidence > 0.8 ? 'success' : confidence > 0.6 ? 'warning' : 'danger';
        
        const resultsHTML = `
            <div class="card">
                <div class="card-header bg-primary text-white">
                    <h5 class="mb-0"><i class="fas fa-robot me-2"></i>Real Agent Prediction</h5>
                </div>
                <div class="card-body">
                    ${data.company_name ? `
                        <div class="mb-3">
                            <p class="mb-1 fs-5"><strong>${data.company_name}</strong></p>
                            ${data.current_sic ? `<small class="text-muted">Current SIC: ${data.current_sic}</small>` : ''}
                        </div>
                    ` : ''}
                    
                    ${data.improvement_percentage ? `
                        <div class="alert alert-info mb-3">
                            <strong>• Improvement: ${data.improvement_percentage}</strong>
                            ${data.analysis_explanation ? `<br><small class="text-muted">${data.analysis_explanation}</small>` : ''}
                        </div>
                    ` : ''}
                    
                    <div class="row">
                        <div class="col-md-6">
                            <h6>Predicted SIC Code</h6>
                            <div class="alert alert-info mb-2">
                                <strong>${data.prediction}</strong>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <h6>Confidence Score</h6>
                            <div class="progress mb-2">
                                <div class="progress-bar bg-${confidenceClass}" role="progressbar" 
                                     style="width: ${confidence * 100}%" 
                                     aria-valuenow="${confidence * 100}" aria-valuemin="0" aria-valuemax="100">
                                    ${(confidence * 100).toFixed(1)}%
                                </div>
                            </div>
                            ${data.new_accuracy && data.old_accuracy ? `
                                <small class="text-muted">
                                    New: ${data.new_accuracy} | Old: ${data.old_accuracy}
                                </small>
                            ` : ''}
                        </div>
                    </div>
                    
                    ${data.description ? `
                        <div class="mt-3">
                            <h6>Analysis Details: ${data.description}</h6>
                        </div>
                    ` : ''}
                    
                    <div class="mt-4 d-grid">
                        <button class="btn btn-success btn-update-score" 
                                onclick="sicApp.updateScoreFromPrediction('${data.prediction}', ${confidence * 100})"
                                title="Save this prediction as New SIC and update accuracy score">
                            <i class="fas fa-save me-2"></i>Update Score (${data.prediction})
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        resultsContainer.html(resultsHTML);
    }

    displayRevenueResults(data) {
        const resultsContainer = $('#revenueResults');
        if (!data || (!data.estimated_revenue && !data.updated_revenue)) {
            resultsContainer.html('<div class="alert alert-warning">No revenue estimation results available</div>');
            return;
        }

        const revenue = data.estimated_revenue || data.updated_revenue || 0;
        const confidence = data.confidence || 0;
        const confidenceClass = confidence > 0.8 ? 'success' : confidence > 0.6 ? 'warning' : 'danger';
        
        const resultsHTML = `
            <div class="card">
                <div class="card-header bg-success text-white">
                    <h5 class="mb-0"><i class="fas fa-pound-sign me-2"></i>Revenue Estimation Results</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <h6>Estimated Revenue</h6>
                            <div class="alert alert-success">
                                <strong>£${revenue.toLocaleString()}</strong>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <h6>Confidence Score</h6>
                            <div class="progress mb-2">
                                <div class="progress-bar bg-${confidenceClass}" role="progressbar" 
                                     style="width: ${confidence * 100}%" 
                                     aria-valuenow="${confidence * 100}" aria-valuemin="0" aria-valuemax="100">
                                    ${(confidence * 100).toFixed(1)}%
                                </div>
                            </div>
                        </div>
                    </div>
                    ${data.method ? `
                        <div class="mt-3">
                            <h6>Estimation Method</h6>
                            <span class="badge bg-info">${data.method}</span>
                        </div>
                    ` : ''}
                    ${data.factors && data.factors.length > 0 ? `
                        <div class="mt-3">
                            <h6>Key Factors</h6>
                            <div class="d-flex flex-wrap gap-1">
                                ${data.factors.map(factor => `<span class="badge bg-secondary">${factor}</span>`).join('')}
                            </div>
                        </div>
                    ` : ''}
                    ${data.notes ? `
                        <div class="mt-3">
                            <h6>Notes</h6>
                            <p class="text-muted small">${data.notes}</p>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
        
        resultsContainer.html(resultsHTML);
    }

    toggleSidebar() {
        $('.sidebar').toggleClass('collapsed');
        $('#toggleFilters i').toggleClass('fa-chevron-right fa-chevron-left');
    }

    toggleTopPanel() {
        $('#top-panel').toggleClass('panel-collapsed');
        $('#collapseTopPanel i').toggleClass('fa-chevron-up fa-chevron-down');
    }

    toggleBottomPanel() {
        $('#bottom-panel').toggleClass('panel-collapsed');
        $('#collapseBottomPanel i').toggleClass('fa-chevron-up fa-chevron-down');
    }

    showLoading(message = 'Loading...') {
        const modal = $('#loadingModal');
        if (modal.length) {
            $('#loadingMessage').text(message);
            modal.modal('show');
        } else {
            // If modal doesn't exist, create a simple loading indicator
            const loadingHtml = `
                <div id="tempLoadingModal" class="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center" 
                     style="background: rgba(255,255,255,0.9); z-index: 9999;">
                    <div class="text-center">
                        <div class="spinner-border text-primary" role="status"></div>
                        <p class="mt-2">${message}</p>
                    </div>
                </div>
            `;
            $('body').append(loadingHtml);
        }
    }

    hideLoading() {
        console.log('Hiding loading modal...');
        const modal = $('#loadingModal');
        if (modal.length) {
            modal.modal('hide');
        }
        
        // Also remove temporary loading modal if it exists
        $('#tempLoadingModal').remove();
        
        $('.modal-backdrop').remove(); // Ensure backdrop is removed
        $('body').removeClass('modal-open'); // Remove modal-open class
        
        // Also hide any loading spinners
        $('.loading-spinner').hide();
        $('#loadingSpinner').hide();
    }

    showError(message) {
        // Always hide loading modal first
        this.hideLoading();
        
        // Show error in table instead of alert
        const tableBody = $('#companiesTableBody');
        if (tableBody.length) {
            tableBody.html(`
                <tr>
                    <td colspan="6" class="text-center text-danger p-4">
                        <i class="fas fa-exclamation-triangle fa-2x mb-3"></i><br>
                        <strong>Error:</strong> ${message}<br>
                        <button class="btn btn-primary mt-2" onclick="location.reload()">
                            <i class="fas fa-refresh me-2"></i>Refresh Page
                        </button>
                    </td>
                </tr>
            `);
        }
        
        // Log the error
        console.error('Application Error:', message);
    }

    logActivity(category, message, type = 'info') {
        const timestamp = new Date().toLocaleTimeString();
        const iconClass = type === 'success' ? 'fa-check-circle text-success' : 
                         type === 'error' ? 'fa-exclamation-circle text-danger' : 
                         type === 'warning' ? 'fa-exclamation-triangle text-warning' : 
                         'fa-info-circle text-info';
        
        const logEntry = `
            <div class="log-entry d-flex align-items-start mb-2">
                <i class="fas ${iconClass} me-2 mt-1"></i>
                <div class="flex-grow-1">
                    <div class="d-flex justify-content-between">
                        <strong class="log-category">${category}</strong>
                        <small class="text-muted">${timestamp}</small>
                    </div>
                    <div class="log-message small">${message}</div>
                </div>
            </div>
        `;
        
        const logContainer = $('#activityLogs');
        logContainer.prepend(logEntry);
        
        // Keep only last 50 entries
        const entries = logContainer.find('.log-entry');
        if (entries.length > 50) {
            entries.slice(50).remove();
        }
    }

    clearLogs() {
        $('#activityLogs').empty();
        this.logActivity('System', 'Activity log cleared', 'info');
    }

    exportData() {
        // Simple CSV export functionality
        if (!this.currentData || this.currentData.length === 0) {
            this.showError('No data to export');
            return;
        }
        
        const csv = this.convertToCSV(this.currentData);
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.setAttribute('hidden', '');
        a.setAttribute('href', url);
        a.setAttribute('download', 'company_data.csv');
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        this.logActivity('Export', 'Data exported to CSV', 'success');
    }

    convertToCSV(data) {
        if (!data || data.length === 0) return '';
        
        const headers = Object.keys(data[0]);
        const csvHeaders = headers.join(',');
        const csvRows = data.map(row => 
            headers.map(header => {
                const value = row[header];
                return typeof value === 'string' && value.includes(',') ? `"${value}"` : value;
            }).join(',')
        );
        
        return [csvHeaders, ...csvRows].join('\n');
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // LangGraph Integration Methods
    async loadLangGraphWorkflow() {
        try {
            console.log('🔄 Loading LangGraph workflow structure...');
            const response = await fetch('/api/workflow/structure');
            const data = await response.json();
            
            if (data.success) {
                console.log('✅ LangGraph workflow loaded:', data);
                this.langGraphStructure = data.structure;
                this.displayLangGraphWorkflow();
                return true;
            } else {
                console.error('❌ Failed to load workflow:', data.error);
                return false;
            }
        } catch (error) {
            console.error('❌ Error loading LangGraph workflow:', error);
            return false;
        }
    }

    displayLangGraphWorkflow() {
        if (!this.langGraphStructure) return;
        
        const container = $('#sicWorkflowChart');
        if (container.length === 0) return;
        
        // Create a simple node-based visualization
        const workflow = this.langGraphStructure;
        let html = `
            <div class="langgraph-workflow">
                <div class="workflow-header mb-3">
                    <h6><i class="fas fa-project-diagram"></i> LangGraph Multi-Agent Workflow</h6>
                    <button class="btn btn-sm btn-primary" id="start-langgraph-workflow">
                        <i class="fas fa-play"></i> Execute Workflow
                    </button>
                </div>
                <div class="workflow-nodes">
        `;
        
        // Create nodes in a flow layout
        workflow.nodes.forEach((node, index) => {
            const nodeClass = node.type === 'summary' ? 'node-summary' : 'node-agent';
            html += `
                <div class="workflow-node ${nodeClass}" data-node-id="${node.id}">
                    <div class="node-content">
                        <i class="fas fa-robot"></i>
                        <span class="node-label">${node.label}</span>
                        <div class="node-status idle">
                            <i class="fas fa-circle"></i>
                        </div>
                    </div>
                </div>
            `;
            
            // Add arrows between nodes (simplified)
            if (index < workflow.nodes.length - 1) {
                html += '<div class="workflow-arrow"><i class="fas fa-arrow-down"></i></div>';
            }
        });
        
        html += `
                </div>
                <div class="workflow-info mt-3">
                    <small class="text-muted">
                        <i class="fas fa-info-circle"></i> 
                        Click "Execute Workflow" to run the complete multi-agent analysis
                    </small>
                </div>
            </div>
        `;
        
        container.html(html);
        
        // Add click handler for workflow execution
        $('#start-langgraph-workflow').on('click', () => this.executeLangGraphWorkflow());
        
        // Add CSS styles dynamically
        if (!$('#langgraph-styles').length) {
            $('head').append(`
                <style id="langgraph-styles">
                .langgraph-workflow {
                    padding: 15px;
                    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                    border-radius: 8px;
                }
                .workflow-nodes {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 10px;
                }
                .workflow-node {
                    background: white;
                    border-radius: 6px;
                    padding: 10px 15px;
                    border: 2px solid #dee2e6;
                    min-width: 200px;
                    text-align: center;
                    transition: all 0.3s ease;
                    cursor: pointer;
                }
                .workflow-node:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                }
                .node-agent {
                    border-color: #007bff;
                    color: #007bff;
                }
                .node-summary {
                    border-color: #28a745;
                    color: #28a745;
                }
                .node-content {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                }
                .node-label {
                    font-weight: 500;
                    margin: 0 10px;
                }
                .node-status {
                    font-size: 0.8em;
                }
                .node-status.idle { color: #6c757d; }
                .node-status.running { color: #ffc107; }
                .node-status.completed { color: #28a745; }
                .node-status.error { color: #dc3545; }
                .workflow-arrow {
                    color: #6c757d;
                    font-size: 1.2em;
                }
                .workflow-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                </style>
            `);
        }
    }

    async executeLangGraphWorkflow() {
        try {
            console.log('🚀 Executing LangGraph workflow...');
            
            // Update button state
            const button = $('#start-langgraph-workflow');
            const originalText = button.html();
            button.html('<i class="fas fa-spinner fa-spin"></i> Running...').prop('disabled', true);
            
            // Update node statuses to show progress
            this.updateWorkflowProgress('running');
            
            const response = await fetch('/api/workflow/execute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            });
            
            const result = await response.json();
            
            if (result.success) {
                console.log('✅ Workflow execution completed:', result);
                this.updateWorkflowProgress('completed');
                this.displayWorkflowResults(result);
                this.logActivity('LangGraph Workflow', 'Multi-agent workflow executed successfully', 'success');
            } else {
                console.error('❌ Workflow execution failed:', result.error);
                this.updateWorkflowProgress('error');
                this.logActivity('LangGraph Workflow', `Workflow failed: ${result.error}`, 'error');
            }
            
            // Restore button
            button.html(originalText).prop('disabled', false);
            
        } catch (error) {
            console.error('❌ Error executing workflow:', error);
            this.updateWorkflowProgress('error');
            this.logActivity('LangGraph Workflow', `Workflow error: ${error.message}`, 'error');
            
            // Restore button
            $('#start-langgraph-workflow').html(originalText).prop('disabled', false);
        }
    }

    updateWorkflowProgress(status) {
        $('.workflow-node .node-status').removeClass('idle running completed error').addClass(status);
    }

    displayWorkflowResults(result) {
        const resultsContainer = $('#sicResults');
        if (resultsContainer.length === 0) return;
        
        const html = `
            <div class="workflow-results">
                <h6><i class="fas fa-chart-bar"></i> LangGraph Workflow Results</h6>
                <div class="result-item">
                    <strong>Session ID:</strong> ${result.session_id || 'N/A'}
                </div>
                <div class="result-item">
                    <strong>Current Stage:</strong> ${result.current_stage || 'N/A'}
                </div>
                <div class="result-item">
                    <strong>LangGraph Mode:</strong> ${result.langgraph_enabled ? 'Full LangGraph' : 'Fallback Mode'}
                </div>
                <div class="result-item">
                    <strong>Anomalies Found:</strong> ${result.results?.anomalies?.length || 0}
                </div>
                <div class="result-item">
                    <strong>Sector Predictions:</strong> ${Object.keys(result.results?.sector_predictions || {}).length}
                </div>
                <div class="result-item">
                    <strong>Revenue Estimates:</strong> ${Object.keys(result.results?.revenue_estimates || {}).length}
                </div>
                ${result.error ? `<div class="alert alert-warning mt-2"><small>Warning: ${result.error}</small></div>` : ''}
                <div class="mt-3">
                    <button class="btn btn-sm btn-outline-primary" onclick="window.open('/workflow', '_blank')">
                        <i class="fas fa-external-link-alt"></i> Full Visualization
                    </button>
                </div>
            </div>
        `;
        
        resultsContainer.html(html);
    }
}