const express = require('express');
const path = require('path');
const fs = require('fs');
const multer = require('multer');
const { GoogleSpreadsheet } = require('google-spreadsheet');
const { JWT } = require('google-auth-library');
const { GoogleAuth } = require('google-auth-library');
const axios = require('axios');
const session = require('express-session');
const FileStore = require('session-file-store')(session);
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

// Create necessary directories
const uploadDir = path.join(__dirname, 'uploads');
const processedDir = path.join(__dirname, 'processed');
const sessionsDir = path.join(__dirname, 'sessions');
const chunksDir = path.join(__dirname, 'chunks');

[uploadDir, processedDir, sessionsDir, chunksDir].forEach(dir => {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
    console.log(`Created directory: ${dir}`);
  }
});

// Set up multer storage configuration for credential file upload
const credentialStorage = multer.diskStorage({
  destination: function (req, file, cb) {
    cb(null, uploadDir);
  },
  filename: function (req, file, cb) {
    cb(null, file.originalname);
  }
});

// Set up multer storage configuration for directory uploads
const directoryStorage = multer.diskStorage({
  destination: function (req, file, cb) {
    // Store files temporarily in the uploads directory
    cb(null, uploadDir);
  },
  filename: function (req, file, cb) {
    // Use a unique filename to avoid collisions
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
    // Keep the original extension
    const ext = path.extname(file.originalname);
    cb(null, `${uniqueSuffix}${ext}`);
  }
});

// Create separate multer instances for different upload types
const uploadCredentials = multer({ storage: credentialStorage });
const uploadFiles = multer({ storage: directoryStorage });
const uploadBatch = multer({ storage: directoryStorage });

// Session store to track batch uploads
const batchUploads = {};

// Set the view engine to ejs
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// Middleware to parse form data
app.use(express.urlencoded({ extended: true }));
app.use(express.json({ limit: '50mb' }));
app.use(express.static(path.join(__dirname, 'public')));

// Use file-based session store (no Redis needed)
app.use(session({
  store: new FileStore({
    path: sessionsDir,
    retries: 0,
    ttl: 86400, // 1 day in seconds
    reapInterval: 3600 // 1 hour in seconds
  }),
  secret: process.env.SESSION_SECRET || 'your-secret-key',
  resave: true,  // Changed to true
  saveUninitialized: true,  // Changed to true
  cookie: { 
    secure: false,  // Changed to false for reliable cookie handling
    maxAge: 24 * 60 * 60 * 1000 // 24 hours
  }
}));

// Helper function to get authentication token for Cloud Run
async function getAuthToken(credentials) {
  try {
    console.log('Getting auth token for Cloud Run');
    
    // Create a JWT client with the provided credentials
    const jwtClient = new JWT(
      credentials.googleCredentialsJson.client_email,
      null,
      credentials.googleCredentialsJson.private_key,
      ['https://www.googleapis.com/auth/cloud-platform']
    );
    
    // Get an ID token for the Cloud Run service
    const idToken = await jwtClient.authorize();
    
    // Return the Bearer token
    return `Bearer ${idToken.id_token || idToken.access_token}`;
  } catch (error) {
    console.error('Error getting auth token:', error);
    return null; // Return null so we can try without auth as fallback
  }
}

// Helper function to make authenticated Cloud Run requests
async function cloudRunRequest(url, method, data, credentials) {
  try {
    const token = await getAuthToken(credentials);
    
    // Try with authentication first
    if (token) {
      console.log(`Making authenticated ${method} request to ${url}`);
      return await axios({
        url,
        method,
        data,
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': token 
        },
        timeout: 300000 // 5 minutes
      });
    } else {
      throw new Error('No authentication token available');
    }
  } catch (authError) {
    console.log(`Authenticated request failed, trying without authentication: ${authError.message}`);
    
    // If authentication fails, try without authentication
    return await axios({
      url,
      method,
      data,
      headers: { 'Content-Type': 'application/json' },
      timeout: 300000 // 5 minutes
    });
  }
}

// Routes
app.get('/', (req, res) => {
    console.log('Root route accessed');
    console.log('Session ID:', req.sessionID);
    console.log('Has credentials:', !!(req.session && req.session.credentials));
    
    // Check if credentials exist in session
    if (req.session && req.session.credentials && 
        req.session.credentials.googleSheetId && 
        req.session.credentials.googleCredentialsJson) {
      console.log('Valid credentials found, rendering index');
      
      // Pass the Cloud Run URL to the template
      const cloudRunUrl = req.session.credentials.cloudRunUrl || 
                         process.env.CLOUD_RUN_URL || 
                         'https://processjson-1061451118144.us-central1.run.app';
      
      res.render('index', { 
        hasCredentials: true,
        cloudRunUrl: cloudRunUrl
      });
    } else {
      console.log('No valid credentials found, rendering credentials form');
      // Removed session regeneration - it was causing the credentials to be lost
      res.render('credentials', { error: null });
    }
  });
  
// Analysis page route - simplified to just redirect to home
app.get('/analysis', (req, res) => {
  console.log('Analysis route accessed - redirecting to home');
  console.log('Session ID:', req.sessionID);
  
  // Check if credentials exist in session
  if (req.session && req.session.credentials && 
      req.session.credentials.googleSheetId && 
      req.session.credentials.googleCredentialsJson) {
    
    // Simply redirect to home where the modal will be available
    res.redirect('/');
  } else {
    // Redirect to credentials page if not authenticated
    res.render('credentials', { error: 'Please set your credentials first' });
  }
});
  
