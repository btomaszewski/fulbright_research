const { app, BrowserWindow, dialog, ipcMain } = require('electron'); 
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

// Application paths - initialize these after app is ready
let userDataPath;
let rawJsonPath;
let procJsonPath;

app.on('ready', () => {
    initializePaths();
    createAppDirectories(); // Call this after initializing paths
    createMainWindow();
});

// Initialize application paths
function initializePaths() {
    userDataPath = app.getPath('userData');
    rawJsonPath = path.join(userDataPath, 'processing', 'rawJson');
    procJsonPath = path.join(userDataPath, 'processing', 'processedJson');
}

// Path to Python executable - simplified and more reliable
const getPythonExecutablePath = () => {
    // Platform-specific executable name
    const execName = process.platform === 'win32' ? 'processJson.exe' : 'processJson';
    const platformDir = `dist-${process.platform}`;
    
    console.log('=== Python Executable Path Search ===');
    console.log(`Platform: ${process.platform}, Executable: ${execName}`);
    console.log(`App paths: app.getAppPath()=${app.getAppPath()}`);
    console.log(`Resources path: ${process.resourcesPath || 'undefined'}`);
    console.log(`__dirname: ${__dirname}`);
    console.log(`Is packaged: ${app.isPackaged}`);
    
    // Prioritize paths based on build.sh output structure
    const possiblePaths = [];
    
    if (app.isPackaged) {
        // Packaged app paths - prioritize dist-darwin directory
        possiblePaths.push(
            // Primary location from build.sh
            path.join(process.resourcesPath, 'dist-darwin', execName),
            path.join(app.getAppPath(), 'dist-darwin', execName),
            // Secondary locations
            path.join(process.resourcesPath, platformDir, execName),
            path.join(process.resourcesPath, 'app.asar.unpacked', 'dist-darwin', execName),
            path.join(process.resourcesPath, execName)
        );
    } else {
        // Development paths
        possiblePaths.push(
            // Primary location from build.sh
            path.join(app.getAppPath(), 'dist-darwin', execName),
            path.join(__dirname, 'dist-darwin', execName),
            // Secondary locations
            path.join(app.getAppPath(), platformDir, execName),
            path.join(__dirname, platformDir, execName),
            path.join(app.getAppPath(), 'assets', platformDir, execName)
        );
    }
    
    console.log('Trying paths in order:', possiblePaths);
    
    // Check each path and return the first valid one
    for (const testPath of possiblePaths) {
        console.log(`Checking: ${testPath}`);
        
        if (fs.existsSync(testPath)) {
            try {
                const stats = fs.statSync(testPath);
                if (!stats.isDirectory()) {
                    console.log(`Found executable file: ${testPath}`);
                    
                    // Ensure executable permissions on Unix systems
                    if (process.platform !== 'win32') {
                        try {
                            fs.chmodSync(testPath, '755');
                            console.log(`Ensured executable permissions on: ${testPath}`);
                        } catch (permError) {
                            console.warn(`Note: Could not set permissions: ${permError.message}`);
                        }
                    }
                    
                    return testPath;
                } else {
                    console.log(`Path is a directory, not an executable: ${testPath}`);
                }
            } catch (statError) {
                console.error(`Error checking stats: ${statError.message}`);
            }
        }
    }
    
    // Fallback to electron-assets.json if no direct path was found
    console.log('No executable found in preferred locations, checking electron-assets.json...');
    
    const possibleAssetPaths = [
        path.join(app.getAppPath(), 'electron-assets.json'),
        path.join(__dirname, 'electron-assets.json'),
        path.join(app.getAppPath(), 'assets', 'electron-assets.json'),
        path.join(process.resourcesPath || app.getAppPath(), 'electron-assets.json')
    ];
    
    for (const assetPath of possibleAssetPaths) {
        if (fs.existsSync(assetPath)) {
            console.log(`Found electron-assets.json at: ${assetPath}`);
            try {
                const assetsData = JSON.parse(fs.readFileSync(assetPath, 'utf8'));
                if (assetsData.pyInstaller && assetsData.pyInstaller.executablePath) {
                    const execPath = path.isAbsolute(assetsData.pyInstaller.executablePath) ?
                        assetsData.pyInstaller.executablePath :
                        path.join(app.isPackaged ? process.resourcesPath : app.getAppPath(), 
                                 assetsData.pyInstaller.executablePath);
                    
                    console.log(`Using path from assets: ${execPath}`);
                    
                    if (fs.existsSync(execPath)) {
                        return execPath;
                    }
                }
            } catch (parseError) {
                console.error(`Error parsing electron-assets.json: ${parseError.message}`);
            }
        }
    }
    
    // Final fallback - use path based on build.sh output
    const defaultPath = app.isPackaged ?
        path.join(process.resourcesPath, 'dist-darwin', execName) :
        path.join(app.getAppPath(), 'dist-darwin', execName);
    
    console.log(`Final fallback path: ${defaultPath}`);
    console.log('=== End Python Executable Path Search ===');
    
    return defaultPath;
};

