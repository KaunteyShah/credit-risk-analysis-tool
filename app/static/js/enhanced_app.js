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
                    <td>${company['Company Name'] || 'N/A'}</td>
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
                    <td class="fw-semibold">${company['Company Name'] || 'N/A'}</td>
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
        // Remove any existing event listeners to prevent duplicates
        $('.btn-predict').off('click');
        $('.btn-update').off('click');
        
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
            // Start showing the workflow visualization immediately
            this.startSICWorkflow();
            
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

    startSICWorkflow(result = null) {
        console.log('🔄 startSICWorkflow called with result:', result);
        
        // If real agent result provided, use it
        if (result && result.workflow_steps) {
            console.log('🤖 Using real agent workflow:', result);
            console.log('✅ workflow_steps found:', result.workflow_steps);
            
            // Map the real workflow steps to our display format
            const workflowSteps = result.workflow_steps.map(step => ({
                step: step.step,
                agent: step.agent,
                message: step.message,
                status: step.status || 'completed'
            }));
            
            // Store the real workflow data
            const workflowData = {
                workflow_steps: workflowSteps,
                prediction: result.predicted_sic,
                confidence: result.new_accuracy ? parseFloat(result.new_accuracy.replace('%', '')) / 100 : (typeof result.confidence === 'string' ? parseFloat(result.confidence.replace('%', '')) / 100 : result.confidence), // Use new_accuracy if available, otherwise fall back to confidence
                description: result.reasoning || 'Real agent prediction',
                company_name: result.company_name,
                current_sic: result.current_sic,
                workflow_type: result.workflow_type,
                // Store additional accuracy info for display
                new_accuracy: result.new_accuracy,
                old_accuracy: result.old_accuracy,
                improvement_percentage: result.improvement_percentage,
                analysis_explanation: result.analysis_explanation
            };
            
            console.log('📊 About to call displaySICResults with workflowData:', workflowData);
            
            this.agentWorkflows.sic = workflowData;
            this.renderAgentWorkflow('sic', workflowSteps);
            this.displaySICResults(workflowData);
            this.logActivity('Agent Workflow', `Real ${result.workflow_type} SIC prediction workflow completed for ${result.company_name}`, 'success');
            return;
        }
        
        // Fallback to demo workflow if no real data
        const demoWorkflow = {
            workflow_steps: [
                {
                    step: 1,
                    agent: "Data Ingestion Agent",
                    message: "Processing company data and extracting key information..."
                },
                {
                    step: 2,
                    agent: "Anomaly Detection Agent", 
                    message: "Analyzing data for inconsistencies and outliers..."
                },
                {
                    step: 3,
                    agent: "Sector Classification Agent",
                    message: "Predicting SIC code based on company characteristics..."
                },
                {
                    step: 4,
                    agent: "Results Compilation Agent",
                    message: "Compiling final prediction results and confidence scores..."
                }
            ],
            prediction: "73110",
            confidence: 0.87,
            description: "Demo: Research and experimental development on biotechnology"
        };
        
        this.agentWorkflows.sic = demoWorkflow;
        this.renderAgentWorkflow('sic', demoWorkflow.workflow_steps);
        this.displaySICResults(demoWorkflow);
        this.logActivity('Agent Workflow', 'Demo SIC prediction workflow started', 'info');
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
        this.renderAgentWorkflow('revenue', result.workflow_steps);
        this.displayRevenueResults(result);
        this.logActivity('Agent Workflow', 'Revenue update workflow started', 'info');
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
        this.renderAgentWorkflow('sic', result.workflow_steps);
        this.displayUpdateResults(result);
        this.logActivity('Agent Workflow', 'SIC update workflow started', 'info');
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
}