// CORS middleware to allow Cloud Run to respond to preflight requests
app.use((req, res, next) => {
  // This is a simple CORS middleware that will help your frontend
  // communicate with the Cloud Run backend when needed
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Authorization');
  
  // Handle preflight requests
  if (req.method === 'OPTIONS') {
    return res.sendStatus(200);
  }
  
  next();
});

// Handle credentials submission
app.post('/credentials', uploadCredentials.single('googleCredentialsFile'), (req, res) => {
  try {
    console.log('Credentials submission received');
    console.log('Session ID:', req.sessionID);
    console.log('Form data sheet ID:', req.body.googleSheetId);
    console.log('File received:', !!req.file);
    
    if (!req.body.googleSheetId) {
      return res.render('credentials', { error: 'Google Sheet ID is required' });
    }
    
    if (!req.file) {
      return res.render('credentials', { error: 'Google credentials file is required' });
    }
    
    // Read the credentials file
    const filePath = req.file.path;
    const fileContent = fs.readFileSync(filePath, 'utf8');
    
    try {
      const googleCredsContent = JSON.parse(fileContent);
      
      // Validate basic structure
      if (!googleCredsContent.client_email || !googleCredsContent.private_key) {
        return res.render('credentials', { error: 'Invalid credentials file format' });
      }
      
      // Store in session
      if (!req.session) {
        console.error('No session object found');
        return res.render('credentials', { error: 'Session error - please try again' });
      }
      
      req.session.credentials = {
        googleSheetId: req.body.googleSheetId.trim(),
        googleCredentialsJson: googleCredsContent,
        cloudRunUrl: process.env.CLOUD_RUN_URL || 'https://processjson-1061451118144.us-central1.run.app'
      };
      
      console.log('Credentials stored in session');
      
      // Remove the file after reading
      fs.unlinkSync(filePath);
      
      // Force session save
      req.session.save((err) => {
        if (err) {
          console.error('Error saving session:', err);
          return res.render('credentials', { error: 'Error saving credentials session' });
        }
        
        console.log('Session saved successfully');
        
        // Using a more direct redirect method
        console.log('Redirecting to root page');
        res.writeHead(302, {
          'Location': '/'
        });
        res.end();
      });
    } catch (parseError) {
      console.error('JSON parse error:', parseError);
      return res.render('credentials', { error: `Invalid JSON in credentials file: ${parseError.message}` });
    }
  } catch (error) {
    console.error('Error processing credentials:', error);
    res.render('credentials', { error: `Error: ${error.message}` });
  }
});

// NEW BATCH PROCESSING ROUTES THAT MATCH FRONTEND EXPECTATIONS

// Handle batch file upload
app.post('/upload-batch', uploadBatch.array('files'), async (req, res) => {
  try {
    console.log('Batch upload request received');
    console.log('Files count:', req.files?.length || 0);
    console.log('Directory name:', req.body.directoryName);
    console.log('Batch index:', req.body.batchIndex);
    console.log('Total batches:', req.body.totalBatches);
    console.log('Upload ID:', req.body.uploadId);
    
    if (!req.session || !req.session.credentials) {
      return res.status(401).json({ success: false, message: 'Credentials not set' });
    }
    
    if (!req.files || req.files.length === 0) {
      return res.status(400).json({ success: false, message: 'No files uploaded' });
    }
    
    if (!req.body.directoryName || !req.body.uploadId) {
      return res.status(400).json({ success: false, message: 'Directory name and upload ID are required' });
    }
    
    // Create a directory for this batch
    const dirName = req.body.directoryName.trim();
    const uploadId = req.body.uploadId;
    const batchIndex = parseInt(req.body.batchIndex) || 0;
    
    // Create main upload directory if it doesn't exist
    const mainUploadDir = path.join(uploadDir, uploadId);
    if (!fs.existsSync(mainUploadDir)) {
      fs.mkdirSync(mainUploadDir, { recursive: true });
    }
    
    // Create directory for this specific batch
    const batchDirPath = path.join(mainUploadDir, `batch_${batchIndex}`);
    if (!fs.existsSync(batchDirPath)) {
      fs.mkdirSync(batchDirPath, { recursive: true });
    }
    
    // Check if we have relative paths information
    const filePaths = req.body.filePaths ? 
      (Array.isArray(req.body.filePaths) ? req.body.filePaths : [req.body.filePaths]) : 
      req.files.map(file => file.originalname);
    
    console.log(`Processing ${filePaths.length} file paths`);
    
    // Move files to the batch directory, preserving structure if available
    for (let i = 0; i < req.files.length; i++) {
      const file = req.files[i];
      const relativePath = filePaths[i] || file.originalname;
      
      // Check if the file is in a subdirectory
      const targetDir = path.dirname(relativePath);
      if (targetDir && targetDir !== '.' && targetDir !== '/') {
        // Create the subdirectory structure
        const fullTargetDir = path.join(batchDirPath, targetDir);
        if (!fs.existsSync(fullTargetDir)) {
          fs.mkdirSync(fullTargetDir, { recursive: true });
        }
      }
      
      // Get the basename (just the filename part)
      const basename = path.basename(relativePath);
      
      // Move the file to its final location
      const targetPath = path.join(batchDirPath, targetDir === '.' ? basename : relativePath);
      fs.renameSync(file.path, targetPath);
      
      console.log(`Moved file from ${file.path} to ${targetPath}`);
    }
    
    // Track this batch in our uploads store
    if (!batchUploads[uploadId]) {
      batchUploads[uploadId] = {
        directoryName: dirName,
        batchesReceived: {},
        totalBatches: parseInt(req.body.totalBatches) || 1,
        completed: false
      };
    }
    
    batchUploads[uploadId].batchesReceived[batchIndex] = true;
    
    // Return success response
    res.json({
      success: true,
      message: `Batch ${batchIndex + 1} uploaded successfully`,
      uploadId: uploadId,
      batchesProcessed: Object.keys(batchUploads[uploadId].batchesReceived).length,
      totalBatches: batchUploads[uploadId].totalBatches
    });
    
  } catch (error) {
    console.error('Error handling batch upload:', error);
    res.status(500).json({ success: false, message: `Error: ${error.message}` });
  }
});

