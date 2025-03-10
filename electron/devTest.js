// wrapper-dev-script-fixed.js - Uses the wrapper.py approach with proper argument handling
const { app, BrowserWindow, dialog, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const os = require('os');
require('dotenv').config();

// Set a global flag that we're in dev mode
process.env.DEV_MODE = 'true';

// Initialize global userCredentials object
global.userCredentials = null;

// Capture the main.js userCredentials reference 
// This is needed to sync credentials between our dev script and main.js
global.mainJsUserCredentials = null;

// Development paths
const devDataPath = path.join(__dirname, 'dev-test-data');
const devRawJsonPath = path.join(devDataPath, 'processing', 'rawJson');
const devProcJsonPath = path.join(devDataPath, 'processing', 'processedJson');

// Create directories
function createDevDirectories() {
  [devDataPath, devRawJsonPath, devProcJsonPath].forEach(dir => {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
      console.log(`[DEV] Created directory: ${dir}`);
    } else {
      console.log(`[DEV] Directory exists: ${dir}`);
    }
  });
}

// Create development directories immediately
createDevDirectories();

// Store original methods
const originalGetPath = app.getPath;

// Replace app.getPath to use our dev paths for userData
app.getPath = function(name, ...args) {
  if (name === 'userData') {
    console.log(`[DEV] Redirecting userData path to: ${devDataPath}`);
    return devDataPath;
  }
  return originalGetPath.call(app, name, ...args);
};

// IMPORTANT: We need to save references to original IPC methods before they're called
const originalIpcMainHandle = ipcMain.handle;

// Override ipcMain.handle to intercept specific handlers
ipcMain.handle = function(channel, handler) {
  if (channel === 'process-json') {
    console.log(`[DEV] Intercepting 'process-json' registration`);
    // Instead of registering their handler, register our own
    return originalIpcMainHandle.call(ipcMain, channel, (event, chatDir) => {
      console.log(`[DEV] Handling 'process-json' call for: ${chatDir}`);
      return runWithWrapper(chatDir);
    });
  } 
  else if (channel === 'process-and-upload') {
    console.log(`[DEV] Intercepting 'process-and-upload' registration`);
    // For this one, we'll use our own handler but delegate to their upload function
    return originalIpcMainHandle.call(ipcMain, channel, async (event, chatDir) => {
      console.log(`[DEV] Handling 'process-and-upload' call for: ${chatDir}`);
      try {
        // First process with our wrapper approach
        const processResult = await runWithWrapper(chatDir);
        console.log(`[DEV] Processing complete, resultPath: ${processResult.resultPath}`);
        
        // Now try to find the uploadToGoogleSheets function in the global scope
        if (typeof global.uploadToGoogleSheets === 'function') {
          console.log(`[DEV] Found uploadToGoogleSheets function, calling it`);
          const uploadResult = await global.uploadToGoogleSheets(processResult.resultPath);
          return {
            success: true,
            processResult: processResult.message,
            uploadResult
          };
        } else {
          console.log('[DEV] No uploadToGoogleSheets function found, skipping upload');
          return {
            success: true,
            processResult: processResult.message,
            uploadResult: 'Upload skipped in dev mode'
          };
        }
      } catch (error) {
        console.error('[DEV] Error in process-and-upload:', error);
        // If we have showErrorToUser function available, use it
        if (typeof global.showErrorToUser === 'function') {
          global.showErrorToUser('Process and Upload Error', error.message);
        } else {
          dialog.showErrorBox('Process and Upload Error', error.message);
        }
        throw error;
      }
    });
  }
  // For all other channels, use the original handler
  return originalIpcMainHandle.apply(ipcMain, arguments);
};

