const { app, BrowserWindow, dialog, ipcMain, Menu } = require('electron');
const path = require('path');
const fs = require('fs');

const userDataPath = app.getPath('userData');
const rawJsonPath = path.join(userDataPath, 'processing/rawJson');
const procJsonPath = path.join(userDataPath, 'processing/processedJson');

let mainWindow;

app.whenReady().then(() => {
    mainWindow = new BrowserWindow({
        width: 1000,
        height: 700,
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