// Function to verify executable integrity
function verifyExecutable(execPath) {
    console.log(`Verifying executable at: ${execPath}`);
    
    if (!fs.existsSync(execPath)) {
        console.error(`❌ Executable not found at: ${execPath}`);
        return false;
    }
    
    console.log(`✅ Executable exists at: ${execPath}`);
    
    try {
        const stats = fs.statSync(execPath);
        
        if (stats.isDirectory()) {
            console.error(`❌ Path is a directory, not a file: ${execPath}`);
            return false;
        }
        
        console.log(`✅ Path is a file`);
        
        const fileSize = stats.size;
        console.log(`📊 Executable size: ${fileSize} bytes`);
        
        if (fileSize < 1000) {
            console.warn(`⚠️ WARNING: Executable file is suspiciously small!`);
        }
        
        // Check permissions on non-Windows platforms
        if (process.platform !== 'win32') {
            const hasExecPermission = !!(stats.mode & parseInt('111', 8));
            
            if (!hasExecPermission) {
                console.warn(`⚠️ Executable doesn't have execute permissions, setting them now`);
                try {
                    fs.chmodSync(execPath, '755');
                    console.log(`✅ Successfully set executable permissions`);
                } catch (permError) {
                    console.error(`❌ Failed to set permissions: ${permError.message}`);
                    return false;
                }
            } else {
                console.log(`✅ Executable has proper permissions`);
            }
        }
        
        return true;
    } catch (error) {
        console.error(`❌ Error verifying executable: ${error.message}`);
        return false;
    }
}

// Helper function to find the first existing file from a list of possible paths
function findExistingFile(pathsArray) {
    for (const filePath of pathsArray) {
        if (fs.existsSync(filePath)) {
            return filePath;
        }
    }
    return null;
}

// Validate credentials with improved whitespace handling
function validateCredentials() {
    const requiredCredentials = ['OPENAI_API_KEY', 'GOOGLE_SHEET_ID'];
    const missingCreds = requiredCredentials.filter(cred => {
        return !userCredentials[cred] || (typeof userCredentials[cred] === 'string' && userCredentials[cred].trim() === '');
    });
    
    // Special check for Google credentials - either path or JSON must be present
    const hasGoogleCreds = (
        (userCredentials.GOOGLE_CREDENTIALS_PATH && userCredentials.GOOGLE_CREDENTIALS_PATH.trim() !== '') || 
        (userCredentials.GOOGLE_CREDENTIALS_JSON && Object.keys(userCredentials.GOOGLE_CREDENTIALS_JSON).length > 0)
    );
    
    if (missingCreds.length > 0 || !hasGoogleCreds) {
        console.log('Credential validation failed. Missing:', missingCreds.join(', '));
        console.log('Google creds:', hasGoogleCreds);
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

// Create necessary application directories
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

// Create main application window
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
            show: false // Don't show until credentials are verified
        });

        // Determine correct path for frontend files
        let indexPath;
        if (app.isPackaged) {
            indexPath = path.join(app.getAppPath(), 'frontend', 'index.html');
        } else {
            indexPath = path.normalize(path.join(app.getAppPath(), 'frontend', 'index.html'));
        }
        
        console.log(`Loading main window from: ${indexPath}`);
        mainWindow.loadFile(indexPath);

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
        
        // Open DevTools for local development
        if (!app.isPackaged) {
            mainWindow.webContents.openDevTools();
        }

        mainWindow.on('closed', () => {
            mainWindow = null;
        });

        // Check if we have valid credentials before showing the window
        if (!validateCredentials()) {
            createCredentialsWindow();
        } else {
            mainWindow.show();
        }
    } catch (error) {
        console.error(`Error creating main window: ${error.message}`);
        showErrorToUser('Window Creation Error', `Failed to create main window: ${error.message}`);
    }
}

