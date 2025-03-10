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

// Application paths - ensure consistent path handling across platforms
const userDataPath = app.getPath('userData');
const rawJsonPath = path.join(userDataPath, 'processing', 'rawJson');
const procJsonPath = path.join(userDataPath, 'processing', 'processedJson');

// Path to Python executable - now using the PyInstaller executable
const getPythonExecutablePath = () => {
    // First try to get the path from electron-assets.json
    try {
        // Try multiple locations for the assets file
        const possibleAssetsPaths = [
            path.join(app.getAppPath(), 'assets', 'electron-assets.json'),
            path.join(app.getAppPath(), 'electron-assets.json'),
            path.join(__dirname, 'assets', 'electron-assets.json'),
            path.join(__dirname, 'electron-assets.json')
        ];
        
        let assetsFilePath = null;
        for (const assetPath of possibleAssetsPaths) {
            if (fs.existsSync(assetPath)) {
                assetsFilePath = assetPath;
                console.log('Found electron-assets.json at:', assetsFilePath);
                break;
            }
        }
        
        if (assetsFilePath) {
            const assetsData = JSON.parse(fs.readFileSync(assetsFilePath, 'utf8'));
            
            if (assetsData.pyInstaller && assetsData.pyInstaller.executablePath) {
                // Check if path is absolute or relative
                let execPath;
                if (path.isAbsolute(assetsData.pyInstaller.executablePath)) {
                    execPath = assetsData.pyInstaller.executablePath;
                } else {
                    execPath = path.join(app.getAppPath(), assetsData.pyInstaller.executablePath);
                }
                
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
            console.error('electron-assets.json not found in any of the expected locations');
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
        // Try multiple potential locations for Windows executable
        const possiblePaths = [
            path.join(app.getAppPath(), 'dist-win32', 'processJson.exe'),
            path.join(app.getAppPath(), 'assets', 'dist-win32', 'processJson.exe'),
            path.join(__dirname, 'dist-win32', 'processJson.exe'),
            path.join(__dirname, 'assets', 'dist-win32', 'processJson.exe'),
            // For packaged app in resources directory
            path.join(process.resourcesPath, 'dist-win32', 'processJson.exe'),
            // Additional common locations for Windows
            path.join(process.resourcesPath, 'app.asar.unpacked', 'dist-win32', 'processJson.exe'),
            path.join(app.getAppPath(), 'app.asar.unpacked', 'dist-win32', 'processJson.exe')
        ];
        
        for (const testPath of possiblePaths) {
            console.log('Testing Windows executable path:', testPath);
            if (fs.existsSync(testPath)) {
                console.log('Found Windows executable at:', testPath);
                executablePath = testPath;
                break;
            }
        }
        
        if (!executablePath) {
            console.error('Could not find Windows executable at any expected path');
            executablePath = path.join(app.getAppPath(), 'dist-win32', 'processJson.exe');
        }
    } else if (platform === 'linux') {
        executablePath = path.join(app.getAppPath(), 'dist-linux', 'processJson');
    } else {
        throw new Error(`Unsupported platform: ${platform}`);
    }
    
    console.log('Final executable path:', executablePath);
    return executablePath;
};

// Validate credentials with improved whitespace handling
function validateCredentials() {
    const requiredCredentials = ['OPENAI_API_KEY', 'GOOGLE_SHEET_ID'];
    const missingCreds = requiredCredentials.filter(cred => {
        // Check if credential exists and is not just whitespace
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

        // Use normalized path for loading the file
        const indexPath = path.normalize(path.join(app.getAppPath(), 'frontend', 'index.html'));
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
        
        // Always open DevTools for local development
        if (!app.isPackaged) {
            mainWindow.webContents.openDevTools();
        }

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
  
    // Check if frontend/credentials.html exists with path normalization for Windows
    const credentialsPath = path.normalize(path.join(app.getAppPath(), 'frontend', 'credentials.html'));
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
  
    // Force DevTools to open in credentials window only in development
    if (!app.isPackaged) {
      credentialsWindow.webContents.openDevTools();
    }
  
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

// Modified spawn process for Windows compatibility
function spawnPythonProcess(execPath, args) {
    // Normalize path for Windows
    execPath = path.normalize(execPath);
    
    const options = {
        windowsHide: true
    };
    
    if (process.platform === 'win32') {
        options.shell = true;  // Use shell on Windows for better path handling
        
        // Make sure credentials JSON is properly formatted
        if (args[0] && typeof args[0] === 'string') {
            try {
                // If it's already a JSON string, parse it first
                const credentials = JSON.parse(args[0]);
                // Re-stringify with proper formatting and escaping
                args[0] = JSON.stringify(credentials);
            } catch (e) {
                // If it fails to parse, it might not be JSON or might need escaping
                console.warn("Ensuring JSON string is properly formatted:", e);
                // Try to escape it properly
                args[0] = `'${args[0].replace(/'/g, "\\'")}'`;
            }
        }
        
        // For the path arguments, quote them properly
        for (let i = 1; i < args.length; i++) {
            if (typeof args[i] === 'string' && args[i].includes(' ')) {
                args[i] = `"${args[i]}"`;
            }
        }
        
        // For Windows, combine arguments into a single string command
        // This helps with spaces in paths
        const cmd = [
            `"${execPath}"`,
            ...args.map(arg => typeof arg === 'string' ? `"${arg}"` : arg)
        ].join(' ');
        
        console.log(`Windows command: ${cmd}`);
        
        // Use execFile with shell option for Windows
        return require('child_process').spawn(cmd, [], { 
            shell: true,
            windowsHide: options.windowsHide
        });
    } else {
        // On Unix, use the list form without shell
        return spawn(execPath, args, options);
    }
}

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
            
            // Ensure output directory exists with Windows-safe paths
            const outputDirName = path.basename(chatDir) + 'Processed';
            const outputDir = path.join(procJsonPath, outputDirName);
            
            if (!fs.existsSync(outputDir)) {
                fs.mkdirSync(outputDir, { recursive: true });
                console.log(`Created output directory: ${outputDir}`);
            }
            
            console.log(`Running Python executable: ${execPath}`);
            console.log(`Input directory: ${chatDir}`);
            console.log(`Output directory: ${procJsonPath}`);
            
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
            console.log(`Command: ${execPath} [credentials] ${chatDir} ${procJsonPath}`);
            
            // For Windows platforms, directly create a quoted command to handle spaces in paths
            let pythonProcess;
            
            if (process.platform === 'win32') {
                console.log('Using Windows-specific process spawning method');
                
                // Format paths safely for Windows command line
                const safeExecPath = `"${execPath}"`;
                const safeCredentials = `"${credentialsJson.replace(/"/g, '\\"')}"`;
                const safeChatDir = `"${chatDir}"`;
                const safeProcJsonPath = `"${procJsonPath}"`;
                
                // Create a safe command string
                const commandString = `${safeExecPath} ${safeCredentials} ${safeChatDir} ${safeProcJsonPath}`;
                console.log(`Windows command string: ${commandString.replace(safeCredentials, '"[CREDENTIALS REDACTED]"')}`);
                
                // Use spawn with shell option for Windows
                pythonProcess = require('child_process').spawn(commandString, [], { 
                    shell: true,
                    windowsHide: true
                });
            } else {
                // For non-Windows platforms, use the regular approach
                pythonProcess = spawn(execPath, [
                    credentialsJson,
                    chatDir,
                    procJsonPath
                ]);
            }

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

// For process-and-upload, with improved Windows path handling:
ipcMain.handle('process-and-upload', async (event, chatDir) => {
    try {
        console.log(`Starting combined process-and-upload for: ${chatDir}`);
        
        // First process the data - call the process-json handler directly
        const processResult = await new Promise((resolve, reject) => {
            try {
                // This is the same implementation as the process-json handler with improved Windows handling
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
                console.log(`Command: ${execPath} [credentials] ${chatDir} ${procJsonPath}`);
                
                // For Windows platforms, directly create a quoted command to handle spaces in paths
                let pythonProcess;
                
                if (process.platform === 'win32') {
                    console.log('Using Windows-specific process spawning method');
                    
                    // Format paths safely for Windows command line
                    const safeExecPath = `"${execPath}"`;
                    const safeCredentials = `"${credentialsJson.replace(/"/g, '\\"')}"`;
                    const safeChatDir = `"${chatDir}"`;
                    const safeProcJsonPath = `"${procJsonPath}"`;
                    
                    // Create a safe command string
                    const commandString = `${safeExecPath} ${safeCredentials} ${safeChatDir} ${safeProcJsonPath}`;
                    console.log(`Windows command string: ${commandString.replace(safeCredentials, '"[CREDENTIALS REDACTED]"')}`);
                    
                    // Use spawn with shell option for Windows
                    pythonProcess = require('child_process').spawn(commandString, [], { 
                        shell: true,
                        windowsHide: true
                    });
                } else {
                    // For non-Windows platforms, use the regular approach
                    pythonProcess = spawn(execPath, [
                        credentialsJson,
                        chatDir,
                        procJsonPath
                    ]);
                }

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
        const errorMessage = error && error.message ? error.message : String(error);
        showErrorToUser('Process and Upload Error', errorMessage);
        throw error;
    }
});

// Clean up resources before quitting
app.on('before-quit', () => {
    console.log('Cleaning up resources before quitting...');
    pythonProcesses.forEach(process => {
        if (process && !process.killed) {
            try {
                // On Windows, we need to use a different approach to kill processes
                if (process.platform === 'win32') {
                    // Try to terminate via Windows-specific commands if needed
                    if (process.pid) {
                        try {
                            require('child_process').execSync(`taskkill /F /PID ${process.pid}`, { windowsHide: true });
                            console.log(`Killed Windows process with PID ${process.pid}`);
                        } catch (killError) {
                            console.error(`Error killing Windows process: ${killError.message}`);
                        }
                    }
                } else {
                    process.kill();
                }
                console.log('Killed a Python process');
            } catch (error) {
                console.error('Failed to kill process:', error);
            }
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
            // For Windows compatibility when copying directories
            if (process.platform === 'win32') {
                // We need to use recursive: true for Windows
                if (!fs.existsSync(targetDir)) {
                    fs.mkdirSync(targetDir, { recursive: true });
                }
                
                // Helper function to copy directory recursively on Windows
                const copyDirRecursive = (src, dest) => {
                    const entries = fs.readdirSync(src, { withFileTypes: true });
                    
                    for (const entry of entries) {
                        const srcPath = path.join(src, entry.name);
                        const destPath = path.join(dest, entry.name);
                        
                        if (entry.isDirectory()) {
                            if (!fs.existsSync(destPath)) {
                                fs.mkdirSync(destPath, { recursive: true });
                            }
                            copyDirRecursive(srcPath, destPath);
                        } else {
                            fs.copyFileSync(srcPath, destPath);
                        }
                    }
                };
                
                // Copy directory recursively
                copyDirRecursive(selectedDir, targetDir);
            } else {
                // On macOS/Linux use fs.cpSync
                fs.cpSync(selectedDir, targetDir, { recursive: true });
            }
            
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
                    "id", "date", "from", "text", "reply_id", "LANGUAGE", 
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
                from: msg.from || "",
                text: msg.text || "",
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

        // Try/catch for dashboard refresh to prevent errors if not available
        try {
            setTimeout(() => {
                if (typeof refreshDashboard === 'function') {
                    refreshDashboard(); // Refresh Tableau after upload
                }
            }, 5000); // Delay to ensure data syncs
        } catch (dashboardError) {
            console.log('Dashboard refresh not available:', dashboardError);
        }
        
        return 'Upload successful';
    } catch (error) {
        console.error('Upload error:', error);
        throw new Error(`Failed to upload to Google Sheets: ${error.message}, ${filePath}`);
    }
}