// Handle chunk upload for large files
app.post('/upload-chunk', uploadBatch.single('fileChunk'), async (req, res) => {
  try {
    console.log('Chunk upload request received');
    console.log('Chunk index:', req.body.chunkIndex);
    console.log('Total chunks:', req.body.totalChunks);
    console.log('File name:', req.body.fileName);
    console.log('Upload ID:', req.body.uploadId);
    
    if (!req.session || !req.session.credentials) {
      return res.status(401).json({ success: false, message: 'Credentials not set' });
    }
    
    if (!req.file) {
      return res.status(400).json({ success: false, message: 'No chunk uploaded' });
    }
    
    const requiredFields = ['uploadId', 'fileName', 'chunkIndex', 'totalChunks', 'filePath'];
    for (const field of requiredFields) {
      if (!req.body[field]) {
        return res.status(400).json({ success: false, message: `${field} is required` });
      }
    }
    
    // Create directory for chunks if it doesn't exist
    const uploadId = req.body.uploadId;
    const fileName = req.body.fileName;
    const chunkDir = path.join(chunksDir, uploadId, fileName);
    fs.mkdirSync(chunkDir, { recursive: true });
    
    // Move the chunk to its storage location
    const chunkIndex = parseInt(req.body.chunkIndex);
    const chunkPath = path.join(chunkDir, `chunk_${chunkIndex}`);
    fs.renameSync(req.file.path, chunkPath);
    
    console.log(`Chunk ${chunkIndex} stored at ${chunkPath}`);
    
    // Track this upload in our store
    if (!batchUploads[uploadId]) {
      batchUploads[uploadId] = {
        directoryName: req.body.directoryName,
        chunks: {},
        totalBatches: 1,
        completed: false
      };
    }
    
    if (!batchUploads[uploadId].chunks) {
      batchUploads[uploadId].chunks = {};
    }
    
    if (!batchUploads[uploadId].chunks[fileName]) {
      batchUploads[uploadId].chunks[fileName] = {
        receivedChunks: {},
        totalChunks: parseInt(req.body.totalChunks),
        filePath: req.body.filePath
      };
    }
    
    batchUploads[uploadId].chunks[fileName].receivedChunks[chunkIndex] = true;
    
    res.json({
      success: true,
      message: `Chunk ${chunkIndex + 1}/${req.body.totalChunks} received successfully`,
      uploadId: uploadId,
      fileName: fileName,
      chunksReceived: Object.keys(batchUploads[uploadId].chunks[fileName].receivedChunks).length,
      totalChunks: batchUploads[uploadId].chunks[fileName].totalChunks
    });
    
  } catch (error) {
    console.error('Error handling chunk upload:', error);
    res.status(500).json({ success: false, message: `Error: ${error.message}` });
  }
});

// Finalize chunks for a large file
app.post('/finalize-chunks', express.json(), async (req, res) => {
  try {
    console.log('Finalize chunks request received');
    console.log('Upload ID:', req.body.uploadId);
    console.log('File name:', req.body.fileName);
    
    if (!req.session || !req.session.credentials) {
      return res.status(401).json({ success: false, message: 'Credentials not set' });
    }
    
    const requiredFields = ['uploadId', 'fileName', 'filePath', 'totalChunks'];
    for (const field of requiredFields) {
      if (!req.body[field]) {
        return res.status(400).json({ success: false, message: `${field} is required` });
      }
    }
    
    const uploadId = req.body.uploadId;
    const fileName = req.body.fileName;
    const filePath = req.body.filePath;
    const totalChunks = parseInt(req.body.totalChunks);
    
    // Verify that all chunks have been received
    if (!batchUploads[uploadId] || 
        !batchUploads[uploadId].chunks || 
        !batchUploads[uploadId].chunks[fileName]) {
      return res.status(400).json({ 
        success: false, 
        message: 'No chunks found for this file' 
      });
    }
    
    const fileInfo = batchUploads[uploadId].chunks[fileName];
    const receivedChunks = Object.keys(fileInfo.receivedChunks).length;
    
    if (receivedChunks < totalChunks) {
      return res.status(400).json({ 
        success: false, 
        message: `Only ${receivedChunks}/${totalChunks} chunks received` 
      });
    }
    
    // Create main upload directory structure if it doesn't exist
    const directoryName = batchUploads[uploadId].directoryName;
    const mainUploadDir = path.join(uploadDir, uploadId);
    if (!fs.existsSync(mainUploadDir)) {
      fs.mkdirSync(mainUploadDir, { recursive: true });
    }
    
    // Create target directory structure
    const targetDir = path.dirname(filePath);
    if (targetDir && targetDir !== '.' && targetDir !== '/') {
      const fullTargetDir = path.join(mainUploadDir, targetDir);
      if (!fs.existsSync(fullTargetDir)) {
        fs.mkdirSync(fullTargetDir, { recursive: true });
      }
    }
    
    // Combine all chunks into a single file
    const targetPath = path.join(mainUploadDir, filePath);
    const chunkDir = path.join(chunksDir, uploadId, fileName);
    
    // Create write stream for the combined file
    const writeStream = fs.createWriteStream(targetPath);
    
    // Process chunks in order
    for (let i = 0; i < totalChunks; i++) {
      const chunkPath = path.join(chunkDir, `chunk_${i}`);
      
      // Wait for the chunk to be written
      await new Promise((resolve, reject) => {
        const chunkReadStream = fs.createReadStream(chunkPath);
        chunkReadStream.pipe(writeStream, { end: false });
        chunkReadStream.on('end', resolve);
        chunkReadStream.on('error', reject);
      });
      
      // Remove the chunk after it's been written
      fs.unlinkSync(chunkPath);
    }
    
    // Close the write stream
    writeStream.end();
    
    // Wait for file to be fully written
    await new Promise(resolve => writeStream.on('finish', resolve));
    
    console.log(`Combined file written to ${targetPath}`);
    
    // Remove the chunk directory
    fs.rmdirSync(chunkDir, { recursive: true });
    
    res.json({
      success: true,
      message: `File ${fileName} (${totalChunks} chunks) combined successfully`,
      uploadId: uploadId,
      filePath: filePath
    });
    
  } catch (error) {
    console.error('Error finalizing chunks:', error);
    res.status(500).json({ success: false, message: `Error: ${error.message}` });
  }
});

