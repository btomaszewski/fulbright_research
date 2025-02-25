const { app, BrowserWindow, dialog, ipcMain, Menu } = require('electron');
const path = require('path');
const fs = require('fs');
const { execFile, spawn } = require("child_process");
const os = require("os");
const { GoogleSpreadsheet } = require('google-spreadsheet');
const { JWT } = require('google-auth-library');
require("dotenv").config();

// Track spawned processes for cleanup
let pythonProcesses = [];

// Load environment variables
const envVars = {
    OPENAI_API_KEY: process.env.OPENAI_API_KEY,
    GOOGLE_CREDENTIALS_PATH: process.env.GOOGLE_CREDENTIALS_PATH,
    GOOGLE_SHEET_ID: process.env.GOOGLE_SHEET_ID
};

// Validate required environment variables
function validateEnvironmentVars() {
    const requiredEnvVars = ['OPENAI_API_KEY', 'GOOGLE_CREDENTIALS_PATH', 'GOOGLE_SHEET_ID'];
    const missingVars = requiredEnvVars.filter(varName => !envVars[varName]);
    
    if (missingVars.length > 0) {
        const errorMessage = `Missing required environment variables: ${missingVars.join(', ')}`;
        console.error(errorMessage);
        return false;
    }
    return true;
}

// Application paths
const userDataPath = app.getPath('userData');
const rawJsonPath = path.join(userDataPath, 'processing', 'rawJson');
const procJsonPath = path.join(userDataPath, 'processing', 'processedJson');

// Helper function to show errors to users
function showErrorToUser(title, message) {
    if (mainWindow && !mainWindow.isDestroyed()) {
        dialog.showErrorBox(title, message);
    }
    console.error(`${title}: ${message}`);
}

// Get platform-specific executable path
function getPythonExecutablePath() {
    const isPackaged = app.isPackaged;
    let platformDir;
    let executableName = 'processJson';
    
    if (process.platform === 'darwin') {
        platformDir = 'dist-darwin';
        // Keep as is for macOS
    } else if (process.platform === 'win32') {
        platformDir = 'dist-win32';
        executableName = 'processJson.exe';
    } else {
        platformDir = 'dist-linux';
    }
    
    let basePath;
    if (isPackaged) {
        // In packaged app, use resources path
        basePath = path.join(process.resourcesPath, 'assets', platformDir);
    } else {
        // In development, use app directory
        basePath = path.join(app.getAppPath(), 'assets', platformDir);
    }
    
    const executablePath = path.join(basePath, executableName);
    console.log(`Using Python executable path: ${executablePath}`);
    
    // Check if executable exists
    if (!fs.existsSync(executablePath)) {
        const errorMsg = `Python executable not found at: ${executablePath}`;
        console.error(errorMsg);
        throw new Error(errorMsg);
    }
    
    // Set executable permissions on Unix-like systems
    if (process.platform !== 'win32') {
        try {
            fs.chmodSync(executablePath, '755');
            console.log(`Set executable permissions on ${executablePath}`);
        } catch (err) {
            console.error(`Error setting permissions: ${err.message}`);
        }
    }
    
    return executablePath;
}

let mainWindow;

function createAppDirectories() {
    try {
        [rawJsonPath, procJsonPath].forEach(dir => {
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
                console.log(`Created directory: ${dir}`);
            } else {
                console.log(`Directory already exists: ${dir}`);
            }
        });
        console.log('All application directories created successfully.');
    } catch (error) {
        console.error('Error creating application directories:', error);
        showErrorToUser('Directory Creation Error', 
            `Failed to create application directories: ${error.message}`);
    }
}

function createMainWindow() {
    try {
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
            try {
                const datasets = fs.readdirSync(rawJsonPath)
                    .map(dir => path.join(rawJsonPath, dir));
                mainWindow.webContents.send('load-datasets', datasets);
            } catch (error) {
                console.error(`Error loading datasets: ${error.message}`);
                mainWindow.webContents.send('load-datasets', []);
            }
        });
        
        // Enable developer tools in development mode
        if (!app.isPackaged) {
            mainWindow.webContents.openDevTools();
        }

        mainWindow.on('closed', () => {
            mainWindow = null;
        });
    } catch (error) {
        console.error(`Error creating main window: ${error.message}`);
    }
}

// Initialize Python process with environment variables
function initializePythonProcess() {
    try {
        const executablePath = getPythonExecutablePath();
        console.log(`Initializing Python process with executable: ${executablePath}`);

        const child = execFile(executablePath, [], { 
            env: {...process.env, ...envVars},
            cwd: path.dirname(executablePath) // Set working directory to executable's directory
        }, (error, stdout, stderr) => {
            if (error) {
                console.error(`Python process error: ${error.message}`);
                return;
            }
            console.log(`Python Output: ${stdout}`);
        });

        pythonProcesses.push(child);

        child.on('error', (error) => {
            console.error(`Failed to start Python process: ${error.message}`);
            showErrorToUser('Python Process Error', `Failed to start Python process: ${error.message}`);
        });
    } catch (error) {
        console.error(`Error in initializePythonProcess: ${error.message}`);
        showErrorToUser('Python Initialization Error', error.message);
    }
}

