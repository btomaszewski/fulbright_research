const containerDiv = document.getElementById("vizContainer");
const showBtn = document.getElementById("showBtn");
const hideBtn = document.getElementById("hideBtn");
const exportPDF = document.getElementById("exportPDF");
const exportImage = document.getElementById("exportImage");
let viz;

const url = "https://public.tableau.com/views/LearnEmbeddedAnalytics/SalesOverviewDashboard";
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
showBtn.addEventListener('click', function() {
    viz.show();
});
hideBtn.addEventListener('click', function() {
    viz.hide();
});
exportPDF.addEventListener('click', function() {
    viz.showExportPDFDialog();
});
exportImage.addEventListener('click', function() {
    viz.showExportImageDialog();
});

function getRangeValues() {
    const minValue = document.getElementById('minValue').value;
    const maxValue = document.getElementById('maxValue').value;
    
    const workbook = viz.getWorkbook();
    const activeSheet = workbook.getActiveSheet();
    const sheets = activeSheet.getWorksheets();
    const sheetsToFilter = sheets[1];
    sheetsToFilter.applyRangeFilterAsync("Sales", {
        min: minValue, 
        max: maxValue
    })
    
    .then(console.log('Filter applied'));
}

document.getElementById('applyFilter').addEventListener('click', function() {
    getRangeValues();
})