/**
 * Fix for Update Results button - Clean implementation
 * This completely replaces the broken updateScoreFromPrediction method
 */

console.log('🔧 Loading Update Results Fix...');

// Wait for DOM and ModularDashboard to be ready
$(document).ready(function() {
    console.log('🔧 DOM ready, checking for ModularDashboard...');
    
    // Wait a bit for ModularDashboard to initialize
    setTimeout(() => {
        if (window.ModularDashboard) {
            console.log('🔧 ModularDashboard found, applying fix...');
            
            // Override the problematic updateScoreFromPrediction method
            window.ModularDashboard.updateScoreFromPrediction = async function(predictedSIC, confidencePercentage) {
                console.log('🔧 FIXED METHOD CALLED: Update Score from prediction:', predictedSIC, 'confidence:', confidencePercentage);
                console.log('🔧 FIXED: Current prediction index:', this.currentPredictionIndex);
                
                try {
                    // Find the currently selected company index
                    const companyIndex = this.currentPredictionIndex;
                    
                    if (companyIndex === undefined || companyIndex === null) {
                        console.error('❌ No company index found. currentPredictionIndex:', this.currentPredictionIndex);
                        alert('No company selected for update. Please run SIC prediction first.');
                        return;
                    }
                    
                    console.log('📤 Making API call to update SIC for company index:', companyIndex);
                    
                    // Show loading state in the results panel immediately
                    $('#sicResults').prepend(`
                        <div class="alert alert-info" id="updating-alert">
                            <i class="fas fa-spinner fa-spin me-2"></i>
                            <strong>Updating SIC prediction...</strong> Please wait while we save your results.
                        </div>
                    `);
                    
                    // Call backend API to save to CSV and update table
                    const response = await window.ModularCore.makeApiCall('update-sic', {
                        method: 'POST',
                        body: JSON.stringify({
                            company_index: companyIndex,
                            new_sic: predictedSIC,
                            confidence: confidencePercentage  // This is already in percentage format (0-100)
                        })
                    });
                    
                    console.log('📥 Update SIC API Response:', response);
                    
                    if (response && response.success) {
                        console.log('✅ Update successful, refreshing data...');
                        
                        // Remove loading state
                        $('#updating-alert').remove();
                        
                        // Refresh the companies data to show updated values
                        await this.loadCompaniesData();
                        
                        // Log activity if method exists
                        if (this.logActivity) {
                            this.logActivity('Score Update', `Updated SIC to ${response.new_sic} with ${response.new_accuracy.toFixed(1)}% accuracy for ${response.company_name}`, 'success');
                        }
                        
                        // Show success message in results panel
                        $('#sicResults').prepend(`
                            <div class="alert alert-success alert-dismissible fade show" role="alert">
                                <i class="fas fa-check-circle me-2"></i>
                                <strong>Success!</strong> SIC updated to <strong>${response.new_sic}</strong> with <strong>${response.new_accuracy.toFixed(1)}%</strong> accuracy.
                                <br><small class="text-muted">Saved to updated_sic_predictions.csv</small>
                                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                            </div>
                        `);
                        
                        // Auto-dismiss the alert after 5 seconds
                        setTimeout(() => {
                            $('.alert-success').fadeOut();
                        }, 5000);
                        
                    } else {
                        throw new Error(response?.error || 'Failed to update SIC code - no response received');
                    }
                    
                } catch (error) {
                    console.error('❌ Error updating score from prediction:', error);
                    $('#updating-alert').remove();
                    
                    // Show error message
                    $('#sicResults').prepend(`
                        <div class="alert alert-danger alert-dismissible fade show" role="alert">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            <strong>Error:</strong> Failed to update SIC prediction. ${error.message}
                            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                        </div>
                    `);
                    
                    setTimeout(() => {
                        $('.alert-danger').fadeOut();
                    }, 10000);
                }
            };
            
            console.log('🔧 Update Results method override applied successfully!');
            
            // Also add event delegation for any dynamically created Update Results buttons
            $(document).off('click', '.btn-update-score');
            $(document).on('click', '.btn-update-score', function(e) {
                e.preventDefault();
                console.log('🔧 Update Results button clicked via event delegation');
                
                // Extract data from the button's onclick attribute or data attributes
                const onclick = $(this).attr('onclick');
                if (onclick) {
                    // Parse the onclick to extract the parameters
                    const match = onclick.match(/updateScoreFromPrediction\(['"]([^'"]+)['"],\s*([^)]+)\)/);
                    if (match) {
                        const predictedSIC = match[1];
                        const confidence = parseFloat(match[2]);
                        console.log('🔧 Extracted parameters:', predictedSIC, confidence);
                        
                        // Call our fixed method
                        window.ModularDashboard.updateScoreFromPrediction(predictedSIC, confidence);
                    } else {
                        console.error('🔧 Could not parse onclick parameters');
                        alert('Could not parse button parameters. Please try again.');
                    }
                } else {
                    console.error('🔧 No onclick attribute found');
                    alert('Button configuration error. Please refresh the page.');
                }
            });
            
            console.log('🔧 Event delegation for Update Results buttons added');
            
        } else {
            console.error('❌ ModularDashboard not found - fix could not be applied');
            // Retry after another delay
            setTimeout(() => {
                if (window.ModularDashboard) {
                    console.log('🔧 ModularDashboard found on retry');
                    // Apply the same fix logic here if needed
                }
            }, 2000);
        }
    }, 1000);
});