const { app, BrowserWindow, dialog, ipcMain, Menu } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');


const userDataPath = app.getPath('userData');
const rawJsonPath = path.join(userDataPath, 'processing/rawJson');
const procJsonPath = path.join(userDataPath, 'processing/processedJson');

let mainWindow;

app.whenReady().then(() => {
    const { screen } = require('electron');  // Get screen dimensions
    const primaryDisplay = screen.getPrimaryDisplay();
    const { width, height } = primaryDisplay.workAreaSize;
    
    mainWindow = new BrowserWindow({
        width: width,
        height: height,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false,
        }
    });
    mainWindow.loadFile('index.html');
    createAppDirectories();

    mainWindow.webContents.once('did-finish-load', () => {
        const datasets = fs.readdirSync(rawJsonPath).map(dir => path.join(rawJsonPath, dir));
        mainWindow.webContents.send('load-datasets', datasets);
    });
});

const createAppDirectories = () => {
    if (!fs.existsSync(rawJsonPath)) {
        fs.mkdirSync(rawJsonPath, { recursive: true });
        console.log(`Created directory: ${rawJsonPath}`);
    }
    if (!fs.existsSync(procJsonPath)) {
      fs.mkdirSync(procJsonPath, { recursive: true });
      console.log(`Created directory: ${procJsonPath}`);
  }
};

// Context menu for renaming and deleting
ipcMain.on('show-context-menu', (event, datasetPath, datasetName) => {
    const template = [
        {
            label: 'Delete',
            click: () => {
                dialog.showMessageBox(mainWindow, {
                    type: 'warning',
                    buttons: ['Cancel', 'Delete'],
                    defaultId: 1,
                    title: 'Delete Dataset',
                    message: `Are you sure you want to delete ${datasetName}? This action cannot be undone.`,
                }).then(({ response }) => {
                    if (response === 1) {
                        fs.rmSync(datasetPath, { recursive: true, force: true });
                        mainWindow.webContents.send('delete-dataset', datasetPath);
                    }
                });
            }
        }
    ];

    const menu = Menu.buildFromTemplate(template);
    menu.popup({ window: mainWindow });
});

ipcMain.handle('select-directory', async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openDirectory']
    });
    if (result.filePaths.length > 0) {
        const selectedDir = result.filePaths[0];
        const targetDir = path.join(rawJsonPath, path.basename(selectedDir));

        try {
            fs.cpSync(selectedDir, targetDir, { recursive: true });
            return targetDir;
        } catch (error) {
            console.error('Error copying directory:', error);
            return null;
        }
    }
    return null;
});

pythonScriptPath = './assets/processJson.py'

// Handle processing datasets with processJson.py
ipcMain.handle('process-json', async (event, chatDir) => {
    return new Promise((resolve, reject) => {
        const pythonProcess = spawn('python', [pythonScriptPath, chatDir, procJsonPath]);

        let output = "";
        let errorOutput = "";

        pythonProcess.stdout.on('data', (data) => {
            output += data.toString();
        });

        pythonProcess.stderr.on('data', (data) => {
            errorOutput += data.toString();
        });

        pythonProcess.on('close', (code) => {
            if (code === 0) {
                resolve(output.trim());
            } else {
                reject(errorOutput.trim());
            }
        });
    });
});



// main.js (Main Process)
require('dotenv').config();
const { GoogleSpreadsheet } = require('google-spreadsheet');
const { JWT } = require('google-auth-library');

const credsPath = process.env.GOOGLE_CREDENTIALS_PATH;
if (!credsPath) {
    console.error("Error: GOOGLE_CREDENTIALS_PATH is not set in .env");
    process.exit(1);
}

const creds = JSON.parse(fs.readFileSync(credsPath, 'utf-8'));

async function uploadToGoogleSheets(filePath) {
    try {
        const serviceAccount = new JWT({
            email: creds.client_email,
            key: creds.private_key,
            scopes: ['https://www.googleapis.com/auth/spreadsheets'],
        });

        const doc = new GoogleSpreadsheet('14KErbuI8nk2_69MdvU0Qycdm4kuWlfsAWehyy2F3ZEw', serviceAccount);
        await doc.loadInfo();

        if (doc.sheetsByIndex.length === 0) {
            return 'No sheets found in the document.';
        }

        const fileData = fs.readFileSync(filePath, 'utf-8');

        if (!fileData) {
            return '❌ Error: File is empty!';
        }

        let jsonData;
        try {
            jsonData = JSON.parse(fileData);
        } catch (parseError) {
            return `❌ Error: Invalid JSON format - ${parseError.message}`;
        }

         // ✅ Extract "messages" array from JSON object
         if (!jsonData.messages || !Array.isArray(jsonData.messages)) {
            return '❌ Error: "messages" key is missing or not an array.';
        }
        const messages = jsonData.messages;

        if (messages.length === 0) {
            return '❌ Error: "messages" array is empty.';
        }

        // ✅ Extract headers dynamically from the first message
        const headers = Object.keys(messages[0]);
        const rows = messages.map(msg => headers.map(header => msg[header] || ''));

        // ✅ Generate sheet name: Last directory + Timestamp
        const dirName = path.basename(path.dirname(filePath)); // Extracts the last directory name
        const timestamp = new Date().toISOString().replace(/[-T:.Z]/g, '_'); // Formats timestamp
        const sheetName = `${dirName}_${timestamp}`.substring(0, 100); // Limit to 100 chars (Google Sheets limit)

        // ✅ Create a new sheet with the generated name
        const sheet = await doc.addSheet({ title: sheetName, headerValues: headers });

        // ✅ Add rows to the new sheet
        await sheet.addRows(rows);

        return `✅ Data from ${filePath} exported to Google Sheets in a new sheet: ${sheetName}!`;

    } catch (error) {
        return `Error exporting data to Google Sheets: ${error}`;
    }
}


// Handle upload request from the renderer process
ipcMain.handle('upload-to-google-sheets', async (event, filePath) => {
    return await uploadToGoogleSheets(filePath);
});


