const { app, BrowserWindow, dialog, ipcMain, Menu } = require('electron');
const path = require('path');
const fs = require('fs');
const os = require("os");
const { GoogleSpreadsheet } = require('google-spreadsheet');
const { JWT } = require('google-auth-library');
const axios = require('axios'); // For making API calls to Cloud Run
require("dotenv").config();

// User credentials container - will be populated via UI
let userCredentials = {
    GOOGLE_CREDENTIALS_PATH: process.env.GOOGLE_CREDENTIALS_PATH || null,
    GOOGLE_SHEET_ID: process.env.GOOGLE_SHEET_ID || null,
    GOOGLE_CREDENTIALS_JSON: null, // Will hold the actual JSON content
    CLOUD_RUN_URL: process.env.CLOUD_RUN_URL || 'https://processjson-1061451118144.us-central1.run.app' // Cloud Run service URL
};

// Application paths - ensure consistent path handling across platforms
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

// Validate credentials
function validateCredentials() {
    const requiredCredentials = ['GOOGLE_SHEET_ID'];
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

async function handleProcessJson(chatDir) {
    if (!validateCredentials()) {
        throw new Error("Missing required credentials. Please provide them in the credentials form.");
    }
    
    // Verify the directory exists
    if (!fs.existsSync(chatDir)) {
        throw new Error(`Input directory does not exist: ${chatDir}`);
    }
    
    // Ensure output directory exists - THIS IS MISSING
    const outputDirName = path.basename(chatDir) + 'Processed';
    const outputDir = path.join(procJsonPath, outputDirName);
    
    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
        console.log(`Created output directory: ${outputDir}`);
    }
    
    // Return the result
    const result = await processWithCloudRun(chatDir, outputDir);
    return {
        success: true,
        message: result.message,
        resultPath: path.join(outputDir, 'result.json')
    };
}

// Handler for processing JSON
ipcMain.handle('process-json', async (event, chatDir) => {
    try {
        return await handleProcessJson(chatDir);
    } catch (error) {
        console.error(`Error in process-json handler: ${error.message}`);
        throw error; // Re-throw to let the renderer process handle it
    }
});

// Warmup function for Cloud Run service
async function warmupCloudRunService() {
    try {
      console.log('Warming up Cloud Run service...');
      const response = await axios.get(`${userCredentials.CLOUD_RUN_URL}/health`, {
        timeout: 60000 // 60 second timeout for warmup
      });
      
      if (response.status === 200) {
        console.log('Cloud Run service warmed up successfully');
        return true;
      } else {
        console.warn(`Unexpected response from warmup: ${response.status}`);
        return false;
      }
    } catch (error) {
      console.error('Error warming up Cloud Run service:', error.message);
      return false;
    }
}

