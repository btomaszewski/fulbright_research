const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('api', {
  // Data processing methods
  processJson: (chatDir) => ipcRenderer.invoke('process-json', chatDir),
  processAndUpload: (chatDir) => ipcRenderer.invoke('process-and-upload', chatDir),
  checkResultFile: (dirName) => ipcRenderer.invoke('check-result-file', dirName),
  
  // Directory selection
  selectDirectory: () => ipcRenderer.invoke('select-directory'),
  
  // Event listeners
  onPythonOutput: (callback) => ipcRenderer.on('python-output', (_, message) => callback(message)),
  onPythonError: (callback) => ipcRenderer.on('python-error', (_, message) => callback(message)),
  onLoadDatasets: (callback) => ipcRenderer.on('load-datasets', (_, datasets) => callback(datasets)),
  
  // Credentials management
  showCredentialsForm: () => ipcRenderer.send('show-credentials-form'),
  selectGoogleCredentialsFile: () => ipcRenderer.invoke('select-google-credentials-file'),
  submitCredentials: (credentials) => ipcRenderer.send('submit-credentials', credentials),
  onCredentialsSuccess: (callback) => ipcRenderer.on('credentials-success', (_, message) => callback(message)),
  onCredentialsError: (callback) => ipcRenderer.on('credentials-error', (_, message) => callback(message)),
  
  // System information
  versions: {
    node: () => process.versions.node,
    chrome: () => process.versions.chrome,
    electron: () => process.versions.electron
  }
});