// Finalize upload and process all batches
app.post('/finalize-upload', express.json(), async (req, res) => {
  try {
    console.log('Finalize upload request received');
    console.log('Upload ID:', req.body.uploadId);
    console.log('Directory name:', req.body.directoryName);
    console.log('Total batches:', req.body.totalBatches);
    
    if (!req.session || !req.session.credentials) {
      return res.status(401).json({ success: false, message: 'Credentials not set' });
    }
    
    const requiredFields = ['uploadId', 'directoryName', 'totalBatches'];
    for (const field of requiredFields) {
      if (!req.body[field]) {
        return res.status(400).json({ success: false, message: `${field} is required` });
      }
    }
    
    const uploadId = req.body.uploadId;
    const directoryName = req.body.directoryName;
    const totalBatches = parseInt(req.body.totalBatches);
    
    // Check if all batches have been received
    if (!batchUploads[uploadId]) {
      return res.status(400).json({ success: false, message: 'No batches found for this upload' });
    }
    
    const uploadInfo = batchUploads[uploadId];
    const receivedBatches = Object.keys(uploadInfo.batchesReceived || {}).length;
    
    if (receivedBatches < totalBatches) {
      return res.status(400).json({ 
        success: false, 
        message: `Only ${receivedBatches}/${totalBatches} batches received` 
      });
    }
    
    // Mark upload as completed so we don't process it multiple times
    if (uploadInfo.completed) {
      return res.status(400).json({ success: false, message: 'This upload has already been processed' });
    }
    uploadInfo.completed = true;
    
    // Move files from the temporary upload location to the final directory
    const uploadDirPath = path.join(uploadDir, uploadId);
    const finalDirPath = path.join(uploadDir, directoryName);
    
    // If directory exists, use a timestamped name to avoid conflicts
    let targetDirPath = finalDirPath;
    if (fs.existsSync(finalDirPath)) {
      const timestamp = Date.now();
      const newDirName = `${directoryName}_${timestamp}`;
      targetDirPath = path.join(uploadDir, newDirName);
    }
    
    // Create the target directory
    fs.mkdirSync(targetDirPath, { recursive: true });
    
    // Find all files in the upload directory structure
    const getAllFiles = (dir) => {
      let results = [];
      const list = fs.readdirSync(dir);
      
      list.forEach((file) => {
        const filePath = path.join(dir, file);
        const stat = fs.statSync(filePath);
        
        if (stat && stat.isDirectory()) {
          // Recursive call for subdirectories
          results = results.concat(getAllFiles(filePath));
        } else {
          // Add file with its relative path from uploadDir
          const relativePath = path.relative(uploadDirPath, filePath);
          results.push({ path: filePath, relativePath });
        }
      });
      
      return results;
    };
    
    const allFiles = getAllFiles(uploadDirPath);
    console.log(`Found ${allFiles.length} files to move to the final directory`);
    
    // Move files to the final directory
    for (const file of allFiles) {
      const targetDir = path.dirname(file.relativePath);
      
      // Create subdirectory structure if needed
      if (targetDir && targetDir !== '.' && targetDir !== '/') {
        const fullTargetDir = path.join(targetDirPath, targetDir);
        if (!fs.existsSync(fullTargetDir)) {
          fs.mkdirSync(fullTargetDir, { recursive: true });
        }
      }
      
      // Move the file
      const targetFilePath = path.join(targetDirPath, file.relativePath);
      fs.renameSync(file.path, targetFilePath);
      console.log(`Moved ${file.path} to ${targetFilePath}`);
    }
    
    // Process the uploaded directory with Cloud Run
    try {
      const result = await processFiles(targetDirPath, req.session.credentials);
      
      // Clean up
      console.log('Cleaning up temporary files');
      if (fs.existsSync(uploadDirPath)) {
        fs.rmdirSync(uploadDirPath, { recursive: true });
      }
      
      // Remove from memory
      delete batchUploads[uploadId];
      
      res.json({
        success: true,
        message: 'Processing completed successfully',
        processResult: result.processResult || 'Files processed successfully',
        uploadId: uploadId
      });
    } catch (processingError) {
      console.error('Error processing files:', processingError);
      
      let errorMessage = processingError.message || 'Unknown processing error';
      if (processingError.response) {
        errorMessage = `Cloud Run service error (${processingError.response.status}): ${processingError.response.data.error || processingError.response.statusText}`;
      }
      
      res.status(500).json({ 
        success: false, 
        message: errorMessage,
        details: processingError.toString()
      });
    }
    
  } catch (error) {
    console.error('Error finalizing upload:', error);
    res.status(500).json({ success: false, message: `Error: ${error.message}` });
  }
});