// Create credentials input window
function createCredentialsWindow() {
    console.log('Creating credentials window');
    
    if (credentialsWindow) {
        console.log('Credentials window already exists, focusing it');
        credentialsWindow.focus();
        return;
    }
  
    // Determine correct path for credentials.html
    let credentialsPath;
    if (app.isPackaged) {
        credentialsPath = path.join(app.getAppPath(), 'frontend', 'credentials.html');
    } else {
        credentialsPath = path.normalize(path.join(app.getAppPath(), 'frontend', 'credentials.html'));
    }
    
    console.log('Looking for credentials HTML at:', credentialsPath);
    
    if (!fs.existsSync(credentialsPath)) {
        console.error('CRITICAL ERROR: credentials.html file not found at', credentialsPath);
        dialog.showErrorBox('Missing File', `The credentials.html file is missing at ${credentialsPath}`);
        return;
    }
  
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
  
    // Open DevTools in credentials window only in development
    if (!app.isPackaged) {
        credentialsWindow.webContents.openDevTools();
    }
  
    console.log('Loading credentials.html into window');
    credentialsWindow.loadFile(credentialsPath);
    
    credentialsWindow.webContents.on('did-finish-load', () => {
        console.log('Credentials window loaded successfully');
    });
    
    credentialsWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
        console.error('Credentials window failed to load:', errorDescription);
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

// Improved spawn process function with better cross-platform handling
function spawnPythonProcess(args) {
    const execPathRaw = getPythonExecutablePath();
    console.log(`Using Python executable: ${execPathRaw}`);
    
    // Verify the executable before proceeding
    let finalExecPath;
    if (!verifyExecutable(execPathRaw)) {
        console.error('Failed executable verification, attempting fallback methods');
        
        // Try to find executable in dist-darwin directory
        const distDarwinPath = path.join(app.getAppPath(), 'dist-darwin');
        const fallbackPath = path.join(distDarwinPath, 'processJson');
        
        if (fs.existsSync(fallbackPath)) {
            console.log(`Using fallback executable: ${fallbackPath}`);
            
            // Set permissions
            if (process.platform !== 'win32') {
                try {
                    fs.chmodSync(fallbackPath, '755');
                    console.log(`Set executable permissions on fallback path`);
                } catch (error) {
                    console.warn(`Could not set permissions: ${error.message}`);
                }
            }
            
            finalExecPath = fallbackPath;
        } else {
            console.error(`Fallback executable not found at: ${fallbackPath}`);
            finalExecPath = execPathRaw;
        }
    } else {
        finalExecPath = execPathRaw;
    }
    
    // Log the command for debugging
    console.log(`Spawning Python process: ${finalExecPath} with args:`, args);
    
    // Create and return the process
    const pythonProcess = spawn(finalExecPath, args, { 
        stdio: ['pipe', 'pipe', 'pipe'],
        shell: process.platform === 'win32' // Use shell on Windows to handle spaces in paths
    });
    
    return pythonProcess;
}

// Shared function for processing JSON data
async function processJsonData(chatDir) {
    return new Promise((resolve, reject) => {
        try {
            // Add log to verify this is being called
            console.log(`Starting JSON processing with chatDir: ${chatDir}`);
            
            if (!validateCredentials()) {
                console.log('Credentials validation failed');
                reject("Missing required credentials. Please provide them in the credentials form.");
                createCredentialsWindow();
                return;
            }
            
            const execPath = getPythonExecutablePath();
            
            // Better error handling for executable check
            const execExists = fs.existsSync(execPath);
            const execIsDir = execExists ? fs.statSync(execPath).isDirectory() : false;
            
            if (!execExists) {
                console.log(`Executable not found: ${execPath}`);
                reject(`Python executable not found at: ${execPath}`);
                return;
            } else if (execIsDir) {
                console.log(`WARNING: Path is a directory: ${execPath}`);
                console.log('This will be handled by the spawnPythonProcess function');
                
                // Log directory contents for debugging
                try {
                    const dirContents = fs.readdirSync(execPath);
                    console.log(`Directory contents: ${dirContents.join(', ')}`);
                } catch (readError) {
                    console.error(`Error reading directory: ${readError.message}`);
                }
            }
            
            // Verify the directory exists
            if (!fs.existsSync(chatDir)) {
                console.error(`Input directory does not exist: ${chatDir}`);
                reject(`Input directory does not exist: ${chatDir}`);
                return;
            }
            
            // Ensure output directory exists with Windows-safe paths
            const outputDirName = path.basename(chatDir) + 'Processed';
            const outputDir = path.join(procJsonPath, outputDirName);
            
            if (!fs.existsSync(outputDir)) {
                fs.mkdirSync(outputDir, { recursive: true });
                console.log(`Created output directory: ${outputDir}`);
            }
            
            console.log(`Input directory: ${chatDir}`);
            console.log(`Output directory: ${outputDir}`);
            
            // Prepare credentials JSON to pass to Python with improved formatting
            const credentialsObj = {
                OPENAI_API_KEY: typeof userCredentials.OPENAI_API_KEY === 'string' ? 
                    userCredentials.OPENAI_API_KEY.trim() : userCredentials.OPENAI_API_KEY,
                GOOGLE_SHEET_ID: typeof userCredentials.GOOGLE_SHEET_ID === 'string' ? 
                    userCredentials.GOOGLE_SHEET_ID.trim() : userCredentials.GOOGLE_SHEET_ID,
                GOOGLE_CREDENTIALS_JSON: userCredentials.GOOGLE_CREDENTIALS_JSON
            };
            
            // Ensure we're sending a properly formatted JSON string
            const credentialsJson = JSON.stringify(credentialsObj);
            
            // Log the command being executed (redact actual credentials)
            console.log(`Command: [executable] [credentials] ${chatDir} ${outputDir}`);
            
            // Use the improved spawn function
            const pythonProcess = spawnPythonProcess([
                credentialsJson,
                chatDir,
                outputDir
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
            console.error(`Error in JSON processing: ${error.message}`);
            reject(`Error in JSON processing: ${error.message}`);
        }
    });
}

// Handler for processing JSON - now uses the shared function
ipcMain.handle('process-json', async (event, chatDir) => {
    console.log(`Process-json handler called with chatDir: ${chatDir}`);
    return processJsonData(chatDir);
});

// For process-and-upload - now also uses the shared function
ipcMain.handle('process-and-upload', async (event, chatDir) => {
    try {
        console.log(`Starting combined process-and-upload for: ${chatDir}`);
        
        if (!validateCredentials()) {
            console.log('Credentials validation failed');
            throw new Error("Missing required credentials. Please provide them in the credentials form.");
        }
        
        // Process the data using the shared function
        const processResult = await processJsonData(chatDir);
        
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
        const errorMessage = error && error.message ? error.message : String(error);
        showErrorToUser('Process and Upload Error', errorMessage);
        throw error;
    }
});

// Handle credential submission with improved whitespace handling
ipcMain.on('submit-credentials', (event, credentials) => {
    try {
        console.log('Processing submitted credentials');
        
        // Clean up whitespace in credential values
        const cleanedCredentials = {
            openaiApiKey: credentials.openaiApiKey ? credentials.openaiApiKey.trim() : '',
            googleSheetId: credentials.googleSheetId ? credentials.googleSheetId.trim() : '',
            googleCredentialsPath: credentials.googleCredentialsPath ? credentials.googleCredentialsPath.trim() : ''
        };
        
        // Validate required fields
        if (!cleanedCredentials.openaiApiKey) {
            event.sender.send('credentials-error', 'OpenAI API Key is required');
            return;
        }
        
        if (!cleanedCredentials.googleSheetId) {
            event.sender.send('credentials-error', 'Google Sheet ID is required');
            return;
        }
        
        // Read the Google credentials JSON file
        let googleCredsContent = null;
        if (cleanedCredentials.googleCredentialsPath) {
            try {
                // Normalize path for Windows compatibility
                const normalizedPath = path.normalize(cleanedCredentials.googleCredentialsPath);
                
                if (!fs.existsSync(normalizedPath)) {
                    event.sender.send('credentials-error', `Google credentials file not found: ${normalizedPath}`);
                    return;
                }
                
                const fileContent = fs.readFileSync(normalizedPath, 'utf8');
                try {
                    googleCredsContent = JSON.parse(fileContent);
                    
                    // Validate Google credentials structure
                    if (!googleCredsContent.client_email || !googleCredsContent.private_key) {
                        event.sender.send('credentials-error', 'Google credentials file is missing required fields (client_email or private_key)');
                        return;
                    }
                    
                    console.log('Google credentials loaded successfully');
                } catch (parseError) {
                    console.error('Error parsing Google credentials file:', parseError);
                    event.sender.send('credentials-error', `Invalid JSON in Google credentials file: ${parseError.message}`);
                    return;
                }
            } catch (error) {
                console.error('Error reading Google credentials file:', error);
                event.sender.send('credentials-error', `Error reading Google credentials file: ${error.message}`);
                return;
            }
        } else {
            event.sender.send('credentials-error', 'Google credentials file path is required');
            return;
        }
        
        // Log some diagnostics (without exposing sensitive info)
        console.log('Credentials validation passed:');
        console.log('- OpenAI API Key: [REDACTED]');
        console.log(`- Google Sheet ID: ${cleanedCredentials.googleSheetId}`);
        console.log(`- Google Credentials Path: ${cleanedCredentials.googleCredentialsPath}`);
        console.log(`- Google Credentials JSON valid: ${googleCredsContent !== null}`);
        
        // Update credentials
        userCredentials = {
            OPENAI_API_KEY: cleanedCredentials.openaiApiKey,
            GOOGLE_SHEET_ID: cleanedCredentials.googleSheetId,
            GOOGLE_CREDENTIALS_PATH: cleanedCredentials.googleCredentialsPath,
            GOOGLE_CREDENTIALS_JSON: googleCredsContent
        };
        
        // Persist credentials in config store
        try {
            // Note: Make sure to implement a secure storage mechanism
            // This is just a placeholder
            console.log('Credentials saved in memory successfully');
        } catch (storageError) {
            console.error('Error storing credentials:', storageError);
        }
        
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
            // Return normalized path for cross-platform compatibility
            return path.normalize(result.filePaths[0]);
        }
        return null;
    } catch (error) {
        console.error('Error selecting file:', error);
        return null;
    }
});

// IPC Handlers for datasets
ipcMain.handle('select-directory', async () => {
    try {
        const result = await dialog.showOpenDialog(mainWindow, {
            properties: ['openDirectory']
        });

        if (!result.filePaths.length) return null;

        const selectedDir = path.normalize(result.filePaths[0]);
        const targetDir = path.join(rawJsonPath, path.basename(selectedDir));
        
        try {
            // Use simplified directory copying that works on all platforms
            copyDirectoryRecursively(selectedDir, targetDir);
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

// Cross-platform directory copying helper
function copyDirectoryRecursively(src, dest) {
    if (!fs.existsSync(dest)) {
        fs.mkdirSync(dest, { recursive: true });
    }
    
    const entries = fs.readdirSync(src, { withFileTypes: true });
    
    for (const entry of entries) {
        const srcPath = path.join(src, entry.name);
        const destPath = path.join(dest, entry.name);
        
        if (entry.isDirectory()) {
            copyDirectoryRecursively(srcPath, destPath);
        } else {
            fs.copyFileSync(srcPath, destPath);
        }
    }
}

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

// Function to upload to Google Sheets
async function uploadToGoogleSheets(filePath) {
    try {
        // Validate filePath is a string
        if (typeof filePath !== 'string') {
            throw new Error(`Invalid filePath: expected string but got ${typeof filePath}`);
        }
        
        // Normalize the file path for cross-platform compatibility
        const normalizedPath = path.normalize(filePath);
        
        // Check if file exists
        if (!fs.existsSync(normalizedPath)) {
            throw new Error(`File does not exist at path: ${normalizedPath}`);
        }

        console.log(`Uploading file from: ${normalizedPath}`);

        // Check if we have Google credentials
        if (!userCredentials.GOOGLE_CREDENTIALS_JSON && !userCredentials.GOOGLE_CREDENTIALS_PATH) {
            throw new Error(`Google credentials not available. Please provide them in the credentials form.`);
        }

        let creds;
        
        // Get credentials either from JSON content or from file
        if (userCredentials.GOOGLE_CREDENTIALS_JSON) {
            creds = userCredentials.GOOGLE_CREDENTIALS_JSON;
        } else if (fs.existsSync(userCredentials.GOOGLE_CREDENTIALS_PATH)) {
            const credContent = fs.readFileSync(userCredentials.GOOGLE_CREDENTIALS_PATH, 'utf-8');
            try {
                creds = JSON.parse(credContent);
            } catch (parseError) {
                throw new Error(`Error parsing Google credentials file: ${parseError.message}`);
            }
        } else {
            throw new Error(`Google credentials file not found at: ${userCredentials.GOOGLE_CREDENTIALS_PATH}`);
        }
        
        // Ensure credential values are properly trimmed
        const sheetId = typeof userCredentials.GOOGLE_SHEET_ID === 'string' ? 
            userCredentials.GOOGLE_SHEET_ID.trim() : userCredentials.GOOGLE_SHEET_ID;
        
        const serviceAccount = new JWT({
            email: creds.client_email,
            key: creds.private_key,
            scopes: ['https://www.googleapis.com/auth/spreadsheets'],
        });

        const doc = new GoogleSpreadsheet(sheetId, serviceAccount);
        await doc.loadInfo();

        const fileData = fs.readFileSync(normalizedPath, 'utf-8');
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
                    "id", "date", "date_unixtime", "from", "text", "reply_id", "LANGUAGE", 
                    "TRANSLATED_TEXT", "categories", 
                    "confidence_scores", "locations_names", "locations_coordinates",
                ]
            });
        }
        
        // Process messages to extract data including categories
        const newRows = messages.map(msg => {
            // Get only the first location if available
            let locationName = "";
            let locationCoords = "";
            
            if (msg.LOCATIONS && Array.isArray(msg.LOCATIONS) && msg.LOCATIONS.length > 0) {
                const firstLocation = msg.LOCATIONS[0];
                locationName = firstLocation.location || "";
                
                // Check if location has coordinates
                if (firstLocation.latitude !== undefined && firstLocation.longitude !== undefined) {
                    locationCoords = `(${firstLocation.latitude}, ${firstLocation.longitude})`;
                }
            }
            
            // Initialize top category variables
            let topCategory = "";
            let topConfidenceScore = "";
            
            // Improved category extraction - handle both single and multiple categories
            if (msg.CATEGORIES && Array.isArray(msg.CATEGORIES) && msg.CATEGORIES.length > 0) {
                const categoryData = msg.CATEGORIES[0];
                
                if (categoryData.classification && categoryData.classification.confidence_scores) {
                    const scores = categoryData.classification.confidence_scores;
                    
                    // Handle both single and multiple category cases
                    const entries = Object.entries(scores);
                    
                    if (entries.length === 1) {
                        // Single category case - use it directly
                        const [category, score] = entries[0];
                        topCategory = category;
                        topConfidenceScore = score.toFixed(2);
                        console.log(`Single category found: ${topCategory} with score ${topConfidenceScore}`);
                    } else if (entries.length > 1) {
                        // Multiple categories case - find the highest score
                        let highestScore = -1;
                        let highestCategory = "";
                        
                        for (const [category, score] of entries) {
                            if (score > highestScore) {
                                highestScore = score;
                                highestCategory = category;
                            }
                        }
                        
                        topCategory = highestCategory;
                        topConfidenceScore = highestScore.toFixed(2);
                        console.log(`Found highest category: ${topCategory} with score ${topConfidenceScore}`);
                    }
                } else {
                    console.log('Invalid classification structure:', categoryData);
                }
            } else {
                console.log('No categories found for message:', msg.id);
            }
            
            return {
                id: msg.id || "",
                date: msg.date || "",
                date_unixtime: msg.date_unixtime || "",
                from: msg.from || "",
                text: msg.text ? msg.text.toString().normalize("NFC") : "", // Normalize text
                reply_id: msg.reply_to_message_id || "", 
                LANGUAGE: msg.LANGUAGE || "",
                TRANSLATED_TEXT: msg.TRANSLATED_TEXT || "",
                categories: topCategory,
                confidence_scores: topConfidenceScore,
                locations_names: locationName,
                locations_coordinates: locationCoords
            };
        });
        
        if (newRows.length > 0) {
            await sheet.addRows(newRows);
            console.log(`Added ${newRows.length} rows to Google Sheet with categories`);
        } else {
            console.log('No rows to add to Google Sheet');
        }

        return 'Upload successful';
    } catch (error) {
        console.error('Upload error:', error);
        throw new Error(`Failed to upload to Google Sheets: ${error.message}, ${filePath}`);
    }
}