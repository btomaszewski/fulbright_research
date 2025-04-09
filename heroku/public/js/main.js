document.addEventListener('DOMContentLoaded', function() {
    // Configuration - get Cloud Run URL from data attribute
    const CLOUD_RUN_URL = document.body.dataset.cloudRunUrl || 
                          'https://processjson-1061451118144.us-central1.run.app';
    
    // Status message display functions
    function showStatus(message, type = 'info') {
        const statusContainer = document.getElementById('statusMessages');
        if (!statusContainer) return;
        
        const statusElement = document.createElement('div');
        statusElement.className = `status-message ${type}`;
        statusElement.textContent = message;
        
        statusContainer.appendChild(statusElement);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            statusElement.classList.add('fade-out');
            setTimeout(() => statusElement.remove(), 500);
        }, 5000);
    }
    
    // UPLOAD FORM FUNCTIONALITY
    
    // Toggle upload form visibility
    const addNewButton = document.getElementById('addNew');
    if (addNewButton) {
        addNewButton.addEventListener('click', function() {
            const uploadForm = document.getElementById('upload-form');
            if (uploadForm) {
                const isVisible = uploadForm.style.display !== 'none';
                uploadForm.style.display = isVisible ? 'none' : 'block';
            }
        });
    }
    
    // Handle directory input change
    const directoryInput = document.getElementById('directoryInput');
    if (directoryInput) {
        directoryInput.addEventListener('change', function(e) {
            const files = Array.from(e.target.files);
            const fileCount = document.getElementById('fileCount');
            const fileList = document.getElementById('fileList');
            
            if (fileCount && fileList) {
                fileCount.textContent = files.length;
                fileList.innerHTML = '';
                
                // Display only first 10 files to avoid overwhelming the UI
                const displayFiles = files.slice(0, 10);
                let hasJsonFiles = false;
                
                displayFiles.forEach(file => {
                    const fileItem = document.createElement('div');
                    fileItem.className = 'file-item';
                    
                    // Create file type badge
                    const fileTypeBadge = document.createElement('span');
                    fileTypeBadge.className = 'file-type-badge';
                    
                    // Check file type and apply appropriate styling
                    if (file.name.toLowerCase().endsWith('.json')) {
                        fileTypeBadge.textContent = 'JSON';
                        fileTypeBadge.classList.add('file-type-json');
                        fileItem.classList.add('json-file');
                        hasJsonFiles = true;
                    } else if (file.name.toLowerCase().endsWith('.csv')) {
                        fileTypeBadge.textContent = 'CSV';
                        fileTypeBadge.classList.add('file-type-csv');
                    } else {
                        const ext = file.name.split('.').pop() || 'file';
                        fileTypeBadge.textContent = ext.toUpperCase();
                        fileTypeBadge.classList.add('file-type-other');
                    }
                    
                    fileItem.appendChild(fileTypeBadge);
                    fileItem.appendChild(document.createTextNode(file.name));
                    fileList.appendChild(fileItem);
                });
                
                // If there are more files, show an indicator
                if (files.length > 10) {
                    const moreFiles = document.createElement('div');
                    moreFiles.className = 'file-item';
                    moreFiles.textContent = `... and ${files.length - 10} more files`;
                    fileList.appendChild(moreFiles);
                }
                
                // Show warning if no JSON files are found
                if (!hasJsonFiles && files.length > 0) {
                    showStatus('Warning: No JSON files detected in the selected directory. At least one JSON file is required.', 'warning');
                }
            }
        });
    }
    
    // Handle directory upload form submission
    const uploadForm = document.getElementById('directory-upload-form');
    if (uploadForm) {
        uploadForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const directoryName = document.getElementById('directoryName').value.trim();
            if (!directoryName) {
                showStatus('Please enter a directory name', 'error');
                return;
            }
            
            const directoryInput = document.getElementById('directoryInput');
            if (!directoryInput || directoryInput.files.length === 0) {
                showStatus('Please select a directory', 'error');
                return;
            }
            
            const files = Array.from(directoryInput.files);
            
            // Check if there's at least one JSON file
            const hasJsonFile = files.some(file => file.name.toLowerCase().endsWith('.json'));
            if (!hasJsonFile) {
                showStatus('At least one JSON file is required in the directory', 'error');
                return;
            }
            
            // Display processing status
            showStatus('Uploading and processing directory...', 'info');
            
            // Create FormData and append directory name and files
            const formData = new FormData();
            formData.append('directoryName', directoryName);
            
            // Add all files to the formData
            files.forEach(file => {
                // Include relative path information for server-side reconstruction
                const relativePath = file.webkitRelativePath || file.name;
                formData.append('files', file);
                formData.append('filePaths', relativePath);
            });
            
            try {
                // Update button state
                const submitButton = this.querySelector('button[type="submit"]');
                const originalButtonText = submitButton.querySelector('.front').innerHTML;
                submitButton.disabled = true;
                submitButton.querySelector('.front').innerHTML = `
                    <div class="loader">
                        <div class="loaderB" style="animation-play-state: running;"></div>
                        <div class="loaderA" style="animation-play-state: running;"></div>
                    </div>
                `;
                
                // Send request
                const response = await fetch('/upload-directory', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.message || 'Server error');
                }
                
                const result = await response.json();
                
                // Reset button
                submitButton.disabled = false;
                
                if (result.success) {
                    submitButton.querySelector('.front').innerHTML = `
                        <div class="loader">
                            <span id="check"><i class="fa-solid fa-check"></i></span>
                        </div>
                    `;
                    showStatus(`Success: ${result.message}`, 'success');
                    
                    // Add to dataset list
                    addDatasetToList(directoryName, files.length, result.processResult);
                    
                    // Clear form
                    document.getElementById('directoryName').value = '';
                    document.getElementById('directoryInput').value = '';
                    document.getElementById('fileCount').textContent = '0';
                    document.getElementById('fileList').innerHTML = '';
                    
                    // Update processed count
                    const processedCount = document.getElementById('processed-count');
                    if (processedCount) {
                        const currentCount = parseInt(processedCount.textContent) || 0;
                        processedCount.textContent = currentCount + 1;
                    }
                    
                    // Hide upload form
                    document.getElementById('upload-form').style.display = 'none';
                    
                    // Refresh Tableau dashboard if available
                    if (typeof window.refreshDashboard === 'function') {
                        setTimeout(() => {
                            window.refreshDashboard();
                        }, 1000); // Give a little delay to allow Google Sheets to update
                    }
                } else {
                    submitButton.querySelector('.front').innerHTML = originalButtonText;
                    showStatus(`Error: ${result.message}`, 'error');
                }
            } catch (error) {
                console.error('Upload error:', error);
                showStatus(`Upload failed: ${error.message}`, 'error');
                
                // Reset button
                const submitButton = this.querySelector('button[type="submit"]');
                submitButton.disabled = false;
                submitButton.querySelector('.front').innerHTML = originalButtonText;
            }
        });
    }
    
    function addDatasetToList(dirName, fileCount, processInfo) {
        const ul = document.getElementById('datasetList');
        if (!ul) return;
        
        const li = document.createElement('li');
        li.className = 'dataset-item';
        
        // Add dataset name
        const datasetName = document.createElement('span');
        datasetName.textContent = `${dirName} (${fileCount} files)`;
        datasetName.className = 'dataset-name';
        
        // Add tooltip with processing info
        datasetName.title = processInfo || 'Processed successfully';
        
        // Add status indicator 
        const statusIndicator = document.createElement('span');
        statusIndicator.className = 'status-indicator success';
        statusIndicator.innerHTML = '<i class="fas fa-check-circle"></i> Processed';
        
        li.appendChild(statusIndicator);
        li.appendChild(datasetName);
        ul.appendChild(li);
    }
    
    // ANALYSIS MODAL FUNCTIONALITY
    
    // Modal elements
    const modal = document.getElementById('analysisModal');
    const openModalBtn = document.getElementById('openAnalysisModal');
    const closeModalBtn = document.querySelector('.close-modal');
    
    // Analysis elements
    const promptSelect = document.getElementById('prompt-select');
    const queryForm = document.getElementById('query-form');
    const queryInput = document.getElementById('query-input');
    const queryLoading = document.getElementById('query-loading');
    const responsePanel = document.getElementById('response-panel');
    const responseContent = document.getElementById('response-content');
    const generateSummaryBtn = document.getElementById('generate-summary');
    const summaryLoading = document.getElementById('summary-loading');
    const summaryOutput = document.getElementById('summary-output');
    
    // Modal open/close functionality
    if (openModalBtn && modal) {
        openModalBtn.addEventListener('click', function() {
            modal.style.display = 'block';
            // Initialize analysis when modal opens
            fetchPrompts();
        });
        
        // Close modal when X is clicked
        if (closeModalBtn) {
            closeModalBtn.addEventListener('click', function() {
                modal.style.display = 'none';
            });
        }
        
        // Close modal when clicking outside of it
        window.addEventListener('click', function(event) {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });
    }
    
    // Fetch prompts from API
    async function fetchPrompts() {
        try {
            // Only fetch if the select exists and hasn't been populated yet
            if (!promptSelect || promptSelect.options.length > 1) return;
            
            const response = await fetch(`${CLOUD_RUN_URL}/get-prompts`);
            if (!response.ok) {
                throw new Error('Failed to fetch prompts');
            }
            
            const data = await response.json();
            
            if (data.success && data.prompts) {
                // Clear any existing options except the first one
                while (promptSelect.options.length > 1) {
                    promptSelect.remove(1);
                }
                
                // Add new options
                data.prompts.forEach(prompt => {
                    const option = document.createElement('option');
                    option.value = prompt.id;
                    option.textContent = prompt.name;
                    promptSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error fetching prompts:', error);
            showStatus('Failed to load prompts. Please try again later.', 'error');
        }
    }
    
    // Handle prompt selection
    if (promptSelect) {
        promptSelect.addEventListener('change', async function() {
            if (this.value) {
                try {
                    const response = await fetch(`${CLOUD_RUN_URL}/get-prompt/${this.value}`);
                    if (!response.ok) {
                        throw new Error('Failed to fetch prompt text');
                    }
                    
                    const data = await response.json();
                    if (data.success && data.text) {
                        queryInput.value = data.text;
                    }
                } catch (error) {
                    console.error('Error fetching prompt text:', error);
                    showStatus('Failed to load prompt text', 'error');
                }
            }
        });
    }
    
    // Handle ask form submission
    if (queryForm) {
        queryForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const userInput = queryInput.value.trim();
            if (!userInput) {
                showStatus('Please enter a question', 'error');
                return;
            }
            
            // Show loading, hide results
            queryLoading.style.display = 'block';
            responsePanel.style.display = 'none';
            
            try {
                const response = await fetch(`${CLOUD_RUN_URL}/ask`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        user_input: userInput
                    })
                });
                
                if (!response.ok) {
                    throw new Error('Failed to get analysis');
                }
                
                const data = await response.json();
                
                // Hide loading
                queryLoading.style.display = 'none';
                
                if (data.success && data.response) {
                    // Show response panel with results
                    responseContent.textContent = data.response;
                    responsePanel.style.display = 'block';
                } else {
                    showStatus(data.error || 'Failed to analyze data', 'error');
                }
            } catch (error) {
                console.error('Analysis error:', error);
                queryLoading.style.display = 'none';
                showStatus('Error analyzing data. Please try again.', 'error');
            }
        });
    }
    
    // Handle summary generation
    if (generateSummaryBtn) {
        generateSummaryBtn.addEventListener('click', async function() {
            // Show loading, hide results
            summaryLoading.style.display = 'block';
            summaryOutput.style.display = 'none';
            
            try {
                const response = await fetch(`${CLOUD_RUN_URL}/generate-summary`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        query: "Generate a comprehensive summary of this Telegram data"
                    })
                });
                
                if (!response.ok) {
                    throw new Error('Failed to generate summary');
                }
                
                const data = await response.json();
                
                // Hide loading
                summaryLoading.style.display = 'none';
                
                if (data.success && data.summary) {
                    // Show summary with results
                    summaryOutput.textContent = data.summary;
                    summaryOutput.style.display = 'block';
                } else {
                    showStatus(data.error || 'Failed to generate summary', 'error');
                }
            } catch (error) {
                console.error('Summary error:', error);
                summaryLoading.style.display = 'none';
                showStatus('Error generating summary. Please try again.', 'error');
            }
        });
    }
});