// Handle directory upload
app.post('/upload-directory', uploadFiles.array('files'), async (req, res) => {
  console.log("UPLOAD-DIRECTORY CALLED");
  try {
    console.log('Directory upload request received');
    console.log('Session ID:', req.sessionID);
    console.log('Files count:', req.files?.length || 0);
    console.log('Directory name:', req.body.directoryName);
    console.log('File paths:', req.body.filePaths ? 'Present' : 'Not present');
    console.log('Has credentials in session:', !!(req.session && req.session.credentials));
    
    if (!req.files || req.files.length === 0) {
      return res.status(400).json({ success: false, message: 'No files uploaded' });
    }
    
    if (!req.body.directoryName) {
      return res.status(400).json({ success: false, message: 'Directory name is required' });
    }
    
    if (!req.session || !req.session.credentials) {
      return res.status(401).json({ success: false, message: 'Credentials not set' });
    }
    
    // Create a directory for this upload
    const dirName = req.body.directoryName.trim();
    let uploadDirPath = path.join(__dirname, 'uploads', dirName);
    
    // Ensure directory doesn't already exist
    if (fs.existsSync(uploadDirPath)) {
      // Use a timestamped version to avoid conflicts
      const timestamp = Date.now();
      const newDirName = `${dirName}_${timestamp}`;
      console.log(`Directory ${dirName} already exists, using ${newDirName} instead`);
      uploadDirPath = path.join(__dirname, 'uploads', newDirName);
    }
    
    fs.mkdirSync(uploadDirPath, { recursive: true });
    
    // Check if we have relative paths information
          const filePaths = req.body.filePaths ? 
      (Array.isArray(req.body.filePaths) ? req.body.filePaths : [req.body.filePaths]) : 
      req.files.map(file => file.originalname);
    
    console.log(`Processing ${filePaths.length} file paths`);
    
    // Move files to the directory, preserving subdirectories if info available
    for (let i = 0; i < req.files.length; i++) {
      const file = req.files[i];
      const relativePath = filePaths[i] || file.originalname;
      
      // Check if the file is in a subdirectory
      const targetDir = path.dirname(relativePath);
      if (targetDir && targetDir !== '.' && targetDir !== '/') {
        // Create the subdirectory structure
        const fullTargetDir = path.join(uploadDirPath, targetDir);
        if (!fs.existsSync(fullTargetDir)) {
          fs.mkdirSync(fullTargetDir, { recursive: true });
        }
      }
      
      // Get the basename (just the filename part)
      const basename = path.basename(relativePath);
      
      // Move the file to its final location
      const targetPath = path.join(uploadDirPath, targetDir === '.' ? basename : relativePath);
      fs.renameSync(file.path, targetPath);
      
      console.log(`Moved file from ${file.path} to ${targetPath}`);
    }
    
    console.log(`Files moved to directory: ${uploadDirPath}`);
    
    // Check for at least one JSON file
    const hasJsonFile = req.files.some(file => file.originalname.toLowerCase().endsWith('.json'));
    if (!hasJsonFile) {
      return res.status(400).json({ 
        success: false, 
        message: 'At least one JSON file is required in the upload' 
      });
    }
    
    // Process the uploaded directory
    try {
      const result = await processFiles(uploadDirPath, req.session.credentials);
      res.json(result);
    } catch (processingError) {
      console.error('Error processing files:', processingError);
      let errorMessage = processingError.message || 'Unknown processing error';
      
      // Check for specific error types
      if (processingError.response) {
        // The request was made and the server responded with a status code outside of 2xx range
        const statusCode = processingError.response.status;
        const statusText = processingError.response.statusText;
        const responseData = processingError.response.data;
        
        console.error(`Cloud Run API error: ${statusCode} ${statusText}`);
        console.error('Response data:', responseData);
        
        errorMessage = `Cloud Run service error (${statusCode}): ${responseData.error || statusText}`;
      } else if (processingError.request) {
        // The request was made but no response was received
        console.error('No response received from Cloud Run service');
        errorMessage = 'No response from Cloud Run service. The service may be unavailable or the request timed out.';
      }
      
      res.status(500).json({ 
        success: false, 
        message: errorMessage,
        details: processingError.toString()
      });
    }
  } catch (error) {
    console.error('Error handling directory upload:', error);
    res.status(500).json({ success: false, message: `Error: ${error.message}` });
  }
});

