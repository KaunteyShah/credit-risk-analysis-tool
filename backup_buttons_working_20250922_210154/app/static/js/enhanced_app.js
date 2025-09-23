/**
 * Enhanced Flask App JavaScript for SIC Prediction System
 * Simplified version that actually works
 */

$(document).ready(function() {
    console.log('Document ready - starting app initialization');
    
    // Hide any loading modals immediately
    $('#loadingModal').modal('hide');
    $('.modal-backdrop').remove();
    $('body').removeClass('modal-open');
    
    // Initialize the app
    const app = new SICPredictionApp();
});

class SICPredictionApp {
    constructor() {
        console.log('SICPredictionApp constructor called');
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
        console.log('Quick initialization starting...');
        
        // Setup basic event listeners first
        this.setupBasicEventListeners();
        
        // Initialize panels
        this.initializePanels();
        
        // Load data without showing loading modal
        this.loadDataDirectly();
        
        // Setup agent dashboard
        this.setupAgentDashboard();
        
        console.log('Quick initialization completed');
    }

    setupBasicEventListeners() {
        console.log('Setting up basic event listeners...');
        
        // Sidebar toggle
        $('#toggleFilters, #collapseSidebar').on('click', () => this.toggleSidebar());
        
        // Simple refresh button
        $(document).on('click', '.btn-refresh, #refreshBtn', () => {
            console.log('Refresh clicked');
            this.loadDataDirectly();
        });
        
        console.log('Basic event listeners setup complete');
    }