// Google Sheets upload functionality
async function uploadToGoogleSheets(filePath) {
    try {
        // Validate filePath is a string
        if (typeof filePath !== 'string') {
            throw new Error(`Invalid filePath: expected string but got ${typeof filePath}`);
        }
        
        // Check if file exists
        if (!fs.existsSync(filePath)) {
            throw new Error(`File does not exist at path: ${filePath}`);
        }

        // Check if Google credentials exist
        if (!fs.existsSync(envVars.GOOGLE_CREDENTIALS_PATH)) {
            throw new Error(`Google credentials file not found at: ${envVars.GOOGLE_CREDENTIALS_PATH}`);
        }

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
            if (message.CATEGORIES && Array.isArray(message.CATEGORIES.categories)) {
                message.CATEGORIES.categories.forEach(cat => {
                    headers.add(`CAT_${cat}`);
                });
            }
        });

        const headersArray = Array.from(headers);

        // Convert messages to rows
        const values = messages.map(message => {
            return headersArray.map(header => {
                if (header.startsWith("CAT_")) {
                    const category = header.replace("CAT_", "");
                    const categories = message.CATEGORIES?.categories || [];
                    const index = categories.indexOf(category);
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
        throw new Error(`Failed to upload to Google Sheets: ${error.message}, ${filePath}`);
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
                    try {
                        fs.rmSync(datasetPath, { recursive: true, force: true });
                        mainWindow.webContents.send('delete-dataset', datasetPath);
                    } catch (error) {
                        console.error(`Error deleting dataset: ${error.message}`);
                        showErrorToUser('Delete Error', `Failed to delete dataset: ${error.message}`);
                    }
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
        
        try {
            fs.cpSync(selectedDir, targetDir, { recursive: true });
            return targetDir;
        } catch (error) {
            console.error(`Error copying directory: ${error.message}`);
            showErrorToUser('Directory Copy Error', `Failed to copy directory: ${error.message}`);
            return null;
        }
    } catch (error) {
        console.error('Directory selection error:', error);
        return null;
    }
});

// IPC Handlers
ipcMain.handle('process-json', async (event, chatDir) => {
    return new Promise((resolve, reject) => {
        try {
            const executablePath = getPythonExecutablePath();
            console.log(`Running Python process with executable: ${executablePath}`);
            console.log(`Input directory: ${chatDir}`);
            console.log(`Output directory: ${procJsonPath}`);
            
            const pythonProcess = spawn(executablePath, [chatDir, procJsonPath], {
                env: {...process.env, ...envVars},
                cwd: path.dirname(executablePath)
            });

            pythonProcesses.push(pythonProcess);

            let output = "";
            let errorOutput = "";

            pythonProcess.stdout.on('data', (data) => {
                const message = data.toString();
                console.log(`Python stdout: ${message}`);
                output += message;
            });

            pythonProcess.stderr.on('data', (data) => {
                const message = data.toString();
                console.error(`Python stderr: ${message}`);
                errorOutput += message;
            });

            pythonProcess.on('close', (code) => {
                console.log(`Python process exited with code ${code}`);
                if (code === 0) {
                    resolve(output.trim());
                } else {
                    reject(`Process exited with code ${code}: ${errorOutput.trim()}`);
                }
            });

            pythonProcess.on('error', (error) => {
                reject(`Failed to start Python process: ${error.message}`);
            });
        } catch (error) {
            reject(`Error in process-json handler: ${error.message}`);
        }
    });
});

ipcMain.handle('upload-to-google-sheets', async (event, filePath) => {
    try {
        return await uploadToGoogleSheets(filePath);
    } catch (error) {
        showErrorToUser('Upload Error', error.message);
        throw error;
    }
});

// Clean up resources before quitting
app.on('before-quit', () => {
    console.log('Cleaning up resources before quitting...');
    pythonProcesses.forEach(process => {
        if (process && !process.killed) {
            process.kill();
            console.log('Killed a Python process');
        }
    });
});

// App lifecycle
app.whenReady().then(() => {
    try {
        const envValid = validateEnvironmentVars();
        if (!envValid && !app.isPackaged) {
            dialog.showMessageBox({
                type: 'warning',
                title: 'Environment Variables Missing',
                message: 'Some required environment variables are missing. Some features may not work correctly.',
                buttons: ['Continue Anyway']
            });
        }
        
        createAppDirectories();
        createMainWindow();
        initializePythonProcess();
    } catch (error) {
        console.error(`Error during app initialization: ${error.message}`);
        showErrorToUser('Initialization Error', `Failed to initialize app: ${error.message}`);
    }
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

