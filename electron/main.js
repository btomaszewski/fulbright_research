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

require("dotenv").config();  // Load .env file
const { execFile } = require("child_process");
const path = require("path");
const os = require("os");

const API_KEY = process.env.OPENAI_API_KEY;  // Load API key securely

let scriptPath;
if (os.platform() === "win32") {
  scriptPath = path.join(__dirname, "python-scripts", "main-win.exe");
} else if (os.platform() === "darwin") {
  scriptPath = path.join(__dirname, "python-scripts", "main-mac");
} else {
  scriptPath = path.join(__dirname, "python-scripts", "main-linux");
}

// Run Python script and inject API key securely
const processEnv = { API_KEY };

const child = execFile(scriptPath, [], { env: processEnv }, (error, stdout, stderr) => {
  if (error) {
    console.error(`Error: ${error.message}`);
    return;
  }
  console.log(`Python Output: ${stdout}`);
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

pythonScriptPath = 'assets/python/processJson.py'

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

        const fileData = fs.readFileSync(filePath, 'utf-8');
        if (!fileData) return '❌ Error: File is empty!';

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
        if (messages.length === 0) return '❌ Error: "messages" array is empty.';

        // ✅ Extract base sheet id from "id" key
        if (!jsonData.id) return '❌ Error: JSON file lacks a "name" field.';
        const sheetName = String(jsonData.id);

        // ✅ Extract headers dynamically
        const headers = new Set([
            "id", "date", "from", "text", "reply_id", "LANGUAGE", "TRANSLATED_TEXT"
        ]);

        // Collect all possible category fields dynamically
        messages.forEach(message => {
            let cats = message.CATEGORIES.categories;
            cats.forEach(cat => {
                if (!headers.has(cat)) {
                    headers.add(`CAT_${cat}`)
                }
            })
        });

        const headersArray = Array.from(headers);

        // ✅ Convert message objects to rows
        const values = messages.map(message => {
            return headersArray.map(header => {
                if (header.startsWith("CAT_")) {
                    // Extract category name from header (remove "CAT_" prefix)
                    const category = header.replace("CAT_", "");
                    
                    // Find the index of this category in the message's CATEGORIES array
                    const index = message.CATEGORIES ? message.CATEGORIES.categories.indexOf(category) : -1;
                    
                    // If category exists, get the corresponding confidence score
                    return index !== -1 && message.CONFIDENCE && message.CONFIDENCE[index] !== undefined
                        ? message.CONFIDENCE[index].toFixed(2)  // Format to 2 decimal places
                        : "";
                } else {
                    // Default case: return message field if it exists, otherwise empty string
                    return message[header] || "";
                }
            });
        });


        // ✅ Create a new sheet before uploading data
        const existingSheet = doc.sheetsByTitle[sheetName];
        if (existingSheet) {
            await existingSheet.delete(); // ✅ Delete existing sheet
        }
        const newSheet = await doc.addSheet({ title: sheetName, headerValues: headersArray });

        // ✅ Upload data to the newly created sheet
        await newSheet.addRows(values);

    } catch (error) {
        return `Error exporting data to Google Sheets: ${error}`;
    }
}


// Handle upload request from the renderer process
ipcMain.handle('upload-to-google-sheets', async (event, filePath) => {
    return await uploadToGoogleSheets(filePath);
});


