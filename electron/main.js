const { ipcRenderer } = require('electron');
let currentInput;
let selectedDatasetItem;

const { ipcRenderer } = require('electron');

document.getElementById('uploadBtn').addEventListener('click', async () => {
    const result = await ipcRenderer.invoke('select-directory');
    document.getElementById('status').innerText = result.success ? 
        `Directory moved to: ${result.path}` : 
        `Error: ${result.error}`;
});

function selectDirectory() {
    // Create a temporary file input element for directory selection
    const input = document.createElement('input');
    input.type = 'file';
    input.webkitdirectory = true;
    input.style.display = 'none'; // Hide the input element
    document.body.appendChild(input);

    // Listen for the file selection
    input.onchange = function () {
        if (input.files.length > 0) {
            const directoryPath = input.files[0].path.split(input.files[0].webkitRelativePath)[0]; // Get the selected directory path
            ipcRenderer.send('copy-directory', directoryPath); // Send directory path to the main process
        }

        handleDirectorySelection(input);
        // Remove the temporary input after selection
        document.body.removeChild(input);
    };

    // Trigger the file input click
    input.click();
}

function handleDirectorySelection(input) {
    console.log("handle test")
    const files = input.files;
    if (files.length > 0) {
        const datasetList = document.getElementById('dataset-list');
        const datasetItem = document.createElement('div');
        datasetItem.className = 'dataset-item';

        // Get the directory name from the path of the first file
        const directoryPath = files[0].webkitRelativePath;
        const directoryName = directoryPath.split('/')[0]; // Extract directory name

        datasetItem.innerHTML = `
                    <!-- From Uiverse.io by risabbir --> 
                    <div class="checkbox-container">
                    <div class="checkbox-wrapper">
                        <input class="checkbox" id="checkbox" type="checkbox" />
                        <label class="checkbox-label" for="checkbox">
                        <div class="checkbox-flip">
                            <div class="checkbox-front">
                            <svg
                                fill="white"
                                height="32"
                                width="32"
                                viewBox="0 0 24 24"
                                xmlns="http://www.w3.org/2000/svg"
                            >
                                <path
                                d="M19 13H12V19H11V13H5V12H11V6H12V12H19V13Z"
                                class="icon-path, front"
                                ></path>
                            </svg>
                            </div>
                            <div class="checkbox-back">
                            <svg
                                fill="white"
                                height="32"
                                width="32"
                                viewBox="0 0 24 24"
                                xmlns="http://www.w3.org/2000/svg"
                            >
                                <path
                                d="M9 19l-7-7 1.41-1.41L9 16.17l11.29-11.3L22 6l-13 13z"
                                class="icon-path, back"
                                ></path>
                            </svg>
                            </div>
                        </div>
                        </label>
                    </div>
                    </div>

                    <span>${directoryName}</span>
                    <button onclick="processFile(this)">Process file</button>
                `;
        datasetItem.addEventListener('contextmenu', function (e) {
            e.preventDefault(); // Prevent the default right-click menu
            showContextMenu(e, datasetItem);
        });

        datasetList.appendChild(datasetItem);

        // copy directory to rawJson directory
        copyDir(input);

    }
}

function showContextMenu(event, datasetItem) {
    selectedDatasetItem = datasetItem;

    const contextMenu = document.getElementById('context-menu');
    contextMenu.style.left = `${event.pageX}px`;
    contextMenu.style.top = `${event.pageY}px`;
    contextMenu.style.display = 'block';

    document.addEventListener('click', closeContextMenu);
}

function closeContextMenu() {
    const contextMenu = document.getElementById('context-menu');
    contextMenu.style.display = 'none';
    document.removeEventListener('click', closeContextMenu);
}

// Remove dataset
document.getElementById('remove-option').addEventListener('click', function () {
    const confirmRemove = confirm("Are you sure you want to remove this dataset?");
    if (confirmRemove) {
        selectedDatasetItem.remove();
    }
    closeContextMenu();
});

// Rename dataset
document.getElementById('rename-option').addEventListener('click', function () {
    const newName = prompt("Enter new name for dataset:", selectedDatasetItem.querySelector('span').textContent);
    if (newName && newName.trim() !== "") {
        selectedDatasetItem.querySelector('span').textContent = newName;
    }
    closeContextMenu();
});

function removeDataset(element) {
    element.parentElement.remove();
}

function processFile(button) {
    const datasetItem = button.parentElement;
    const fileNameSpan = datasetItem.querySelector('.file-name');
    alert(`Processing files in directory: ${fileNameSpan.textContent}`);
    // You can add further logic here to process the directory's contents
}