document.addEventListener('DOMContentLoaded', function () {
    const containerDiv = document.getElementById("vizContainer");
    const exportPDF = document.getElementById("exportPDF");
    const exportImage = document.getElementById("exportImage");
    let viz;

    // Tableau Cloud test URL
    /*const url = "https://us-east-1.online.tableau.com/t/osc3732-38648b4cc0/views/AegisDashboard/Dashboard1?:origin=card_share_link&:embed=n";*/
    // Tableau Public URL
    const url = "https://public.tableau.com/views/AegisAnalytics/Dashboard1?:language=en-US&publish=yes&:sid=&:redirect=auth&:display_count=n&:origin=viz_share_link";

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