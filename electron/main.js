const { app, BrowserWindow, dialog, ipcMain, Menu } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require("child_process");
const os = require("os");
const { GoogleSpreadsheet } = require('google-spreadsheet');
const { JWT } = require('google-auth-library');
require("dotenv").config();

// Track spawned processes for cleanup 
let pythonProcesses = [];

// User credentials container - will be populated via UI
let userCredentials = {
    OPENAI_API_KEY: process.env.OPENAI_API_KEY || null,
    GOOGLE_CREDENTIALS_PATH: process.env.GOOGLE_CREDENTIALS_PATH || null,
    GOOGLE_SHEET_ID: process.env.GOOGLE_SHEET_ID || null,
    GOOGLE_CREDENTIALS_JSON: null // Will hold the actual JSON content
};

// Application paths
const userDataPath = app.getPath('userData');
const rawJsonPath = path.join(userDataPath, 'processing', 'rawJson');
const procJsonPath = path.join(userDataPath, 'processing', 'processedJson');

// Add this near the top of main.js, after your requires
/*app.whenReady().then(() => {
    const userDataPath = app.getPath('userData');
    console.log('Clearing app data from:', userDataPath);
    try {
      require('fs').rmSync(userDataPath, { recursive: true, force: true });
      console.log('App data cleared successfully');
    } catch (err) {
      console.error('Failed to clear app data:', err);
    }
    
    // Continue with normal app initialization after clearing
    createAppDirectories();
    createMainWindow();
    
    // Other initialization code...
  });  */

// Path to Python executable - now using the PyInstaller executable
const getPythonExecutablePath = () => {
    // First try to get the path from electron-assets.json
    try {
        const assetsFilePath = path.join(app.getAppPath(), 'assets/electron-assets.json');
        console.log('Looking for electron-assets.json at:', assetsFilePath);
        
        if (fs.existsSync(assetsFilePath)) {
            console.log('Found electron-assets.json, reading executable path');
            const assetsData = JSON.parse(fs.readFileSync(assetsFilePath, 'utf8'));
            
            if (assetsData.pyInstaller && assetsData.pyInstaller.executablePath) {
                const execPath = path.join(app.getAppPath(), assetsData.pyInstaller.executablePath);
                console.log('Using executable path from assets file:', execPath);
                
                // Check if the file exists at this path
                if (fs.existsSync(execPath)) {
                    return execPath;
                } else {
                    console.error(`Executable not found at path from assets file: ${execPath}`);
                    // Continue to fallback
                }
            }
        } else {
            console.error('electron-assets.json not found at:', assetsFilePath);
        }
    } catch (error) {
        console.error('Error reading electron-assets.json:', error);
        // Continue to fallback method
    }
    
    // Fallback to hardcoded paths if electron-assets.json doesn't provide the path
    console.log('Using hardcoded executable path');
    const platform = process.platform;
    let executablePath;
    
    if (platform === 'darwin') {
        // Try multiple potential locations in order of likelihood
        const possiblePaths = [
            path.join(app.getAppPath(), 'dist-darwin', 'processJson'),
            path.join(app.getAppPath(), 'assets', 'dist-darwin', 'processJson'),
            path.join(__dirname, 'dist-darwin', 'processJson'),
            path.join(__dirname, 'assets', 'dist-darwin', 'processJson')
        ];
        
        for (const testPath of possiblePaths) {
            console.log('Testing path:', testPath);
            if (fs.existsSync(testPath)) {
                console.log('Found executable at:', testPath);
                executablePath = testPath;
                break;
            }
        }
        
        if (!executablePath) {
            console.error('Could not find executable at any expected path');
            executablePath = path.join(app.getAppPath(), 'dist-darwin', 'processJson');
        }
    } else if (platform === 'win32') {
        executablePath = path.join(app.getAppPath(), 'dist-win32', 'processJson.exe');
    } else if (platform === 'linux') {
        executablePath = path.join(app.getAppPath(), 'dist-linux', 'processJson');
    } else {
        throw new Error(`Unsupported platform: ${platform}`);
    }
    
    console.log('Final executable path:', executablePath);
    return executablePath;
};

