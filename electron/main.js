const { app, BrowserWindow, dialog, ipcMain, Menu } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');


const userDataPath = app.getPath('userData');
const rawJsonPath = path.join(userDataPath, 'processing/rawJson');
const procJsonPath = path.join(userDataPath, 'processing/processedJson');

let mainWindow;

app.whenReady().then(() => {
    const { screen } = require('electron');  // Get screen dimensions
    const primaryDisplay = screen.getPrimaryDisplay();
    const { width, height } = primaryDisplay.workAreaSize;
    
    mainWindow = new BrowserWindow({
        width: width,
        height: height,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false,
        }
    });
    mainWindow.loadFile('index.html');
    createAppDirectories();

    mainWindow.webContents.once('did-finish-load', () => {
        const datasets = fs.readdirSync(rawJsonPath).map(dir => path.join(rawJsonPath, dir));
        mainWindow.webContents.send('load-datasets', datasets);
    });
});

const createAppDirectories = () => {
    if (!fs.existsSync(rawJsonPath)) {
        fs.mkdirSync(rawJsonPath, { recursive: true });
        console.log(`Created directory: ${rawJsonPath}`);
    }
    if (!fs.existsSync(procJsonPath)) {
      fs.mkdirSync(procJsonPath, { recursive: true });
      console.log(`Created directory: ${procJsonPath}`);
  }
};

// Context menu for renaming and deleting
ipcMain.on('show-context-menu', (event, datasetPath, datasetName) => {
    const template = [
        {
            label: 'Delete',
            click: () => {
                dialog.showMessageBox(mainWindow, {
                    type: 'warning',
                    buttons: ['Cancel', 'Delete'],
                    defaultId: 1,
                    title: 'Delete Dataset',
                    message: `Are you sure you want to delete ${datasetName}? This action cannot be undone.`,
                }).then(({ response }) => {
                    if (response === 1) {
                        fs.rmSync(datasetPath, { recursive: true, force: true });
                        mainWindow.webContents.send('delete-dataset', datasetPath);
                    }
                });
            }
        }
    ];

    const menu = Menu.buildFromTemplate(template);
    menu.popup({ window: mainWindow });
});

ipcMain.handle('select-directory', async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openDirectory']
    });
    if (result.filePaths.length > 0) {
        const selectedDir = result.filePaths[0];
        const targetDir = path.join(rawJsonPath, path.basename(selectedDir));

        try {
            fs.cpSync(selectedDir, targetDir, { recursive: true });
            return targetDir;
        } catch (error) {
            console.error('Error copying directory:', error);
            return null;
        }
    }
    return null;
});

pythonScriptPath = './assets/processJson.py'

// Handle processing datasets with processJson.py
ipcMain.handle('process-json', async () => {
    return new Promise((resolve, reject) => {
        const pythonProcess = spawn('python', [pythonScriptPath, rawJsonPath, procJsonPath]);

        let output = "";
        let errorOutput = "";

        pythonProcess.stdout.on('data', (data) => {
            output += data.toString();
        });

        pythonProcess.stderr.on('data', (data) => {
            errorOutput += data.toString();
        });

        pythonProcess.on('close', (code) => {
            if (code === 0) {
                resolve(output.trim());
            } else {
                reject(errorOutput.trim());
            }
        });
    });
});
