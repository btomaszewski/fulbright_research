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

            const submitButton = this.querySelector('button[type="submit"]');
            const originalButtonText = submitButton.querySelector('.front').innerHTML;
            
            try {
                // Update button state
                submitButton.disabled = true;
                submitButton.querySelector('.front').innerHTML = `
                    <div class="loader">
                        <div class="loaderB" style="animation-play-state: running;"></div>
                        <div class="loaderA" style="animation-play-state: running;"></div>
                    </div>
                `;
                
                // Send request
                const response = await fetch('upload-directory', {
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
    // const promptSelect = document.getElementById('prompt-select');
    const queryForm = document.getElementById('query-form');
    const queryInput = document.getElementById('query-input');
    const queryLoading = document.getElementById('query-loading');
    const responsePanel = document.getElementById('response-panel');
    const responseContent = document.getElementById('response-content');
    const generateSummaryBtn = document.getElementById('generate-summary');
    const summaryLoading = document.getElementById('summary-loading');
    const summaryOutput = document.getElementById('summary-output');
    const exportSummaryBtn = document.getElementById('export-summary');
    
    // Modal open/close functionality
    if (openModalBtn && modal) {
        openModalBtn.addEventListener('click', function() {
            modal.style.display = 'block';
            exportSummaryBtn.style.display = 'none';
            // Initialize analysis when modal opens
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

    document.getElementById('question-form').addEventListener('submit', async function (event) {
        event.preventDefault();

        const userInput = document.querySelector('input[name="user_input"]').value;
        if (!userInput.trim()) return; // Prevent empty messages

        // Append user message to chat
        appendMessage('user', userInput);

        const response = await fetch(`${CLOUD_RUN_URL}/ask`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_input: userInput
            })
        });

        const aiResponse = await response.text();

        // Append AI message to chat
        appendMessage('ai', aiResponse);

        document.getElementById('question-form').reset();
    });

    // Function to append messages to chat
    function appendMessage(role, text) {
        const chatBox = document.getElementById('chat-box');
        const messageDiv = document.createElement('div');

        messageDiv.classList.add('message', role);
        messageDiv.innerHTML = `<strong>${role === 'user' ? 'You' : 'AI'}</strong>: ${formatMessage(text)}`;

        chatBox.appendChild(messageDiv);
        chatBox.scrollTop = chatBox.scrollHeight; // Auto-scroll to the latest message
    }

    // Function to format AI chat responses
    function formatMessage(text) {
        try {
            const parsed = JSON.parse(text);
            let response = parsed.response || '';

            // Remove all instances of ***
            response = response.replace(/\*{3,}/g, '');
            response = response.replace(/\*{2,}/g, '');
    
            // Convert newlines to <br> for HTML display
            response = response.replace(/\n/g, '<br>');
    
            return `<div class="ai-response">${response}</div>`;
        } catch (e) {
            console.error('Invalid message format:', e);
            // Fallback: just return raw text with safe formatting
            return `<div class="ai-response">${text.replace(/\n/g, '<br>')}</div>`;
        }
    }
    

    // To be used in summary export, updated when returned by generateSummaryBtn handler
    let summaryText = "";
    
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
                    exportSummaryBtn.style.display = 'block';

                    // Set summaryText to be used in exportSummaryBtn handler
                    summaryText = data.summary;
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

    // Handle summary export
    if (exportSummaryBtn) {
        exportSummaryBtn.addEventListener('click', async function () {
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF();

            // Set font styles
            doc.setFont("helvetica", "normal");
            doc.setFontSize(12);

            // Replace <br> with new lines and manually apply bold styling
            summaryText = String(summaryText);
            summaryText = summaryText
                .replace(/<br>/g, "\n") // Convert <br> to new lines
                .replace(/<strong>(.*?)<\/strong>/g, "**$1**"); // Simulate bold text for PDF

            const pageWidth = doc.internal.pageSize.getWidth();
            const pageHeight = doc.internal.pageSize.getHeight();
            const margin = 10;
            const maxWidth = pageWidth - margin * 2;
            const lineHeight = 7; // Line height for each wrapped line
            let y = 20; // Start y position

            let lines = summaryText.split("\n");

            lines.forEach(line => {
                if (line.startsWith("**")) {
                    doc.setFont("helvetica", "bold");
                    line = line.replace(/\*\*/g, ""); // Remove bold markers
                } else {
                    doc.setFont("helvetica", "normal");
                }

                let wrappedText = doc.splitTextToSize(line, maxWidth);

                // Check if text will exceed the page height
                if (y + wrappedText.length * lineHeight > pageHeight - margin) {
                    doc.addPage(); // Add a new page
                    y = margin; // Reset y position for new page
                }

                doc.text(wrappedText, margin, y);
                y += wrappedText.length * lineHeight;
            });
            // Save the PDF
            doc.save("summaryReport.pdf");
        })
    }
});