// Validate credentials
function validateCredentials() {
    const requiredCredentials = ['OPENAI_API_KEY', 'GOOGLE_SHEET_ID'];
    const missingCreds = requiredCredentials.filter(cred => !userCredentials[cred]);
    
    if (missingCreds.length > 0 || (!userCredentials.GOOGLE_CREDENTIALS_PATH && !userCredentials.GOOGLE_CREDENTIALS_JSON)) {
        console.log('Credential validation failed. Missing:', missingCreds.join(', '));
        console.log('Google creds:', !!userCredentials.GOOGLE_CREDENTIALS_PATH || !!userCredentials.GOOGLE_CREDENTIALS_JSON);
        return false;
    }
    return true;
}

// Helper function to show errors to users
function showErrorToUser(title, message) {
    if (mainWindow && !mainWindow.isDestroyed()) {
        dialog.showErrorBox(title, message);
    }
    console.error(`${title}: ${message}`);
}

let mainWindow;
let credentialsWindow = null;

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
        },
        show: false // Keep this to not show until credentials are verified
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
        
        // Always open DevTools for local development
        mainWindow.webContents.openDevTools();

        mainWindow.on('closed', () => {
            mainWindow = null;
        });

        // First check if we have stored credentials
        if (!validateCredentials()) {
            createCredentialsWindow();
        } else {
            mainWindow.show();
        }
    } catch (error) {
        console.error(`Error creating main window: ${error.message}`);
    }
}

function createCredentialsWindow() {
    console.log('CREATING CREDENTIALS WINDOW');
    
    if (credentialsWindow) {
      console.log('Credentials window already exists, focusing it');
      credentialsWindow.focus();
      return;
    }
  
    // Check if frontend/credentials.html exists
    const credentialsPath = path.join(app.getAppPath(), 'frontend', 'credentials.html');
    console.log('Looking for credentials HTML at:', credentialsPath);
    
    if (!fs.existsSync(credentialsPath)) {
      console.error('CRITICAL ERROR: credentials.html file not found at', credentialsPath);
      dialog.showErrorBox('Missing File', `The credentials.html file is missing at ${credentialsPath}`);
      return;
    }
  
    console.log('credentials.html file found, creating window');
    
    credentialsWindow = new BrowserWindow({
      width: 600,
      height: 600,
      parent: mainWindow,
      modal: true,
      webPreferences: {
        nodeIntegration: true,
        contextIsolation: false,
      }
    });
  
    // Force DevTools to open in credentials window
    credentialsWindow.webContents.openDevTools();
  
    console.log('Loading credentials.html into window');
    credentialsWindow.loadFile('frontend/credentials.html');
    
    credentialsWindow.webContents.on('did-finish-load', () => {
      console.log('SUCCESS: Credentials window loaded successfully');
    });
    
    credentialsWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
      console.error('FAILED: Credentials window failed to load:', errorDescription);
    });
    
    credentialsWindow.on('closed', () => {
      console.log('Credentials window closed');
      credentialsWindow = null;
    });
  }