// Process with Cloud Run service
async function processWithCloudRun(inputDir, outputDir) {
    try {
        // First warm up the service before sending the main request
        const isWarmedUp = await warmupCloudRunService();
        if (!isWarmedUp) {
            console.log('Warmup failed, but will attempt to process anyway');
            // Optional: You could add additional retry logic here
        }
        // Read all files in the input directory
        const files = fs.readdirSync(inputDir);
        const jsonFiles = files.filter(file => file.endsWith('.json'));
        const mediaFiles = files.filter(file => 
            file.endsWith('.mp4') || 
            file.endsWith('.jpg') || 
            file.endsWith('.jpeg') || 
            file.endsWith('.png')
        );
        
        if (jsonFiles.length === 0) {
            throw new Error('No JSON files found in the input directory');
        }
        
        // Read the content of each JSON file
        const jsonContents = {};
        for (const file of jsonFiles) {
            const filePath = path.join(inputDir, file);
            const content = fs.readFileSync(filePath, 'utf8');
            jsonContents[file] = content;
        }
        
        // Read and encode media files if any
        const mediaFilesContents = {};
        for (const file of mediaFiles) {
            const filePath = path.join(inputDir, file);
            try {
                // Read file as binary and convert to base64
                const content = fs.readFileSync(filePath);
                const base64Content = content.toString('base64');
                mediaFilesContents[file] = base64Content;
                console.log(`Encoded media file: ${file}`);
            } catch (error) {
                console.error(`Error reading media file ${file}: ${error.message}`);
                // Continue with other files
            }
        }
        
        // Prepare request payload
        const payload = {
            jsonContents,
            mediaFiles: mediaFilesContents,
            outputDir: path.basename(outputDir)
        };
        
        // Log payload size for debugging
        const payloadSize = JSON.stringify(payload).length;
        console.log(`Sending request to Cloud Run with payload size: ${(payloadSize / 1024 / 1024).toFixed(2)} MB`);
        
        // Add progress notification to the UI
        if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('python-output', 'Sending data to Cloud Run for processing...');
        }
        
        // Call Cloud Run service
        const response = await axios.post(`${userCredentials.CLOUD_RUN_URL}/process-json`, payload, {
            headers: {
                'Content-Type': 'application/json'
            },
            // Set a longer timeout for larger payloads
            timeout: 1800000 // 5 minutes
        });
        
        // Write the processed results to the output directory
        if (response.data && response.data.result) {
            fs.writeFileSync(path.join(outputDir, 'result.json'), 
                JSON.stringify(response.data.result, null, 2));
            
            // Forward logs from the Cloud Run service
            if (mainWindow && !mainWindow.isDestroyed() && response.data.logs) {
                for (const log of response.data.logs) {
                    mainWindow.webContents.send('python-output', log);
                }
            }
            
            return {
                success: true,
                message: response.data.message || 'Processing completed successfully'
            };
        } else {
            throw new Error('Invalid response from Cloud Run service');
        }
    } catch (error) {
        console.error('Error processing with Cloud Run:', error);
        
        // Forward error message to UI
        if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('python-error', 
                `Error communicating with Cloud Run: ${error.message}`);
        }
        
        throw error;
    }
}