// This function uses the wrapper.py approach for development
function runWithWrapper(chatDir) {
  return new Promise((resolve, reject) => {
    try {
      console.log(`[DEV] Starting execution with wrapper for: ${chatDir}`);
      
      // Look for the wrapper script
      let wrapperScriptPath = null;
      const potentialWrapperPaths = [
        path.join(__dirname, 'assets', 'python', 'wrapper.py'),
        path.join(__dirname, 'assets', 'src', 'wrapper.py'),
        path.join(__dirname, 'assets', 'wrapper.py'),
      ];
      
      for (const scriptPath of potentialWrapperPaths) {
        if (fs.existsSync(scriptPath)) {
          wrapperScriptPath = scriptPath;
          console.log(`[DEV] Found wrapper script at: ${wrapperScriptPath}`);
          break;
        }
      }
      
      // If we don't find the wrapper, use the main script approach
      if (!wrapperScriptPath) {
        console.log('[DEV] Wrapper script not found. Looking for main Python script.');
        
        // Look for the main Python script instead
        let pythonScriptPath = null;
        const potentialScriptPaths = [
          path.join(__dirname, 'assets', 'python', 'processJson.py'),
          path.join(__dirname, 'assets', 'src', 'processJson.py'),
          path.join(__dirname, 'assets', 'processJson.py'),
        ];
        
        for (const scriptPath of potentialScriptPaths) {
          if (fs.existsSync(scriptPath)) {
            pythonScriptPath = scriptPath;
            console.log(`[DEV] Found Python script at: ${pythonScriptPath}`);
            break;
          }
        }
        
        if (!pythonScriptPath) {
          return reject('Could not find Python script in any expected location.');
        }
        
        wrapperScriptPath = pythonScriptPath;
      }
      
      // Ensure output directory exists
      const outputDirName = path.basename(chatDir) + 'Processed';
      const outputDir = path.join(devProcJsonPath, outputDirName);
      
      if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
        console.log(`[DEV] Created output directory: ${outputDir}`);
      }
      
      // Get credentials from userCredentials global if available
      let credentials = {};
      
      if (global.userCredentials) {
        // Use the credentials stored in the global object
        credentials = {
          OPENAI_API_KEY: global.userCredentials.OPENAI_API_KEY,
          GOOGLE_SHEET_ID: global.userCredentials.GOOGLE_SHEET_ID,
          GOOGLE_CREDENTIALS_JSON: global.userCredentials.GOOGLE_CREDENTIALS_JSON
        };
        
        // If we have a path but no JSON, try to load it
        if (global.userCredentials.GOOGLE_CREDENTIALS_PATH && 
            !credentials.GOOGLE_CREDENTIALS_JSON && 
            fs.existsSync(global.userCredentials.GOOGLE_CREDENTIALS_PATH)) {
          try {
            const credContent = fs.readFileSync(global.userCredentials.GOOGLE_CREDENTIALS_PATH, 'utf8');
            credentials.GOOGLE_CREDENTIALS_JSON = JSON.parse(credContent);
          } catch (err) {
            console.error(`[DEV] Error loading Google credentials from path: ${err.message}`);
          }
        }
      } else {
        // Fallback to environment variables
        credentials = {
          OPENAI_API_KEY: process.env.OPENAI_API_KEY,
          GOOGLE_SHEET_ID: process.env.GOOGLE_SHEET_ID,
          GOOGLE_CREDENTIALS_JSON: null
        };
        
        // Try to load Google credentials from path
        if (process.env.GOOGLE_CREDENTIALS_PATH && fs.existsSync(process.env.GOOGLE_CREDENTIALS_PATH)) {
          try {
            const credContent = fs.readFileSync(process.env.GOOGLE_CREDENTIALS_PATH, 'utf8');
            credentials.GOOGLE_CREDENTIALS_JSON = JSON.parse(credContent);
          } catch (err) {
            console.error(`[DEV] Error loading Google credentials from env path: ${err.message}`);
          }
        }
      }
      
      // Log what credentials we have (without exposing sensitive details)
      console.log('[DEV] Using credentials:');
      console.log('- OPENAI_API_KEY:', credentials.OPENAI_API_KEY ? '[PRESENT]' : '[MISSING]');
      console.log('- GOOGLE_SHEET_ID:', credentials.GOOGLE_SHEET_ID ? '[PRESENT]' : '[MISSING]');
      console.log('- GOOGLE_CREDENTIALS_JSON:', credentials.GOOGLE_CREDENTIALS_JSON ? '[PRESENT]' : '[MISSING]');
      
      // Create a JSON string from the credentials
      const credentialsJson = JSON.stringify(credentials);
      
      console.log(`[DEV] Running with wrapper approach`);
      console.log(`[DEV] Script: ${wrapperScriptPath}`);
      console.log(`[DEV] Input: ${chatDir}`);
      console.log(`[DEV] Output: ${devProcJsonPath}`);
      
      // Determine Python executable based on platform
      const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
      
      // Get browser window to send messages to
      const getMainWindow = () => {
        return BrowserWindow.getAllWindows().find(w => !w.isDestroyed());
      };
      
      // Prepare Python execution options with proper environment variables
      const pythonOptions = {
        env: { 
          ...process.env,
          // Set PYTHONPATH to include your assets directory
          PYTHONPATH: path.join(__dirname, 'assets'),
          // Force Python to use unbuffered output for better logging
          PYTHONUNBUFFERED: '1',
          // Ensure SSL certificate path is available
          NODE_TLS_REJECT_UNAUTHORIZED: '0',
          // Pass through credentials explicitly
          OPENAI_API_KEY: credentials.OPENAI_API_KEY,
          GOOGLE_SHEET_ID: credentials.GOOGLE_SHEET_ID
        },
        cwd: path.dirname(wrapperScriptPath) // Set current working directory to script directory
      };
      
      // Python args setup - match EXACTLY how the process-json handler does it
      // Because wrapper.py expects: credentials_json input_dir output_dir
      const pythonArgs = [
        wrapperScriptPath,
        credentialsJson,  // Pass credentials JSON directly as an argument
        chatDir,          // Input directory as second argument
        devProcJsonPath   // Output directory as third argument
      ];
      
      // Log the exact credentials JSON format we're passing (with sensitive info masked)
      const logCredentials = JSON.parse(JSON.stringify(credentials));
      if (logCredentials.OPENAI_API_KEY) {
        logCredentials.OPENAI_API_KEY = "[REDACTED]";
      }
      if (logCredentials.GOOGLE_CREDENTIALS_JSON) {
        logCredentials.GOOGLE_CREDENTIALS_JSON = "[REDACTED_JSON]";
      }
      console.log(`[DEV] Credentials format: ${JSON.stringify(logCredentials)}`);
      
      // Execute Python process
      console.log(`[DEV] Executing: ${pythonCmd} "${wrapperScriptPath}"`);
      const pythonProcess = spawn(pythonCmd, pythonArgs, pythonOptions);

      let output = "";
      let errorOutput = "";

      pythonProcess.stdout.on('data', (data) => {
        const message = data.toString();
        console.log(`[DEV] Python stdout: ${message}`);
        output += message;
        // Forward output to UI if window is available
        const mainWindow = getMainWindow();
        if (mainWindow) {
          mainWindow.webContents.send('python-output', message);
        }
      });

      pythonProcess.stderr.on('data', (data) => {
        const message = data.toString();
        console.error(`[DEV] Python stderr: ${message}`);
        errorOutput += message;
        // Forward errors to UI if window is available
        const mainWindow = getMainWindow();
        if (mainWindow) {
          mainWindow.webContents.send('python-error', message);
        }
      });

      pythonProcess.on('close', (code) => {
        console.log(`[DEV] Python process exited with code ${code}`);
        
        // Check if the expected output file was created
        const resultFile = path.join(outputDir, 'result.json');
        const resultExists = fs.existsSync(resultFile);
        console.log(`[DEV] Result file exists: ${resultExists}, path: ${resultFile}`);
        
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
        console.error(`[DEV] Failed to start Python process: ${error.message}`);
        reject(`Failed to start Python process: ${error.message}`);
      });
    } catch (error) {
      console.error(`[DEV] Error in runWithWrapper: ${error.message}`);
      reject(`Error in runWithWrapper: ${error.message}`);
    }
  });
}

