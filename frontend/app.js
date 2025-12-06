/**
 * Loan Eligibility Engine - Frontend Application
 * 
 * Handles CSV file upload using presigned URLs for S3
 */

// Configuration - Update these values after deployment
const CONFIG = {
    // For local testing:
    API_BASE_URL: 'http://localhost:3000',
    // For AWS deployment, use:
    // API_BASE_URL: 'https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/dev',
};

// DOM Elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const removeFile = document.getElementById('removeFile');
const progressContainer = document.getElementById('progressContainer');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const uploadBtn = document.getElementById('uploadBtn');
const statusCard = document.getElementById('statusCard');
const statusIcon = document.getElementById('statusIcon');
const statusTitle = document.getElementById('statusTitle');
const statusDetails = document.getElementById('statusDetails');
const batchIdElement = document.getElementById('batchId');

let selectedFile = null;

// Event Listeners
uploadArea.addEventListener('click', (e) => {
    if (e.target !== removeFile && !removeFile.contains(e.target)) {
        fileInput.click();
    }
});

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileSelect(files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileSelect(e.target.files[0]);
    }
});

removeFile.addEventListener('click', (e) => {
    e.stopPropagation();
    clearFileSelection();
});

uploadBtn.addEventListener('click', uploadFile);

// Functions
function handleFileSelect(file) {
    // Validate file type
    if (!file.name.endsWith('.csv')) {
        showError('Please select a CSV file');
        return;
    }

    // Validate file size (max 50MB)
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
        showError('File size must be less than 50MB');
        return;
    }

    selectedFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    fileInfo.style.display = 'block';
    uploadBtn.disabled = false;
    
    // Hide previous status
    statusCard.style.display = 'none';
}

function clearFileSelection() {
    selectedFile = null;
    fileInput.value = '';
    fileInfo.style.display = 'none';
    uploadBtn.disabled = true;
    progressContainer.style.display = 'none';
    progressFill.style.width = '0%';
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' bytes';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

async function uploadFile() {
    if (!selectedFile) return;

    const btnText = uploadBtn.querySelector('.btn-text');
    const btnLoader = uploadBtn.querySelector('.btn-loader');

    try {
        // Update UI
        uploadBtn.disabled = true;
        btnText.textContent = 'Uploading...';
        btnLoader.style.display = 'inline-block';
        progressContainer.style.display = 'block';
        statusCard.style.display = 'none';

        // Read file content
        updateProgress(10, 'Reading file...');
        const csvContent = await readFileAsText(selectedFile);

        // Upload to local API
        updateProgress(40, 'Processing CSV...');
        const formData = new FormData();
        formData.append('file', selectedFile);

        const response = await fetch(`${CONFIG.API_BASE_URL}/upload-csv`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.error || `HTTP error ${response.status}`);
        }

        const result = await response.json();

        // Step 2: Trigger matching
        updateProgress(70, 'Running matching algorithm...');
        const matchResponse = await fetch(`${CONFIG.API_BASE_URL}/trigger-matching`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ batch_id: result.batch_id })
        });

        const matchResult = await matchResponse.json();

        // Step 3: Show success
        updateProgress(100, 'Complete!');
        
        showSuccess({
            batchId: result.batch_id,
            usersAdded: result.users_added,
            matchesCreated: matchResult.matches_created || 0
        });

    } catch (error) {
        console.error('Upload error:', error);
        showError(error.message || 'Upload failed. Please try again.');
    } finally {
        btnText.textContent = 'Upload & Process';
        btnLoader.style.display = 'none';
        uploadBtn.disabled = false;
    }
}

function readFileAsText(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(new Error('Failed to read file'));
        reader.readAsText(file);
    });
}

async function getPresignedUrl(filename) {
    const url = `${CONFIG.API_BASE_URL}/upload/presigned-url?filename=${encodeURIComponent(filename)}`;
    
    const response = await fetch(url, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.error || `HTTP error ${response.status}`);
    }

    return response.json();
}

async function uploadToS3(presignedUrl, file) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percentComplete = 30 + (e.loaded / e.total) * 60;
                updateProgress(percentComplete, `Uploading... ${Math.round(e.loaded / e.total * 100)}%`);
            }
        });

        xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                resolve();
            } else {
                reject(new Error(`Upload failed with status ${xhr.status}`));
            }
        });

        xhr.addEventListener('error', () => {
            reject(new Error('Network error during upload'));
        });

        xhr.open('PUT', presignedUrl);
        xhr.setRequestHeader('Content-Type', 'text/csv');
        xhr.send(file);
    });
}

function updateProgress(percent, message) {
    progressFill.style.width = `${percent}%`;
    progressText.textContent = message;
}

function showSuccess(data) {
    statusCard.style.display = 'block';
    statusCard.classList.remove('error');
    statusIcon.textContent = '✓';
    statusTitle.textContent = 'Upload Successful!';
    statusDetails.innerHTML = `
        <p>Your file has been uploaded and processed.</p>
        <p><strong>${data.usersAdded}</strong> users added, <strong>${data.matchesCreated}</strong> matches found!</p>
        <p style="margin-top: 10px;">Batch ID: <code>${data.batchId}</code></p>
        <p style="margin-top: 10px;"><a href="${CONFIG.API_BASE_URL}/matches" target="_blank">View Matches →</a></p>
    `;
    
    // Clear file selection after successful upload
    setTimeout(() => {
        clearFileSelection();
    }, 1000);
}

function showError(message) {
    statusCard.style.display = 'block';
    statusCard.classList.add('error');
    statusIcon.textContent = '✕';
    statusTitle.textContent = 'Upload Failed';
    statusDetails.innerHTML = `<p>${message}</p>`;
}

// Initialize
console.log('Loan Eligibility Engine Frontend Loaded');
console.log('API Base URL:', CONFIG.API_BASE_URL);