// Legacy route - handle file upload for processing 
app.post('/upload', uploadFiles.array('files', 20), async (req, res) => {
  try {
    console.log('Upload request received (legacy route)');
    console.log('Session ID:', req.sessionID);
    console.log('Files count:', req.files?.length || 0);
    console.log('Has credentials in session:', !!(req.session && req.session.credentials));
    
    if (!req.files || req.files.length === 0) {
      return res.status(400).json({ success: false, message: 'No files uploaded' });
    }
    
    if (!req.session || !req.session.credentials) {
      return res.status(401).json({ success: false, message: 'Credentials not set' });
    }
    
    // Create a directory for this upload batch
    const timestamp = Date.now();
    const uploadDirPath = path.join(__dirname, 'uploads', `batch_${timestamp}`);
    fs.mkdirSync(uploadDirPath, { recursive: true });
    
    // Move files to the batch directory
    for (const file of req.files) {
      fs.renameSync(file.path, path.join(uploadDirPath, file.originalname));
    }
    
    console.log(`Files moved to batch directory: ${uploadDirPath}`);
    
    // Process the uploaded files
    try {
      const result = await processFiles(uploadDirPath, req.session.credentials);
      res.json(result);
    } catch (processingError) {
      console.error('Error processing files:', processingError);
      
      let errorMessage = processingError.message || 'Unknown processing error';
      if (processingError.response) {
        const statusCode = processingError.response.status;
        errorMessage = `Cloud Run service error (${statusCode}): ${processingError.response.data.error || processingError.response.statusText}`;
      }
      
      res.status(500).json({ 
        success: false, 
        message: errorMessage 
      });
    }
  } catch (error) {
    console.error('Error handling upload:', error);
    res.status(500).json({ success: false, message: `Error: ${error.message}` });
  }
});

// Refresh Tableau dashboard API endpoint
app.post('/refresh-dashboard', (req, res) => {
  try {
    console.log('Dashboard refresh requested');
    // This endpoint doesn't actually refresh the dashboard on the server
    // It's just a signal to the client to refresh the dashboard
    res.json({ success: true, message: 'Dashboard refresh signal sent' });
  } catch (error) {
    console.error('Error handling dashboard refresh:', error);
    res.status(500).json({ success: false, message: `Error: ${error.message}` });
  }
});

// Debug endpoint
app.get('/debug-session', (req, res) => {
  res.json({
    sessionID: req.sessionID,
    hasSession: !!req.session,
    hasCredentials: !!(req.session && req.session.credentials),
    sheetId: req.session?.credentials?.googleSheetId || null,
    hasGoogleCreds: !!(req.session?.credentials?.googleCredentialsJson),
    cloudRunUrl: req.session?.credentials?.cloudRunUrl || null
  });
});

// Cloud Run health check endpoint
app.get('/check-cloud-run', async (req, res) => {
  try {
    if (!req.session || !req.session.credentials) {
      return res.status(401).json({ success: false, message: 'Credentials not set' });
    }
    
    const cloudRunUrl = req.session.credentials.cloudRunUrl;
    console.log(`Checking Cloud Run service at: ${cloudRunUrl}`);
    
    try {
      // Try to get an ID token for authentication
      const auth = new GoogleAuth();
      const client = await auth.getIdTokenClient(cloudRunUrl);
      const headers = await client.getRequestHeaders();
      const token = headers.Authorization;
      
      // Call the health endpoint with authentication
      const response = await axios.get(`${cloudRunUrl}/health`, {
        headers: { 
          'Authorization': token 
        },
        timeout: 10000 // 10 seconds timeout
      });
      
      if (response.status === 200) {
        return res.json({
          success: true,
          message: 'Cloud Run service is healthy',
          details: response.data
        });
      } else {
        return res.json({
          success: false,
          message: `Cloud Run service returned status ${response.status}`,
          details: response.data
        });
      }
    } catch (authError) {
      console.log('Failed to authenticate with Cloud Run, trying without authentication');
      
      // Try without authentication as fallback
      try {
        const response = await axios.get(`${cloudRunUrl}/health`, {
          timeout: 10000
        });
        
        return res.json({
          success: true,
          message: 'Cloud Run service is healthy (public access)',
          details: response.data
        });
      } catch (publicError) {
        return res.status(503).json({
          success: false,
          message: 'Cloud Run service is unavailable',
          error: publicError.message
        });
      }
    }
  } catch (error) {
    console.error('Error checking Cloud Run health:', error);
    return res.status(500).json({
      success: false,
      message: 'Error checking Cloud Run health',
      error: error.message
    });
  }
});

// Clear credentials (useful for testing)
app.get('/clear-credentials', (req, res) => {
  if (req.session) {
    req.session.destroy((err) => {
      if (err) {
        console.error('Error destroying session:', err);
      }
      res.redirect('/');
    });
  } else {
    res.redirect('/');
  }
});