// Check if Python executable exists
function checkPythonExecutable() {
    try {
        const execPath = getPythonExecutablePath();
        if (!fs.existsSync(execPath)) {
            const errorMsg = `Python executable not found at: ${execPath}`;
            console.error(errorMsg);
            return false;
        }
        
        console.log(`Python executable found at: ${execPath}`);
        // Make executable (chmod +x) for macOS and Linux with more verbose output
        if (process.platform !== 'win32') {
            try {
                fs.chmodSync(execPath, '755');
                console.log(`Successfully set executable permissions on: ${execPath}`);
                
                // Verify permissions were set correctly
                const stats = fs.statSync(execPath);
                const octalPermissions = '0' + (stats.mode & parseInt('777', 8)).toString(8);
                console.log(`Permissions on executable: ${octalPermissions}`);
                
                if ((stats.mode & parseInt('111', 8)) === 0) {
                    console.error(`ERROR: Executable permissions not set correctly`);
                    return false;
                }
            } catch (permissionError) {
                console.error(`Failed to set permissions: ${permissionError}`);
                return false;
            }
        }
        return true;
    } catch (error) {
        console.error(`Error checking Python executable: ${error.message}`);
        return false;
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

        console.log(`Uploading file from: ${filePath}`);

        // Check if we have Google credentials
        if (!userCredentials.GOOGLE_CREDENTIALS_JSON && !userCredentials.GOOGLE_CREDENTIALS_PATH) {
            throw new Error(`Google credentials not available. Please provide them in the credentials form.`);
        }

        let creds;
        
        // Get credentials either from JSON content or from file
        if (userCredentials.GOOGLE_CREDENTIALS_JSON) {
            creds = userCredentials.GOOGLE_CREDENTIALS_JSON;
        } else if (fs.existsSync(userCredentials.GOOGLE_CREDENTIALS_PATH)) {
            creds = JSON.parse(fs.readFileSync(userCredentials.GOOGLE_CREDENTIALS_PATH, 'utf-8'));
        } else {
            throw new Error(`Google credentials file not found at: ${userCredentials.GOOGLE_CREDENTIALS_PATH}`);
        }
        
        const serviceAccount = new JWT({
            email: creds.client_email,
            key: creds.private_key,
            scopes: ['https://www.googleapis.com/auth/spreadsheets'],
        });

        const doc = new GoogleSpreadsheet(userCredentials.GOOGLE_SHEET_ID, serviceAccount);
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

        const sheetName = "allMessages";
        
        // Manage sheet
        let sheet = doc.sheetsByTitle[sheetName];
        if (!sheet) {
            sheet = await doc.addSheet({
                title: sheetName,
                headerValues: [
                    "id", "date", "from", "text", "reply_id", "LANGUAGE", 
                    "TRANSLATED_TEXT", "locations_names", "locations_coordinates"
                ]
            });
        }
        
        await sheet.loadCells("A:A");
        const existingIds = new Set();
        for (let row = 0; row < sheet.rowCount; row++) {
            const cell = sheet.getCell(row, 0);
            if (cell.value) {
                existingIds.add(String(cell.value));
            }
        }
        
        const newRows = messages.filter(msg => !existingIds.has(String(msg.id)))
                                .map(msg => {
                                    const locations = (msg.LOCATIONS || []).filter(loc => loc.coordinates);
                                    const locationNames = locations.map(loc => loc.name).join(", ");
                                    const locationCoords = locations
                                        .map(loc => `(${loc.coordinates.latitude}, ${loc.coordinates.longitude})`)
                                        .join("; ");
                                    
                                    return {
                                        id: msg.id || "",
                                        date: msg.date || "",
                                        from: msg.from || "",
                                        text: msg.text || "",
                                        reply_id: msg.reply_id || "",
                                        LANGUAGE: msg.LANGUAGE || "",
                                        TRANSLATED_TEXT: msg.TRANSLATED_TEXT || "",
                                        locations_names: locationNames || "",
                                        locations_coordinates: locationCoords || ""
                                    };
                                });
        
        if (newRows.length > 0) {
            await sheet.addRows(newRows);
            console.log(`Added ${newRows.length} new rows to Google Sheet`);
        } else {
            console.log('No new rows to add to Google Sheet');
        }
        
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

// New handler to check if result file exists
ipcMain.handle('check-result-file', (event, dirName) => {
    const outputDir = path.join(procJsonPath, dirName + 'Processed');
    const resultFile = path.join(outputDir, 'result.json');
    
    console.log(`Checking for file at: ${resultFile}`);
    const exists = fs.existsSync(resultFile);
    console.log(`File exists: ${exists}`);
    
    return {
        exists,
        path: resultFile,
        dirPath: outputDir,
        dirExists: fs.existsSync(outputDir)
    };
});

// Handler for processing JSON
ipcMain.handle('process-json', async (event, chatDir) => {
    return new Promise((resolve, reject) => {
        try {
            // Add log to verify this is being called
            console.log(`Starting process-json handler with chatDir: ${chatDir}`);
            
            if (!validateCredentials()) {
                console.log('Credentials validation failed');
                reject("Missing required credentials. Please provide them in the credentials form.");
                createCredentialsWindow();
                return;
            }
            
            const execPath = getPythonExecutablePath();
            if (!fs.existsSync(execPath)) {
                console.log(`Executable not found: ${execPath}`);
                reject(`Python executable not found at: ${execPath}`);
                return;
            }
            
            // Verify the directory exists
            if (!fs.existsSync(chatDir)) {
                console.error(`Input directory does not exist: ${chatDir}`);
                reject(`Input directory does not exist: ${chatDir}`);
                return;
            }
            
            // Ensure output directory exists
            const outputDirName = path.basename(chatDir) + 'Processed';
            const outputDir = path.join(procJsonPath, outputDirName);
            
            if (!fs.existsSync(outputDir)) {
                fs.mkdirSync(outputDir, { recursive: true });
                console.log(`Created output directory: ${outputDir}`);
            }
            
            console.log(`Running Python executable: ${execPath}`);
            console.log(`Input directory: ${chatDir}`);
            console.log(`Output directory: ${procJsonPath}`);
            
            // Prepare credentials JSON to pass to Python
            const credentialsJson = JSON.stringify({
                OPENAI_API_KEY: userCredentials.OPENAI_API_KEY,
                GOOGLE_SHEET_ID: userCredentials.GOOGLE_SHEET_ID,
                GOOGLE_CREDENTIALS_JSON: userCredentials.GOOGLE_CREDENTIALS_JSON
            });
            
            // Log the command being executed (redact actual credentials)
            console.log(`Command: ${execPath} [credentials] ${chatDir} ${procJsonPath}`);
            
            // Launch the Python executable with credentials and paths
            const pythonProcess = spawn(execPath, [
                credentialsJson,  // Pass credentials as first argument
                chatDir,          // Input directory as second argument
                procJsonPath      // Output directory as third argument
            ]);

            pythonProcesses.push(pythonProcess);

            let output = "";
            let errorOutput = "";

            pythonProcess.stdout.on('data', (data) => {
                const message = data.toString();
                console.log(`Python stdout: ${message}`);
                output += message;
                // Forward output to UI
                if (mainWindow && !mainWindow.isDestroyed()) {
                    mainWindow.webContents.send('python-output', message);
                }
            });

            pythonProcess.stderr.on('data', (data) => {
                const message = data.toString();
                console.error(`Python stderr: ${message}`);
                errorOutput += message;
                // Forward errors to UI
                if (mainWindow && !mainWindow.isDestroyed()) {
                    mainWindow.webContents.send('python-error', message);
                }
            });

            pythonProcess.on('close', (code) => {
                console.log(`Python process exited with code ${code}`);
                
                // Check if the expected output file was created
                const resultFile = path.join(outputDir, 'result.json');
                const resultExists = fs.existsSync(resultFile);
                console.log(`Result file exists: ${resultExists}, path: ${resultFile}`);
                
                if (code === 0) {
                    if (resultExists) {
                        resolve({
                            success: true,
                            message: output.trim(),
                            resultPath: resultFile
                        });
                    } else {
                        reject(`Process completed but result file was not created: ${resultFile}`);
                    }
                } else {
                    reject(`Process exited with code ${code}: ${errorOutput.trim()}`);
                }
            });

            pythonProcess.on('error', (error) => {
                console.error(`Failed to start Python process: ${error.message}`);
                reject(`Failed to start Python process: ${error.message}`);
            });
        } catch (error) {
            console.error(`Error in process-json handler: ${error.message}`);
            reject(`Error in process-json handler: ${error.message}`);
        }
    });
});

ipcMain.handle('upload-to-google-sheets', async (event, filePath) => {
    try {
        console.log(`Upload request received for file: ${filePath}`);
        
        // Verify file exists before attempting upload
        if (!fs.existsSync(filePath)) {
            console.error(`File does not exist: ${filePath}`);
            throw new Error(`File does not exist at path: ${filePath}`);
        }
        
        return await uploadToGoogleSheets(filePath);
    } catch (error) {
        console.error('Upload error in handler:', error);
        showErrorToUser('Upload Error', error.message);
        throw error;
    }
});

// Combine process and upload into a single operation
ipcMain.handle('process-and-upload', async (event, chatDir) => {
    try {
        console.log(`Starting combined process-and-upload for: ${chatDir}`);
        
        // First process the data - call the process-json handler directly
        const processResult = await new Promise((resolve, reject) => {
            try {
                // This is the same implementation as the process-json handler
                console.log(`Starting process-json from process-and-upload with chatDir: ${chatDir}`);
                
                if (!validateCredentials()) {
                    console.log('Credentials validation failed');
                    reject("Missing required credentials. Please provide them in the credentials form.");
                    createCredentialsWindow();
                    return;
                }
                
                const execPath = getPythonExecutablePath();
                if (!fs.existsSync(execPath)) {
                    console.log(`Executable not found: ${execPath}`);
                    reject(`Python executable not found at: ${execPath}`);
                    return;
                }
                
                // Verify the directory exists
                if (!fs.existsSync(chatDir)) {
                    console.error(`Input directory does not exist: ${chatDir}`);
                    reject(`Input directory does not exist: ${chatDir}`);
                    return;
                }
                
                // Ensure output directory exists
                const outputDirName = path.basename(chatDir) + 'Processed';
                const outputDir = path.join(procJsonPath, outputDirName);
                
                if (!fs.existsSync(outputDir)) {
                    fs.mkdirSync(outputDir, { recursive: true });
                    console.log(`Created output directory: ${outputDir}`);
                }
                
                console.log(`Running Python executable: ${execPath}`);
                console.log(`Input directory: ${chatDir}`);
                console.log(`Output directory: ${procJsonPath}`);
                
                // Prepare credentials JSON to pass to Python
                const credentialsJson = JSON.stringify({
                    OPENAI_API_KEY: userCredentials.OPENAI_API_KEY,
                    GOOGLE_SHEET_ID: userCredentials.GOOGLE_SHEET_ID,
                    GOOGLE_CREDENTIALS_JSON: userCredentials.GOOGLE_CREDENTIALS_JSON
                });
                
                // Log the command being executed (redact actual credentials)
                console.log(`Command: ${execPath} [credentials] ${chatDir} ${procJsonPath}`);
                
                // Launch the Python executable with credentials and paths
                const pythonProcess = spawn(execPath, [
                    credentialsJson,  // Pass credentials as first argument
                    chatDir,          // Input directory as second argument
                    procJsonPath      // Output directory as third argument
                ]);

                pythonProcesses.push(pythonProcess);

                let output = "";
                let errorOutput = "";

                pythonProcess.stdout.on('data', (data) => {
                    const message = data.toString();
                    console.log(`Python stdout: ${message}`);
                    output += message;
                    // Forward output to UI
                    if (mainWindow && !mainWindow.isDestroyed()) {
                        mainWindow.webContents.send('python-output', message);
                    }
                });

                pythonProcess.stderr.on('data', (data) => {
                    const message = data.toString();
                    console.error(`Python stderr: ${message}`);
                    errorOutput += message;
                    // Forward errors to UI
                    if (mainWindow && !mainWindow.isDestroyed()) {
                        mainWindow.webContents.send('python-error', message);
                    }
                });

                pythonProcess.on('close', (code) => {
                    console.log(`Python process exited with code ${code}`);
                    
                    // Check if the expected output file was created
                    const resultFile = path.join(outputDir, 'result.json');
                    const resultExists = fs.existsSync(resultFile);
                    console.log(`Result file exists: ${resultExists}, path: ${resultFile}`);
                    
                    if (code === 0) {
                        if (resultExists) {
                            resolve({
                                success: true,
                                message: output.trim(),
                                resultPath: resultFile
                            });
                        } else {
                            reject(`Process completed but result file was not created: ${resultFile}`);
                        }
                    } else {
                        reject(`Process exited with code ${code}: ${errorOutput.trim()}`);
                    }
                });

                pythonProcess.on('error', (error) => {
                    console.error(`Failed to start Python process: ${error.message}`);
                    reject(`Failed to start Python process: ${error.message}`);
                });
            } catch (error) {
                console.error(`Error in process-json handler: ${error.message}`);
                reject(`Error in process-json handler: ${error.message}`);
            }
        });
        
        console.log('Processing completed successfully');
        
        // If processing succeeded and we have a result path, upload it
        if (processResult && processResult.resultPath) {
            console.log(`Now uploading from: ${processResult.resultPath}`);
            const uploadResult = await uploadToGoogleSheets(processResult.resultPath);
            return {
                success: true,
                processResult: processResult.message,
                uploadResult
            };
        } else {
            throw new Error('Processing completed but no result path was returned');
        }
    } catch (error) {
        console.error('Process and upload failed:', error);
        showErrorToUser('Process and Upload Error', error.message);
        throw error;
    }
});

// Handle credential submission
ipcMain.on('submit-credentials', (event, credentials) => {
    try {
        // Read the Google credentials JSON file
        let googleCredsContent = null;
        if (credentials.googleCredentialsPath) {
            try {
                googleCredsContent = JSON.parse(fs.readFileSync(credentials.googleCredentialsPath, 'utf8'));
                console.log('Google credentials loaded successfully');
            } catch (error) {
                console.error('Error reading Google credentials file:', error);
                event.sender.send('credentials-error', `Error reading Google credentials file: ${error.message}`);
                return;
            }
        }
        
        // Update credentials
        userCredentials = {
            OPENAI_API_KEY: credentials.openaiApiKey,
            GOOGLE_SHEET_ID: credentials.googleSheetId,
            GOOGLE_CREDENTIALS_PATH: credentials.googleCredentialsPath,
            GOOGLE_CREDENTIALS_JSON: googleCredsContent
        };
        
        event.sender.send('credentials-success', 'Credentials saved successfully');
        
        // Close credentials window and show main window
        if (credentialsWindow && !credentialsWindow.isDestroyed()) {
            credentialsWindow.close();
        }
        
        if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.show();
        }
    } catch (error) {
        console.error('Error processing credentials:', error);
        event.sender.send('credentials-error', `Error processing credentials: ${error.message}`);
    }
});

// Show credentials form
ipcMain.on('show-credentials-form', () => {
    createCredentialsWindow();
});

// Select Google credentials file
ipcMain.handle('select-google-credentials-file', async () => {
    try {
        const result = await dialog.showOpenDialog({
            properties: ['openFile'],
            filters: [{ name: 'JSON Files', extensions: ['json'] }]
        });
        
        if (!result.canceled && result.filePaths.length > 0) {
            return result.filePaths[0];
        }
        return null;
    } catch (error) {
        console.error('Error selecting file:', error);
        return null;
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
        createAppDirectories();
        createMainWindow();
        
        // Check if Python executable exists at startup
        if (!checkPythonExecutable()) {
            dialog.showMessageBox({
                type: 'warning',
                title: 'Python Executable Missing',
                message: `Python executable not found or permissions could not be set. Make sure the build process has completed successfully.`,
                buttons: ['OK']
            });
        }
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