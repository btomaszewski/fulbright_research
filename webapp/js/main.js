//const path = require('path');
//const fs = require('fs');
//const { GoogleSpreadsheet } = require('google-spreadsheet');
//const { JWT } = require('google-auth-library');
//require('dotenv').config();


const status = document.getElementById('processing-status');

document.getElementById('addNew').addEventListener('click', async () => {
    const dirPath = await ipcRenderer.invoke('select-directory');
    if (dirPath) {
        addDatasetToList(dirPath);
    }
});

document.getElementById('process').addEventListener('click', async () => {
    status.innerText = "Processing...";
    try {
        const result = await ipcRenderer.invoke('process-json');
        status.innerText = "Processing completed: " + result;
    } catch (error) {
        status.innerText = "Error: " + error;
    }
});

function addDatasetToList(dirPath) {
    const dirName = path.basename(dirPath);
    const ul = document.getElementById('datasetList');
    const li = document.createElement('li');
    const sendFB = document.createElement('button');
    sendFB.setAttribute('id', "sendFB");
    sendFB.innerHTML = "Upload";

    let normalizedPath = path.normalize(dirPath);
    const parentDir = path.dirname(normalizedPath);
    const grandparentDir = path.dirname(parentDir);
    const filePath = path.join(grandparentDir, "processedJson", dirName, "result.json");
    sendFB.addEventListener("click", function () {
        uploadToGoogleSheets(filePath);
    });
    li.appendChild(sendFB);

    li.appendChild(document.createTextNode(dirName));
    li.dataset.path = dirPath;
    li.setAttribute('class', 'dataset-item');

    // Right-click context menu
    li.addEventListener('contextmenu', (event) => {
        event.preventDefault();
        ipcRenderer.send('show-context-menu', dirPath, dirName);
    });

    ul.appendChild(li);
}

ipcRenderer.on('load-datasets', (event, datasets) => {
    datasets.forEach(addDatasetToList);
});

ipcRenderer.on('delete-dataset', (event, deletedPath) => {
    const items = document.querySelectorAll('#datasetList li');
    items.forEach((li) => {
        if (li.dataset.path === deletedPath) {
            li.remove();
        }
    });
});

// Function to upload JSON data from file to Google Sheets
async function uploadToGoogleSheets(filePath) {
    try {
        // Initialize the Google Spreadsheet
        // Read the credentials from the .env file
        const serviceAccount = new JWT({
            email: process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL,
            key: process.env.GOOGLE_PRIVATE_KEY,
            scopes: [
                'https://www.googleapis.com/auth/spreadsheets',
            ],
        });
        const doc = new GoogleSpreadsheet('14KErbuI8nk2_69MdvU0Qycdm4kuWlfsAWehyy2F3ZEw', serviceAccount);
        // Load the spreadsheet and get the first sheet
        await doc.loadInfo();
        status.innerHTML += 'loaded';

        if (doc.sheetsByIndex.length === 0) {
            status.innerHTML += 'No sheets found in the document.';
        } else {
            status.innerHTML += 'sheet exists';
        }
        const sheet = doc.sheetsByIndex[0]; // Assuming the first sheet is where we want to add data
        status.innerHTML += sheet;

        // Read the content of the file (assuming it's a JSON file)
        const fileData = fs.readFileSync(filePath, 'utf-8');
        const jsonData = JSON.parse(fileData);

        // If data exists, push it to the Google Sheet
        if (jsonData) {
            const rows = [];
            for (const key in jsonData) {
                rows.push(Object.values(jsonData[key])); // Flatten nested data if necessary
            }

            // Set headers and add data to the sheet
            await sheet.setHeaderRow(Object.keys(jsonData));  // Setting headers from keys of JSON
            await sheet.addRows(rows);  // Add the rows to the sheet
            status.innerHTML += `✅ Data from ${filePath} exported to Google Sheets!`;
        } else {
            status.innerHTML += 'No data found in the file';
        }
    } catch (error) {
        status.innerHTML += `Error exporting data to Google Sheets: ${error}`;
    }
}