    async loadDataDirectly() {
        console.log('Loading data directly...');
        
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
            console.log('Data loaded successfully:', data);
            
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
            console.log('Loading filter options quietly...');
            const response = await fetch('/api/filter_options');
            if (response.ok) {
                const options = await response.json();
                console.log('Filter options loaded:', options);
                // TODO: Setup filters with options
            }
        } catch (error) {
            console.warn('Filter options failed to load:', error);
        }
    }

    renderTableSimple() {
        console.log('Rendering table with', this.currentData.length, 'companies');
        
        const tableBody = $('#companiesTableBody');
        if (!tableBody.length) {
            console.error('Table body element not found');
            return;
        }
        
        tableBody.empty();
        
        if (!this.currentData || this.currentData.length === 0) {
            tableBody.html(`
                <tr>
                    <td colspan="8" class="text-center text-muted p-4">
                        <i class="fas fa-info-circle fa-2x mb-3"></i><br>
                        No companies found
                    </td>
                </tr>
            `);
            return;
        }
        
        this.currentData.forEach((company, index) => {
            const accuracy = company.SIC_Accuracy ? (company.SIC_Accuracy * 100).toFixed(1) + '%' : 'N/A';
            const accuracyClass = company.SIC_Accuracy >= 0.9 ? 'text-success fw-bold' : 
                                 company.SIC_Accuracy >= 0.8 ? 'text-warning fw-bold' : 'text-danger fw-bold';
            
            const row = `
                <tr>
                    <td>${company['Company Name'] || 'N/A'}</td>
                    <td>${company.Country || 'N/A'}</td>
                    <td>${company['Employees (Total)'] ? parseInt(company['Employees (Total)']).toLocaleString() : 'N/A'}</td>
                    <td>${company['Sales (USD)'] ? '$' + parseInt(company['Sales (USD)']).toLocaleString() : 'N/A'}</td>
                    <td>${company['UK SIC 2007 Code'] || 'N/A'}</td>
                    <td><span class="${accuracyClass}">${accuracy}</span></td>
                </tr>
            `;
            tableBody.append(row);
        });
        
        console.log('Table rendered successfully');
    }

    initializePanels() {
        console.log('Initializing panels...');
        
        // Make sure panels are visible
        $('#mainTablePanel').show();
        $('#agentDashboardPanel').show();
        $('#filterSidebar').show();
        
        // Setup split panels if Split.js is available
        if (typeof Split !== 'undefined') {
            try {
                Split(['#mainTablePanel', '#agentDashboardPanel'], {
                    direction: 'vertical',
                    sizes: [60, 40],
                    minSize: [200, 150],
                    gutterSize: 10,
                    cursor: 'row-resize'
                });
                console.log('Split panels initialized');
            } catch (error) {
                console.warn('Split.js initialization failed:', error);
            }
        }
    }

    setupAgentDashboard() {
        console.log('Setting up agent dashboard...');
        
        // Make sure agent tabs are visible and functional
        $('#sicAgentTab, #revenueAgentTab').on('click', function(e) {
            e.preventDefault();
            $(this).tab('show');
        });
        
        // Show some demo content in agent areas
        this.showAgentContent();
        
        console.log('Agent dashboard setup complete');
    }

    showAgentContent() {
        // Show SIC agent content
        const sicContent = $('#sicWorkflowChart');
        if (sicContent.length) {
            sicContent.html(`
                <div class="text-center p-4">
                    <i class="fas fa-robot fa-3x text-primary mb-3"></i>
                    <h5>SIC Prediction Agent</h5>
                    <p class="text-muted">Ready to predict SIC codes</p>
                    <button class="btn btn-primary btn-sm">
                        <i class="fas fa-play me-2"></i>Start Prediction
                    </button>
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
                    <button class="btn btn-success btn-sm">
                        <i class="fas fa-play me-2"></i>Start Update
                    </button>
                </div>
            `);
        }
    }

    toggleSidebar() {
        console.log('Toggling sidebar...');
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
        
        console.log(`[${category}] ${message}`);
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

    initializePanels() {
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
    }

    async loadInitialData() {
        try {
            console.log('Starting loadInitialData...');
            
            // First test if the API is accessible
            console.log('Testing API connectivity...');
            const testResponse = await fetch('/api/filter_options');
            if (!testResponse.ok) {
                throw new Error(`API not accessible: ${testResponse.status} ${testResponse.statusText}`);
            }
            console.log('API connectivity confirmed');
            
            this.showLoading('Loading company data...');
            
            // Load filter options first
            console.log('Loading filter options...');
            await this.populateFilterOptions();
            console.log('Filter options loaded successfully');
            
            // Load company data
            console.log('Loading company data...');
            await this.loadCompanyData();
            console.log('Company data loaded successfully');
            
            // Hide loading and show success
            this.hideLoading();
            this.logActivity('System', 'Application initialized successfully', 'success');
            console.log('Initial data loading completed successfully');
            
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
            console.log('Loading company data...');
            const params = new URLSearchParams({
                page: this.currentPage,
                limit: this.perPage,  // Changed from per_page to limit
                ...this.filters
            });

            console.log('Fetching data with params:', params.toString());
            const response = await fetch(`/api/data?${params}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status} ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('Data received:', data);
            
            if (data.error) {
                throw new Error(data.error);
            }

            this.currentData = data.data || [];
            this.totalPages = data.total_pages || 0;
            
            console.log(`Loaded ${this.currentData.length} companies, page ${data.page} of ${this.totalPages}`);
            
            this.renderTable();
            this.renderPagination();
            this.updateCompanyCount(data.total || 0);
            
            console.log('Company data loaded and rendered successfully');
            
        } catch (error) {
            console.error('Error loading company data:', error);
            this.logActivity('System', `Error loading data: ${error.message}`, 'error');
            throw error; // Re-throw to be caught by loadInitialData
        }
    }

    async populateFilterOptions() {
        try {
            console.log('Fetching filter options...');
            const response = await fetch('/api/filter_options');
            
            if (!response.ok) {
                throw new Error(`Filter options API failed: ${response.status} ${response.statusText}`);
            }
            
            const options = await response.json();
            console.log('Filter options received:', options);
            
            if (options.error) {
                throw new Error(options.error);
            }

            // Initialize range sliders with actual data
            this.initializeRangeSliders(options);
            
            // Populate dropdown options
            this.populateDropdownOptions(options);
            
            this.logActivity('System', 'Filter options loaded successfully', 'success');
            console.log('Filter options populated successfully');
            
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
        $('#accuracyMin').attr('min', Math.round(accRange.min * 100)).attr('max', Math.round(accRange.max * 100));
        $('#accuracyRangeDisplay').text(`${Math.round(accRange.min * 100)}% - ${Math.round(accRange.max * 100)}%`);
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
            summary.push(`Min Accuracy: ${Math.round(this.filters.accuracy_min * 100)}%`);
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
        console.log('renderTable() called with currentData:', this.currentData?.length || 0, 'items');
        const tableBody = $('#companiesTableBody');
        
        if (!this.currentData || this.currentData.length === 0) {
            console.log('No data found, showing empty message');
            tableBody.html(`
                <tr>
                    <td colspan="8" class="text-center text-muted py-4">
                        <i class="fas fa-search fs-1 mb-3 d-block text-secondary"></i>
                        No companies found matching your criteria
                    </td>
                </tr>
            `);
            return;
        }

        const rows = this.currentData.map((company, index) => {
            const accuracy = (company.SIC_Accuracy * 100).toFixed(1);
            const accuracyClass = accuracy >= 90 ? 'high' : accuracy >= 75 ? 'medium' : 'low';
            
            return `
                <tr data-company-index="${(this.currentPage - 1) * this.perPage + index}">
                    <td class="fw-semibold">${company['Company Name'] || 'N/A'}</td>
                    <td>${company['Country'] || 'N/A'}</td>
                    <td class="text-end">${this.formatNumber(company['Employees (Total)'] || 0)}</td>
                    <td class="text-end">$${this.formatCurrency(company['Sales (USD)'] || 0)}</td>
                    <td>${company['Current SIC'] || company['SIC Code'] || 'N/A'}</td>
                    <td>
                        <span class="sic-accuracy ${accuracyClass}">${accuracy}%</span>
                    </td>
                    <td>
                        <button class="btn btn-primary btn-predict btn-sm" data-company-index="${(this.currentPage - 1) * this.perPage + index}" title="Predict SIC Code">
                            <i class="fas fa-robot"></i>
                        </button>
                    </td>
                    <td>
                        <button class="btn btn-warning btn-update btn-sm" data-company-index="${(this.currentPage - 1) * this.perPage + index}" title="Update Revenue">
                            <i class="fas fa-sync"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        console.log('Generated', this.currentData.length, 'table rows with buttons');
        console.log('Sample row HTML:', rows.substring(0, 300) + '...');
        tableBody.html(rows);
        console.log('Table HTML updated');
        
        // Debug: Check if buttons were actually added to DOM
        setTimeout(() => {
            const buttonCount = $('.btn-predict').length + $('.btn-update').length;
            console.log('Buttons found in DOM:', buttonCount);
            console.log('Predict buttons:', $('.btn-predict').length);
            console.log('Update buttons:', $('.btn-update').length);
        }, 100);
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

    async predictSIC(e) {
        const row = $(e.target).closest('tr');
        const companyIndex = row.data('company-index');
        
        try {
            this.showLoading('Predicting SIC code...');
            
            const response = await fetch('/api/predict_sic', {
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
            
            // Start SIC workflow visualization
            this.startSICWorkflow(result);
            
            this.hideLoading();
            this.logActivity('SIC Prediction', `Predicted SIC code for ${result.company_name}: ${result.predicted_sic}`, 'success');
            
        } catch (error) {
            console.error('Error predicting SIC:', error);
            this.hideLoading();
            this.showError(`Error predicting SIC: ${error.message}`);
        }
    }

    async updateRevenue(e) {
        const row = $(e.target).closest('tr');
        const companyIndex = row.data('company-index');
        
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

    startSICWorkflow(result) {
        this.agentWorkflows.sic = result;
        this.renderAgentWorkflow('sic', result.workflow_steps);
        this.logActivity('Agent Workflow', 'SIC prediction workflow started', 'info');
    }

    startRevenueWorkflow(result) {
        this.agentWorkflows.revenue = result;
        this.renderAgentWorkflow('revenue', result.workflow_steps);
        this.logActivity('Agent Workflow', 'Revenue update workflow started', 'info');
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

    setupAgentDashboard() {
        // Initialize agent dashboard tabs
        $('#agentTabs .nav-link').on('click', function(e) {
            e.preventDefault();
            $(this).tab('show');
        });
        
        // Initialize workflow areas
        this.initializeWorkflowAreas();
    }

    initializeWorkflowAreas() {
        // Set up initial workflow visualization areas
        $('#sicWorkflowChart, #revenueWorkflowChart').html(`
            <div class="text-center text-muted py-4">
                <i class="fas fa-robot fs-1 mb-3 d-block"></i>
                <p>No active workflow</p>
                <small>Start a prediction or update to see agent workflow</small>
            </div>
        `);
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
        console.log('Showing loading:', message);
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
        
        console.log('Loading modal hidden');
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

// Initialize the application when the DOM is ready
$(document).ready(function() {
    // Add emergency fallback for loading modal
    setTimeout(() => {
        if ($('#loadingModal').hasClass('show')) {
            console.warn('Emergency fallback: Force hiding loading modal after 15 seconds');
            $('#loadingModal').modal('hide');
        }
    }, 15000);
    
    window.sicApp = new SICPredictionApp();
});

// Global error handler
window.onerror = function(msg, url, lineNo, columnNo, error) {
    console.error('JavaScript Error:', msg, 'at', url, ':', lineNo);
    return false;
};

console.log('Enhanced app JavaScript loaded and ready');