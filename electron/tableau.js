const containerDiv = document.getElementById("vizContainer");
const exportPDF = document.getElementById("exportPDF");
const exportImage = document.getElementById("exportImage");
let viz;

const url = "https://public.tableau.com/shared/3CF6NNNYR?:display_count=n&:origin=viz_share_link";
const options = {
    hideTabs: true,
    height: 800,
    width: 1000,
    device: "desktop",
    onFirstInteractive: function() {
        console.log("dashboard is ready");
    },
    onFirstVizSizeKnown: function() {
        console.log("hey my dashboard has a size")
    }
};

function initViz() {
    viz = new tableau.Viz (containerDiv, url, options)
}

document.addEventListener('DOMContentLoaded', initViz)
exportPDF.addEventListener('click', function() {
    viz.showExportPDFDialog();
});
exportImage.addEventListener('click', function() {
    viz.showExportImageDialog();
});