const { app, BrowserWindow, dialog, ipcMain, Menu } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const { execFile } = require("child_process");
const os = require("os");
const { GoogleSpreadsheet } = require('google-spreadsheet');
const { JWT } = require('google-auth-library');
require("dotenv").config();

// Load all environment variables at runtime
const envVars = {
    API_KEY: process.env.OPENAI_API_KEY,
    GOOGLE_CREDENTIALS_PATH: process.env.GOOGLE_CREDENTIALS_PATH,
    GOOGLE_SHEET_ID: process.env.GOOGLE_SHEET_ID
};

// Application paths
const userDataPath = app.getPath('userData');
const rawJsonPath = path.join(userDataPath, 'processing/rawJson');
const procJsonPath = path.join(userDataPath, 'processing/processedJson');
const pythonScriptPath = 'assets/python/processJson.py';

// Get platform-specific executable path
function getPythonExecutablePath() {
    const platform = os.platform();
    const scriptName = {
        "win32": "processJson.exe",
        "darwin": "processJson-mac",
        "linux": "processJson-linux"
    }[platform] || "processJson-linux";

    return path.join(__dirname, "assets", "python-scripts", scriptName);
}

let mainWindow;

function createAppDirectories() {
    [rawJsonPath, procJsonPath].forEach(dir => {
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
            console.log(`Created directory: ${dir}`);
        }
    });
}

function createMainWindow() {
    const { screen } = require('electron');
    const { width, height } = screen.getPrimaryDisplay().workAreaSize;
    
    mainWindow = new BrowserWindow({
        width: width,
        height: height,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false,
        }
    });

    mainWindow.loadFile('frontend/index.html');

    mainWindow.webContents.once('did-finish-load', () => {
        const datasets = fs.readdirSync(rawJsonPath)
            .map(dir => path.join(rawJsonPath, dir));
        mainWindow.webContents.send('load-datasets', datasets);
    });
}

// Initialize Python process with environment variables
function initializePythonProcess() {
    const scriptPath = getPythonExecutablePath();
    console.log(`Initializing Python process with script: ${scriptPath}`);

    const child = execFile(scriptPath, [], { env: envVars }, (error, stdout, stderr) => {
        if (error) {
            console.error(`Python process error: ${error.message}`);
            return;
        }
        console.log(`Python Output: ${stdout}`);
    });

    child.on('error', (error) => {
        console.error(`Failed to start Python process: ${error.message}`);
    });
}

// Google Sheets upload functionality
async function uploadToGoogleSheets(filePath) {
    try {
        // Read credentials at runtime
        const creds = JSON.parse(fs.readFileSync(envVars.GOOGLE_CREDENTIALS_PATH, 'utf-8'));
        
        const serviceAccount = new JWT({
            email: creds.client_email,
            key: creds.private_key,
            scopes: ['https://www.googleapis.com/auth/spreadsheets'],
        });

        const doc = new GoogleSpreadsheet(envVars.GOOGLE_SHEET_ID, serviceAccount);
        await doc.loadInfo();

        const fileData = fs.readFileSync(filePath, 'utf-8');
        if (!fileData) {
            throw new Error('File is empty');
        }

        const jsonData = JSON.parse(fileData);
        if (!jsonData.messages || !Array.isArray(jsonData.messages)) {
            throw new Error('"messages" key is missing or not an array');
        }

        const messages = jsonData.messages;
        if (messages.length === 0) {
            throw new Error('"messages" array is empty');
        }

        const sheetName = String(jsonData.id);

        // Extract headers
        const headers = new Set([
            "id", "date", "from", "text", "reply_id", "LANGUAGE", "TRANSLATED_TEXT"
        ]);

        // Collect category fields
        messages.forEach(message => {
            message.CATEGORIES.categories.forEach(cat => {
                headers.add(`CAT_${cat}`);
            });
        });

        const headersArray = Array.from(headers);

        // Convert messages to rows
        const values = messages.map(message => {
            return headersArray.map(header => {
                if (header.startsWith("CAT_")) {
                    const category = header.replace("CAT_", "");
                    const index = message.CATEGORIES.categories.indexOf(category);
                    return (index !== -1 && message.CONFIDENCE?.[index] !== undefined)
                        ? message.CONFIDENCE[index].toFixed(2)
                        : "";
                }
                return message[header] || "";
            });
        });

        // Manage sheet
        const existingSheet = doc.sheetsByTitle[sheetName];
        if (existingSheet) {
            await existingSheet.delete();
        }
        const newSheet = await doc.addSheet({ title: sheetName, headerValues: headersArray });
        await newSheet.addRows(values);

        return 'Upload successful';
    } catch (error) {
        console.error('Upload error:', error);
        throw new Error(`Failed to upload to Google Sheets: ${error.message}`);
    }
}

// IPC Handlers
ipcMain.on('show-context-menu', (event, datasetPath, datasetName) => {
    const template = [{
        label: 'Delete',
        click: () => {
            dialog.showMessageBox(mainWindow, {
                type: 'warning',
                buttons: ['Cancel', 'Delete'],
                defaultId: 1,
                title: 'Delete Dataset',
                message: `Are you sure you want to delete ${datasetName}?`,
            }).then(({ response }) => {
                if (response === 1) {
                    fs.rmSync(datasetPath, { recursive: true, force: true });
                    mainWindow.webContents.send('delete-dataset', datasetPath);
                }
            });
        }
    }];

    Menu.buildFromTemplate(template).popup({ window: mainWindow });
});

ipcMain.handle('select-directory', async () => {
    try {
        const result = await dialog.showOpenDialog(mainWindow, {
            properties: ['openDirectory']
        });

        if (!result.filePaths.length) return null;

        const selectedDir = result.filePaths[0];
        const targetDir = path.join(rawJsonPath, path.basename(selectedDir));
        
        fs.cpSync(selectedDir, targetDir, { recursive: true });
        return targetDir;
    } catch (error) {
        console.error('Directory selection error:', error);
        return null;
    }
});

ipcMain.handle('process-json', async (event, chatDir) => {
    return new Promise((resolve, reject) => {
        const pythonProcess = spawn('python', [pythonScriptPath, chatDir, procJsonPath]);
        
        let output = "";
        let errorOutput = "";

        pythonProcess.stdout.on('data', (data) => output += data.toString());
        pythonProcess.stderr.on('data', (data) => errorOutput += data.toString());
        
        pythonProcess.on('close', (code) => {
            if (code === 0) {
                resolve(output.trim());
            } else {
                reject(errorOutput.trim());
            }
        });

        pythonProcess.on('error', (error) => {
            reject(`Failed to start Python process: ${error.message}`);
        });
    });
});

ipcMain.handle('upload-to-google-sheets', async (event, filePath) => {
    return await uploadToGoogleSheets(filePath);
});

// App lifecycle
app.whenReady().then(() => {
    createAppDirectories();
    createMainWindow();
    initializePythonProcess();
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createMainWindow();
    }
});