async function processFiles(inputDir, credentials) {
  try {
    // Prepare output directory
    const dirName = path.basename(inputDir);
    const outputDir = path.join(__dirname, 'processed', dirName);
    fs.mkdirSync(outputDir, { recursive: true });
    
    console.log(`Processing files from ${inputDir} to ${outputDir}`);
    
    // Recursively find all files in the input directory and subdirectories
    const getAllFiles = (dir) => {
      let results = [];
      const list = fs.readdirSync(dir);
      
      list.forEach((file) => {
        const filePath = path.join(dir, file);
        const stat = fs.statSync(filePath);
        
        if (stat && stat.isDirectory()) {
          // Recursive call for subdirectories
          results = results.concat(getAllFiles(filePath));
        } else {
          // Add file with its relative path from inputDir
          const relativePath = path.relative(inputDir, filePath);
          results.push({ path: filePath, relativePath });
        }
      });
      
      return results;
    };
    
    const allFiles = getAllFiles(inputDir);
    const jsonFiles = allFiles.filter(file => file.path.endsWith('.json'));
    const mediaFiles = allFiles.filter(file => 
      file.path.endsWith('.mp4') || 
      file.path.endsWith('.jpg') || 
      file.path.endsWith('.jpeg') || 
      file.path.endsWith('.png')
    );
    
    console.log(`Found ${jsonFiles.length} JSON files and ${mediaFiles.length} media files`);
    
    if (jsonFiles.length === 0) {
      throw new Error('No JSON files found in the input directory');
    }
    
    // Read JSON content
    const jsonContents = {};
    for (const file of jsonFiles) {
      const content = fs.readFileSync(file.path, 'utf8');
      jsonContents[file.relativePath] = content;
    }
    
    // Instead of sending all media files at once, create a manifest of them
    const mediaManifest = mediaFiles.map(file => ({
      relativePath: file.relativePath,
      size: fs.statSync(file.path).size
    }));
    
    console.log('Prepared initial payload for Cloud Run');
    
    // Initial payload with JSON content and media manifest
    const initialPayload = {
      jsonContents,
      mediaManifest,
      outputDir: path.basename(outputDir),
      preserveStructure: true
    };
    
    console.log(`Calling Cloud Run service at: ${credentials.cloudRunUrl}`);
    
    // Make request to Cloud Run service using the helper function
    const initialResponse = await cloudRunRequest(
      `${credentials.cloudRunUrl}/process-json-init`,
      'POST',
      initialPayload,
      credentials
    );
    
    console.log('Received response for initial phase');
    
    if (!initialResponse.data || !initialResponse.data.success) {
      const errorMsg = initialResponse.data?.message || 'Invalid response from Cloud Run service';
      throw new Error(errorMsg);
    }
    
    // Get session ID or other reference from response
    const sessionId = initialResponse.data.sessionId;
    
    // Upload media files in batches if needed
    if (mediaFiles.length > 0 && initialResponse.data.needsMediaFiles) {
      console.log(`Uploading ${mediaFiles.length} media files in batches`);
      
      // Chunk media files into batches of 5 (or smaller for large files)
      const batchSize = 5;
      for (let i = 0; i < mediaFiles.length; i += batchSize) {
        const batch = mediaFiles.slice(i, i + batchSize);
        console.log(`Uploading batch ${Math.floor(i/batchSize) + 1} of ${Math.ceil(mediaFiles.length/batchSize)}`);
        
        // Prepare batch data
        const batchData = {
          sessionId,
          mediaFiles: {}
        };
        
        // Read and encode media files for this batch
        for (const file of batch) {
          const content = fs.readFileSync(file.path);
          const base64Content = content.toString('base64');
          batchData.mediaFiles[file.relativePath] = base64Content;
        }
        
        // Send batch to Cloud Run using helper function
        await cloudRunRequest(
          `${credentials.cloudRunUrl}/upload-media-batch`,
          'POST',
          batchData,
          credentials
        );
        
        console.log(`Completed batch ${Math.floor(i/batchSize) + 1}`);
      }
    }
    
    // Trigger final processing after all media is uploaded
    console.log('Starting final processing phase');
    
    // Make the final processing request using helper function
    const finalResponse = await cloudRunRequest(
      `${credentials.cloudRunUrl}/finalize-processing`,
      'POST',
      { sessionId },
      credentials
    );
    
    console.log('Received final response from Cloud Run');
    
    // Write the processed results
    if (finalResponse.data && finalResponse.data.result) {
      const resultPath = path.join(outputDir, 'result.json');
      fs.writeFileSync(resultPath, JSON.stringify(finalResponse.data.result, null, 2));
      
      console.log(`Results written to: ${resultPath}`);
      
      // Upload to Google Sheets
      console.log('Starting upload to Google Sheets');
      const uploadResult = await uploadToGoogleSheets(resultPath, credentials);
      
      return {
        success: true,
        message: 'Processing and upload completed successfully',
        processResult: finalResponse.data.message || 'Processing completed',
        uploadResult
      };
    } else {
      throw new Error(finalResponse.data?.error || 'Invalid response from Cloud Run service');
    }
  } catch (error) {
    console.error('Error in processing:', error);
    throw error;
  }
}