// Also intercept the check-result-file handler for completeness
const originalIpcMainHandleOnce = ipcMain.handleOnce;
ipcMain.handleOnce = function(channel, handler) {
  if (channel === 'check-result-file') {
    console.log(`[DEV] Intercepting 'check-result-file' registration`);
    return originalIpcMainHandleOnce.call(ipcMain, channel, (event, dirName) => {
      const outputDir = path.join(devProcJsonPath, dirName + 'Processed');
      const resultFile = path.join(outputDir, 'result.json');
      
      console.log(`[DEV] Checking for file at: ${resultFile}`);
      const exists = fs.existsSync(resultFile);
      console.log(`[DEV] File exists: ${exists}`);
      
      return {
        exists,
        path: resultFile,
        dirPath: outputDir,
        dirExists: fs.existsSync(outputDir)
      };
    });
  }
  return originalIpcMainHandleOnce.apply(ipcMain, arguments);
};

// Set up handler to intercept credentials submission to access them immediately
ipcMain.on('submit-credentials', (event, credentials) => {
  console.log('[DEV] Captured credentials submission');
  console.log('- OPENAI_API_KEY:', credentials.openaiApiKey ? '[PRESENT]' : '[MISSING]');
  console.log('- GOOGLE_SHEET_ID:', credentials.googleSheetId || '[MISSING]');
  console.log('- GOOGLE_CREDENTIALS_PATH:', credentials.googleCredentialsPath || '[MISSING]');
  
  // Save credentials properly to global object
  global.userCredentials = {
    OPENAI_API_KEY: credentials.openaiApiKey,
    GOOGLE_SHEET_ID: credentials.googleSheetId,
    GOOGLE_CREDENTIALS_PATH: credentials.googleCredentialsPath,
    GOOGLE_CREDENTIALS_JSON: null
  };
  
  // Load Google credentials from path if provided
  if (credentials.googleCredentialsPath && fs.existsSync(credentials.googleCredentialsPath)) {
    try {
      const credContent = fs.readFileSync(credentials.googleCredentialsPath, 'utf8');
      global.userCredentials.GOOGLE_CREDENTIALS_JSON = JSON.parse(credContent);
      console.log('Google credentials loaded successfully');
      
      // Verify Google credentials structure
      if (!global.userCredentials.GOOGLE_CREDENTIALS_JSON.client_email || 
          !global.userCredentials.GOOGLE_CREDENTIALS_JSON.private_key) {
        console.error('[DEV] Google credentials file is missing required fields (client_email or private_key)');
        
        if (event && event.sender) {
          event.sender.send('credentials-error', 'Google credentials file is missing required fields (client_email or private_key)');
        }
        return;
      }
    } catch (err) {
      console.error(`[DEV] Error loading Google credentials: ${err.message}`);
      
      if (event && event.sender) {
        event.sender.send('credentials-error', `Invalid JSON in Google credentials file: ${err.message}`);
      }
      return;
    }
  } else if (credentials.googleCredentialsPath) {
    console.error(`[DEV] Google credentials file not found: ${credentials.googleCredentialsPath}`);
    
    if (event && event.sender) {
      event.sender.send('credentials-error', `Google credentials file not found: ${credentials.googleCredentialsPath}`);
    }
    return;
  }
  
  // Validate credentials
  const validationStatus = [];
  validationStatus.push(`- OpenAI API Key: ${credentials.openaiApiKey ? '[REDACTED]' : '[MISSING]'}`);
  validationStatus.push(`- Google Sheet ID: ${credentials.googleSheetId || '[MISSING]'}`);
  validationStatus.push(`- Google Credentials Path: ${credentials.googleCredentialsPath || '[MISSING]'}`);
  validationStatus.push(`- Google Credentials JSON valid: ${global.userCredentials.GOOGLE_CREDENTIALS_JSON ? 'true' : 'false'}`);
  console.log('Credentials validation passed:');
  validationStatus.forEach(status => console.log(status));
  
  // Also set userCredentials in main.js scope to make sure both have access
  // This is a bit hacky but ensures compatibility with main.js
  try {
    // This essentially makes our userCredentials available to the main.js module
    global.userCredentials = {
      OPENAI_API_KEY: credentials.openaiApiKey,
      GOOGLE_SHEET_ID: credentials.googleSheetId,
      GOOGLE_CREDENTIALS_PATH: credentials.googleCredentialsPath,
      GOOGLE_CREDENTIALS_JSON: global.userCredentials.GOOGLE_CREDENTIALS_JSON
    };
    
    // Also update the script-local userCredentials variable in main.js
    // This is needed because main.js uses a local variable not a global one
    if (global.mainJsUserCredentials) {
      console.log('[DEV] Updating main.js userCredentials reference');
      global.mainJsUserCredentials.OPENAI_API_KEY = credentials.openaiApiKey;
      global.mainJsUserCredentials.GOOGLE_SHEET_ID = credentials.googleSheetId;
      global.mainJsUserCredentials.GOOGLE_CREDENTIALS_PATH = credentials.googleCredentialsPath;
      global.mainJsUserCredentials.GOOGLE_CREDENTIALS_JSON = global.userCredentials.GOOGLE_CREDENTIALS_JSON;
    }
  } catch (err) {
    console.error(`[DEV] Error syncing credentials with main.js: ${err.message}`);
  }
  
  console.log('Credentials saved in memory successfully');
  
  // Send success message to the renderer
  if (event && event.sender) {
    event.sender.send('credentials-success', 'Credentials saved successfully');
  }
  
  console.log('Credentials window closed');
});

