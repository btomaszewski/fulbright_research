const containerDiv = document.getElementById("vizContainer");
const exportPDF = document.getElementById("exportPDF");
const exportImage = document.getElementById("exportImage");
let viz;

const url = "https://public.tableau.com/views/AegisAnalytics/Dashboard1?:language=en-US&publish=yes&:sid=&:redirect=auth&:display_count=n&:origin=viz_share_link";
const options = {
    hideTabs: true,
    height: 800,
    width: "100%",
    borderRadius: "0.625rem",
    device: "desktop",
    onFirstInteractive: function () {
        console.log("Tableau Dashboard is ready.");
        viz = tableau.VizManager.getVizs()[0]; // Store the instance
    }
};

function initViz() {
    viz = new tableau.Viz (containerDiv, url, options)
}

// Function to refresh the Tableau dashboard
function refreshDashboard() {
    if (viz) {
        console.log("Refreshing Tableau dashboard...");
        viz.refreshDataAsync().then(() => {
            console.log("Dashboard refreshed.");
        }).catch(err => console.error("Error refreshing dashboard:", err));
    }
}

document.addEventListener('DOMContentLoaded', initViz)
exportPDF.addEventListener('click', function() {
    viz.showExportPDFDialog();
});
exportImage.addEventListener('click', function() {
    viz.showExportImageDialog();
});