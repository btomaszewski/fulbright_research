const { contextBridge } = require('electron')

contextBridge.exposeInMainWorld('versions', {
  node: () => process.versions.node,
  chrome: () => process.versions.chrome,
  electron: () => process.versions.electron
  // we can also expose variables, not just functions
})

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electron', {
  // Expose methods for the environment setup window
  credentials: {
    submit: (credentials) => ipcRenderer.send('submit-credentials', credentials),
    selectFile: () => ipcRenderer.send('select-credentials-file'),
    onFileSelected: (callback) => ipcRenderer.on('selected-credentials-file', (_, path) => callback(path))
  }
});