// Expose the uploadToGoogleSheets function to the global scope
global.uploadToGoogleSheets = async function(filePath) {
  console.log(`[DEV] Calling uploadToGoogleSheets with path: ${filePath}`);
  
  // Simple mock implementation - don't try to call the real function recursively
  console.log('[DEV] Using mock implementation for uploadToGoogleSheets');
  
  // You can add some validation logic if needed
  if (!filePath || typeof filePath !== 'string') {
    throw new Error('[DEV] Invalid file path provided');
  }
  
  // Return a success message without calling any other function
  return '[DEV] Upload simulation successful';
};

// Similarly, expose the showErrorToUser function
global.showErrorToUser = function(title, message) {
  console.log(`[DEV] Error: ${title} - ${message}`);
  // We'll use Electron's dialog directly for simplicity
  const { dialog } = require('electron');
  dialog.showErrorBox(title, message);
};

// Create a handler to capture the userCredentials object from main.js
const originalObjectDefineProperty = Object.defineProperty;
Object.defineProperty = function(obj, prop, descriptor) {
  // Attempt to capture userCredentials variable from main.js
  if (prop === 'userCredentials' && descriptor && descriptor.value) {
    console.log('[DEV] Captured userCredentials reference from main.js');
    global.mainJsUserCredentials = descriptor.value;
  }
  return originalObjectDefineProperty.apply(this, arguments);
};

// Now load main.js - this is important to do after we've intercepted handlers
console.log('[DEV] Loading main.js with interception in place');
require('./main');

console.log('[DEV] Development script initialized');