async function uploadToGoogleSheets(filePath, credentials) {
  try {
    console.log(`Uploading data from ${filePath} to Google Sheets`);
    
    // Check if file exists
    if (!fs.existsSync(filePath)) {
      throw new Error(`File does not exist at path: ${filePath}`);
    }
    
    // Set up authentication
    console.log('Setting up Google Sheets authentication');
    const serviceAccount = new JWT({
      email: credentials.googleCredentialsJson.client_email,
      key: credentials.googleCredentialsJson.private_key,
      scopes: ['https://www.googleapis.com/auth/spreadsheets'],
    });
    
    const doc = new GoogleSpreadsheet(credentials.googleSheetId, serviceAccount);
    await doc.loadInfo();
    console.log(`Connected to Google Sheet: ${doc.title}`);
    
    // Read and parse the file
    const fileData = fs.readFileSync(filePath, 'utf-8');
    const jsonData = JSON.parse(fileData);
    
    if (!jsonData.messages || !Array.isArray(jsonData.messages)) {
      throw new Error('"messages" key is missing or not an array');
    }
    
    const messages = jsonData.messages;
    console.log(`Found ${messages.length} messages to upload`);
    
    if (messages.length === 0) {
      throw new Error('"messages" array is empty');
    }
    
    const sheetName = "allMessages";
    const expectedHeaders = [
      "id", "date", "date_unixtime", "from", "text", "reply_id", "LANGUAGE", 
      "TRANSLATED_TEXT", "parent_category", "parent_confidence_score", 
      "child_category", "child_confidence_score",
      "locations_names", "locations_coordinates", "location_confidence",
      "source_file" // Added to track which file the message came from
    ];
    
    // Get or create sheet
    let sheet;
    
    try {
      // Try to get the existing sheet
      if (doc.sheetsByTitle[sheetName]) {
        sheet = doc.sheetsByTitle[sheetName];
        await sheet.loadHeaderRow();
        console.log(`Using existing sheet: ${sheetName}`);
        
        const existingHeaders = sheet.headerValues || [];
        const missingHeaders = expectedHeaders.filter(header => !existingHeaders.includes(header));
        
        if (missingHeaders.length > 0) {
          console.log(`Adding missing headers: ${missingHeaders.join(', ')}`);
          
          try {
            // Try to update the headers
            await sheet.setHeaderRow([...existingHeaders, ...missingHeaders]);
          } catch (error) {
            // If there's an error about sheet size, resize the sheet first
            if (error.message && error.message.includes("not large enough")) {
              console.log("Sheet not large enough, resizing it first");
              
              // Get the current sheet properties
              const sheetProperties = sheet.a1SheetId ? await doc.axios.get(
                `https://sheets.googleapis.com/v4/spreadsheets/${doc.spreadsheetId}/sheets/${sheet.a1SheetId}`
              ) : null;
              
              // Calculate needed columns (current plus new ones)
              const currentColumnCount = sheetProperties?.data?.properties?.gridProperties?.columnCount || existingHeaders.length;
              const neededColumnCount = Math.max(currentColumnCount, expectedHeaders.length);
              
              // Resize the sheet if needed
              if (neededColumnCount > currentColumnCount) {
                console.log(`Resizing sheet from ${currentColumnCount} to ${neededColumnCount} columns`);
                
                // Use the Sheets API to resize the grid
                await doc.sheetsApi.spreadsheets.batchUpdate({
                  spreadsheetId: doc.spreadsheetId,
                  requestBody: {
                    requests: [
                      {
                        updateSheetProperties: {
                          properties: {
                            sheetId: sheet.sheetId,
                            gridProperties: {
                              columnCount: neededColumnCount
                            }
                          },
                          fields: 'gridProperties.columnCount'
                        }
                      }
                    ]
                  }
                });
                
                // Retry setting the header row after resize
                await sheet.setHeaderRow([...existingHeaders, ...missingHeaders]);
              }
            } else {
              // If it's another error, rethrow it
              throw error;
            }
          }
          
          // Reload headers after updating
          await sheet.loadHeaderRow();
        }
      } else {
        // Create a new sheet with all expected headers
        console.log(`Creating new sheet: ${sheetName}`);
        sheet = await doc.addSheet({
          title: sheetName,
          headerValues: expectedHeaders
        });
        await sheet.loadHeaderRow();
      }
    } catch (sheetError) {
      console.error('Error setting up sheet:', sheetError);
      
      // If we can't modify the existing sheet, create a new one with a timestamp
      const timestampedSheetName = `${sheetName}_${Date.now()}`;
      console.log(`Creating new timestamped sheet: ${timestampedSheetName}`);
      
      sheet = await doc.addSheet({
        title: timestampedSheetName,
        headerValues: expectedHeaders
      });
      await sheet.loadHeaderRow();
    }
    
    // Process messages for adding to sheet
    console.log('Processing message data for sheet upload');
    const newRows = messages.map(msg => {
      // Process location data
      let locationName = "";
      let locationCoords = "";
      let locationConfidence = "";
      
      if (msg.LOCATIONS && Array.isArray(msg.LOCATIONS) && msg.LOCATIONS.length > 0) {
        const firstLocation = msg.LOCATIONS[0];
        locationName = firstLocation.location || "";
        
        if (firstLocation.latitude !== undefined && firstLocation.longitude !== undefined) {
          locationCoords = `(${firstLocation.latitude}, ${firstLocation.longitude})`;
        }
        
        if (firstLocation.confidence !== undefined) {
          locationConfidence = firstLocation.confidence.toString();
        }
      }
      
      // Process category data
      let parentCategory = "";
      let parentScore = "";
      let childCategory = "";
      let childScore = "";
      
      if (msg.CATEGORIES && Array.isArray(msg.CATEGORIES) && msg.CATEGORIES.length > 0) {
        const categoryData = msg.CATEGORIES[0];
        
        if (categoryData.classification) {
          parentCategory = categoryData.classification.parent_category || "";
          parentScore = categoryData.classification.parent_confidence_score || "";
          childCategory = categoryData.classification.child_category || "";
          childScore = categoryData.classification.child_confidence_score || "";
        }
      }
      
      // Return formatted row
      return {
        id: msg.id || "",
        date: msg.date || "",
        date_unixtime: msg.date_unixtime || "",
        from: msg.from || "",
        text: msg.text ? msg.text.toString().normalize("NFC") : "",
        reply_id: msg.reply_to_message_id || "", 
        LANGUAGE: msg.LANGUAGE || "",
        TRANSLATED_TEXT: msg.TRANSLATED_TEXT || "",
        parent_category: parentCategory,
        parent_confidence_score: parentScore,
        child_category: childCategory,
        child_confidence_score: childScore,
        locations_names: locationName,
        locations_coordinates: locationCoords,
        location_confidence: locationConfidence,
        source_file: msg.source_file || ""
      };
    });
    
    if (newRows.length > 0) {
      console.log(`Adding ${newRows.length} rows to Google Sheet`);
      await sheet.addRows(newRows);
      console.log('Rows added successfully');
    } else {
      console.log('No rows to add to Google Sheet');
    }
    
    return 'Upload successful';
  } catch (error) {
    console.error('Upload error:', error);
    throw new Error(`Failed to upload to Google Sheets: ${error.message}`);
  }
}

// Start the server
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  console.log(`Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log(`Session Secret: ${process.env.SESSION_SECRET ? 'Set' : 'Not set'}`);
  console.log(`Cloud Run URL: ${process.env.CLOUD_RUN_URL || 'Default URL'}`);
});