// For process-and-upload
ipcMain.handle('process-and-upload', async (event, chatDir) => {
    try {
        console.log(`Starting combined process-and-upload for: ${chatDir}`);
        
        // First process the data - call the function directly instead of through IPC
        const processResult = await handleProcessJson(chatDir);
        
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

// App lifecycle
app.whenReady().then(() => {
    try {
        createAppDirectories();
        createMainWindow();
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
            googleSheetId: credentials.googleSheetId ? credentials.googleSheetId.trim() : '',
            googleCredentialsPath: credentials.googleCredentialsPath ? credentials.googleCredentialsPath.trim() : ''
        };
        
        // Validate required fields
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
        console.log(`- Google Sheet ID: ${cleanedCredentials.googleSheetId}`);
        console.log(`- Google Credentials Path: ${cleanedCredentials.googleCredentialsPath}`);
        console.log(`- Google Credentials JSON valid: ${googleCredsContent !== null}`);
        
        // Update credentials
        userCredentials = {
            GOOGLE_SHEET_ID: cleanedCredentials.googleSheetId,
            GOOGLE_CREDENTIALS_PATH: cleanedCredentials.googleCredentialsPath,
            GOOGLE_CREDENTIALS_JSON: googleCredsContent,
            CLOUD_RUN_URL: userCredentials.CLOUD_RUN_URL // Keep existing Cloud Run URL
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
        
        // Define the expected header values for Google Sheet
        // Added location_confidence column to handle confidence scores
        const expectedHeaders = [
            "id", "date", "date_unixtime", "from", "text", "reply_id", "LANGUAGE", 
            "TRANSLATED_TEXT", "parent_category", "parent_confidence_score", 
            "child_category", "child_confidence_score",
            "locations_names", "locations_coordinates", "location_confidence"
        ];
        
        // Manage sheet with proper loading
        let sheet;
        
        // First check if the sheet exists
        if (doc.sheetsByTitle[sheetName]) {
            sheet = doc.sheetsByTitle[sheetName];
            // Make sure to load the sheet headers before accessing them
            console.log("Sheet exists, loading headers...");
            await sheet.loadHeaderRow();
            console.log("Headers loaded successfully");
            
            // Now check if the sheet has all the expected headers
            const existingHeaders = sheet.headerValues || [];
            console.log("Existing headers:", existingHeaders);
            
            const missingHeaders = expectedHeaders.filter(header => !existingHeaders.includes(header));
            
            // If there are missing headers, update the sheet headers
            if (missingHeaders.length > 0) {
                console.log(`Adding missing headers to sheet: ${missingHeaders.join(', ')}`);
                await sheet.setHeaderRow([
                    ...existingHeaders,
                    ...missingHeaders
                ]);
                // Reload headers after updating
                await sheet.loadHeaderRow();
            }
        } else {
            // Create a new sheet with the expected headers
            console.log("Creating new sheet with headers:", expectedHeaders);
            sheet = await doc.addSheet({
                title: sheetName,
                headerValues: expectedHeaders
            });
            // Ensure headers are loaded
            await sheet.loadHeaderRow();
            console.log("New sheet created and headers loaded");
        }
        
        // Process messages to extract data including categories and confidence scores
        const newRows = messages.map(msg => {
            // Initialize location variables
            let locationName = "";
            let locationCoords = "";
            let locationConfidence = "";
            
            // Handle both formats (with and without confidence scores)
            if (msg.LOCATIONS && Array.isArray(msg.LOCATIONS) && msg.LOCATIONS.length > 0) {
                const firstLocation = msg.LOCATIONS[0];
                locationName = firstLocation.location || "";
                
                // Check if location has coordinates
                if (firstLocation.latitude !== undefined && firstLocation.longitude !== undefined) {
                    locationCoords = `(${firstLocation.latitude}, ${firstLocation.longitude})`;
                }
                
                // Check if confidence score is available in the new format
                if (firstLocation.confidence !== undefined) {
                    locationConfidence = firstLocation.confidence.toString();
                    console.log(`Found location with confidence: ${locationName} (${locationConfidence}%)`);
                }
            }
            
            // Initialize category variables with empty strings
            let parentCategory = "";
            let parentScore = "";
            let childCategory = "";
            let childScore = "";
            
            // Extract category information if available
            if (msg.CATEGORIES && Array.isArray(msg.CATEGORIES) && msg.CATEGORIES.length > 0) {
                const categoryData = msg.CATEGORIES[0];
                
                if (categoryData.classification) {
                    // Directly access the parent and child category fields
                    parentCategory = categoryData.classification.parent_category || "";
                    parentScore = categoryData.classification.parent_confidence_score || "";
                    childCategory = categoryData.classification.child_category || "";
                    childScore = categoryData.classification.child_confidence_score || "";
                    
                    console.log(`Found categories - Parent: ${parentCategory} (${parentScore}), Child: ${childCategory} (${childScore})`);
                } else {
                    console.log('Invalid classification structure:', categoryData);
                }
            } else {
                console.log('No categories found for message:', msg.id);
            }
            
            // Create the row object with the exact column names matching sheet headers
            return {
                id: msg.id || "",
                date: msg.date || "",
                date_unixtime: msg.date_unixtime || "",
                from: msg.from || "",
                text: msg.text ? msg.text.toString().normalize("NFC") : "", // Normalize text
                reply_id: msg.reply_to_message_id || "", 
                LANGUAGE: msg.LANGUAGE || "",
                TRANSLATED_TEXT: msg.TRANSLATED_TEXT || "",
                parent_category: parentCategory,
                parent_confidence_score: parentScore,
                child_category: childCategory,
                child_confidence_score: childScore,
                locations_names: locationName,
                locations_coordinates: locationCoords,
                location_confidence: locationConfidence // New field for location confidence
            };
        });
        
        if (newRows.length > 0) {
            // Add additional logging for debugging
            console.log(`Adding ${newRows.length} rows to Google Sheet`);
            console.log("First row sample:", JSON.stringify(newRows[0], null, 2));
            
            try {
                // Add rows with error handling
                await sheet.addRows(newRows);
                console.log(`Successfully added ${newRows.length} rows to Google Sheet with categories and location confidence`);
            } catch (rowError) {
                console.error("Error adding rows:", rowError);
                
                // Try adding rows one by one to identify problematic rows
                console.log("Attempting to add rows individually...");
                let successCount = 0;
                
                for (let i = 0; i < newRows.length; i++) {
                    try {
                        await sheet.addRow(newRows[i]);
                        successCount++;
                    } catch (singleRowError) {
                        console.error(`Error adding row ${i}:`, singleRowError);
                        console.error("Problematic row:", JSON.stringify(newRows[i], null, 2));
                    }
                }
                
                if (successCount > 0) {
                    console.log(`Successfully added ${successCount} out of ${newRows.length} rows`);
                } else {
                    throw new Error("Failed to add any rows to the sheet");
                }
            }
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