document.addEventListener('DOMContentLoaded', function () {
    const containerDiv = document.getElementById("vizContainer");
    const exportPDF = document.getElementById("exportPDF");
    const exportImage = document.getElementById("exportImage");
    let viz;

    /*
    const url = "https://us-east-1.online.tableau.com/t/osc3732-38648b4cc0/views/AegisDashboard/Dashboard1?:origin=card_share_link&:embed=n";
    const options = {
        hideTabs: true,
        height: "80vh",  // Match container height
        width: "100%",   // Take full width of container
        borderRadius: "0.625rem",
        device: "desktop",
        onFirstInteractive: function () {
            viz = tableau.VizManager.getVizs()[0]; // Store the instance
            
            // Update any loading indicators
            const loader = document.querySelector(".dashboard-loader");
            if (loader) {
                loader.style.display = "none";
            }
            
            // Show success message
            const statusContainer = document.getElementById('statusMessages');
            if (statusContainer) {
                const statusElement = document.createElement('div');
                statusElement.className = 'status-message success';
                statusElement.textContent = 'Dashboard loaded successfully';
                
                statusContainer.appendChild(statusElement);
                
                // Auto-remove after 5 seconds
                setTimeout(() => {
                    statusElement.classList.add('fade-out');
                    setTimeout(() => statusElement.remove(), 500);
                }, 5000);
            }
        }
    };

    // Function to initialize the visualization
    function initViz() {
        if (!containerDiv) {
            console.error("Tableau container not found");
            return;
        }
        
        try {
            // Check if Tableau JS API is loaded
            if (typeof tableau === 'undefined') {
                console.error("Tableau API not loaded");
                return;
            }
            
            // Clear any previous content
            //containerDiv.innerHTML = '<div class="dashboard-loader">Loading dashboard...</div>';
            
            // Initialize the viz
            viz = new tableau.Viz(containerDiv, url, options);
        } catch (error) {
            console.error("Error initializing Tableau dashboard:", error);
            
            // Show error in container
            containerDiv.innerHTML = `
                <div class="dashboard-error">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Error loading dashboard: ${error.message}</p>
                    <button id="retry-tableau" class="button">
                        <span class="shadow"></span>
                        <span class="edge"></span>
                        <div class="front">
                            <span>Retry</span>
                        </div>
                    </button>
                </div>
            `;
            
            // Add retry button listener
            document.getElementById('retry-tableau')?.addEventListener('click', initViz);
        }
    }

    // Function to refresh the Tableau dashboard
    window.refreshDashboard = function() {
        if (!viz) {
            console.warn("Tableau visualization not initialized");
            return;
        }
        
        try {
            console.log("Refreshing Tableau dashboard");
            viz.refreshDataAsync()
                .then(() => {
                    console.log("Dashboard refreshed successfully");
                    
                    // Show success message
                    const statusContainer = document.getElementById('statusMessages');
                    if (statusContainer) {
                        const statusElement = document.createElement('div');
                        statusElement.className = 'status-message success';
                        statusElement.textContent = 'Dashboard refreshed successfully';
                        
                        statusContainer.appendChild(statusElement);
                        
                        // Auto-remove after 5 seconds
                        setTimeout(() => {
                            statusElement.classList.add('fade-out');
                            setTimeout(() => statusElement.remove(), 500);
                        }, 5000);
                    }
                })
                .catch(err => {
                    console.error("Error refreshing dashboard:", err);
                    
                    // Show error message
                    const statusContainer = document.getElementById('statusMessages');
                    if (statusContainer) {
                        const statusElement = document.createElement('div');
                        statusElement.className = 'status-message error';
                        statusElement.textContent = `Error refreshing dashboard: ${err.message}`;
                        
                        statusContainer.appendChild(statusElement);
                        
                        // Auto-remove after 5 seconds
                        setTimeout(() => {
                            statusElement.classList.add('fade-out');
                            setTimeout(() => statusElement.remove(), 500);
                        }, 5000);
                    }
                });
        } catch (error) {
            console.error("Error refreshing dashboard:", error);
        }
    };

*/


    const url = "https://us-east-1.online.tableau.com/t/osc3732-38648b4cc0/views/AegisDashboard/Dashboard1?:origin=card_share_link&:embed=n";
    const options = {
        hideTabs: true,
        borderRadius: "0.625rem",
        device: "desktop",
        onFirstInteractive: function () {
            viz = tableau.VizManager.getVizs()[0]; // Store the instance
        }
    };

    function initViz() {
        viz = new tableau.Viz(containerDiv, url, options)
    }

    // Function to refresh the Tableau dashboard
    window.refreshDashboard = function() {
        if (viz) {
            viz.refreshDataAsync().then(() => {
                console.log("Dashboard refreshed successfully");
                    
                    // Show success message
                    const statusContainer = document.getElementById('statusMessages');
                    if (statusContainer) {
                        const statusElement = document.createElement('div');
                        statusElement.className = 'status-message success';
                        statusElement.textContent = 'Dashboard refreshed successfully';
                        
                        statusContainer.appendChild(statusElement);
                        
                        // Auto-remove after 5 seconds
                        setTimeout(() => {
                            statusElement.classList.add('fade-out');
                            setTimeout(() => statusElement.remove(), 500);
                        }, 5000);
                    }
            }).catch(err => {
                console.error("Error refreshing dashboard:", err);
                    
                    // Show error message
                    const statusContainer = document.getElementById('statusMessages');
                    if (statusContainer) {
                        const statusElement = document.createElement('div');
                        statusElement.className = 'status-message error';
                        statusElement.textContent = `Error refreshing dashboard: ${err.message}`;
                        
                        statusContainer.appendChild(statusElement);
                        
                        // Auto-remove after 5 seconds
                        setTimeout(() => {
                            statusElement.classList.add('fade-out');
                            setTimeout(() => statusElement.remove(), 500);
                        }, 5000);
                    }
            });
        }
    }

    document.addEventListener('DOMContentLoaded', initViz)
    exportPDF.addEventListener('click', function () {
        viz.showExportPDFDialog();
    });
    exportImage.addEventListener('click', function () {
        viz.showExportImageDialog();
    });
    // Initialize Tableau visualization
    initViz();
});