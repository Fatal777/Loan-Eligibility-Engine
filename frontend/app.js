/**
 * Loan Eligibility Engine - Frontend Application
 * Handles CSV file upload using presigned URLs for S3
 */

// Configuration
const CONFIG = {
    API_BASE_URL: 'https://c41a2ucawd.execute-api.ap-south-1.amazonaws.com/dev',
};

// DOM Elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const filePreview = document.getElementById('filePreview');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const removeFile = document.getElementById('removeFile');
const progressContainer = document.getElementById('progressContainer');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const progressPercent = document.getElementById('progressPercent');
const uploadBtn = document.getElementById('uploadBtn');
const uploadCard = document.getElementById('uploadCard');
const statusCard = document.getElementById('statusCard');
const statusIcon = document.getElementById('statusIcon');
const statusTitle = document.getElementById('statusTitle');
const statusMessage = document.getElementById('statusMessage');
const statusDetails = document.getElementById('statusDetails');
const uploadAnother = document.getElementById('uploadAnother');
const connectionStatus = document.getElementById('connectionStatus');

let selectedFile = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    checkAPIConnection();
});

function setupEventListeners() {
    // Upload area click
    uploadArea.addEventListener('click', () => fileInput.click());

    // File input change
    fileInput.addEventListener('change', handleFileSelect);

    // Drag and drop
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);

    // Remove file
    removeFile.addEventListener('click', handleRemoveFile);

    // Upload button
    uploadBtn.addEventListener('click', handleUpload);

    // Upload another
    uploadAnother.addEventListener('click', resetUI);
}

// Check API Connection
async function checkAPIConnection() {
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/health`);
        if (response.ok) {
            connectionStatus.innerHTML = '<span class="status-dot"></span><span>System Online</span>';
        } else {
            throw new Error('API not responding');
        }
    } catch (error) {
        connectionStatus.innerHTML = '<span class="status-dot" style="background:#ef4444"></span><span>System Offline</span>';
    }
}

// File Selection
function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) validateAndSetFile(file);
}

function handleDragOver(e) {
    e.preventDefault();
    uploadArea.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) validateAndSetFile(file);
}

function validateAndSetFile(file) {
    // Validate file type
    if (!file.name.endsWith('.csv')) {
        showError('Invalid file type', 'Please select a CSV file.');
        return;
    }

    // Validate file size (50MB max)
    if (file.size > 50 * 1024 * 1024) {
        showError('File too large', 'Maximum file size is 50MB.');
        return;
    }

    selectedFile = file;
    displayFileInfo(file);
}

function displayFileInfo(file) {
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    uploadArea.style.display = 'none';
    filePreview.style.display = 'flex';
    uploadBtn.disabled = false;
}

function handleRemoveFile(e) {
    e.stopPropagation();
    selectedFile = null;
    fileInput.value = '';
    filePreview.style.display = 'none';
    uploadArea.style.display = 'block';
    uploadBtn.disabled = true;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Upload Process
async function handleUpload() {
    if (!selectedFile) return;

    try {
        // Show progress
        filePreview.style.display = 'none';
        progressContainer.style.display = 'block';
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = '<span>Uploading...</span>';

        updateProgress(10, 'Getting upload URL...');

        // Step 1: Get presigned URL
        const presignedResponse = await fetch(
            `${CONFIG.API_BASE_URL}/upload/presigned-url?filename=${encodeURIComponent(selectedFile.name)}`
        );

        if (!presignedResponse.ok) {
            throw new Error('Failed to get upload URL');
        }

        const presignedData = await presignedResponse.json();
        updateProgress(30, 'Uploading to S3...');

        // Step 2: Upload to S3
        const uploadResponse = await fetch(presignedData.presignedUrl, {
            method: 'PUT',
            body: selectedFile,
            headers: {
                'Content-Type': 'text/csv',
            },
        });

        if (!uploadResponse.ok) {
            throw new Error('Failed to upload file to S3');
        }

        updateProgress(70, 'Processing data...');

        // Step 3: Wait for processing
        await new Promise(resolve => setTimeout(resolve, 2000));
        updateProgress(100, 'Complete!');

        // Show success
        setTimeout(() => {
            showSuccess(presignedData);
        }, 500);

    } catch (error) {
        console.error('Upload error:', error);
        showError('Upload Failed', error.message || 'An error occurred during upload.');
    }
}

function updateProgress(percent, text) {
    progressFill.style.width = `${percent}%`;
    progressPercent.textContent = `${percent}%`;
    progressText.textContent = text;
}

// Status Display
function showSuccess(data) {
    uploadCard.style.display = 'none';
    statusCard.style.display = 'block';

    statusIcon.className = 'status-icon success';
    statusIcon.innerHTML = `
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12"/>
        </svg>
    `;

    statusTitle.textContent = 'Upload Successful!';
    statusMessage.textContent = 'Your file has been uploaded and is being processed.';

    statusDetails.innerHTML = `
        <p><strong>File:</strong> ${selectedFile.name}</p>
        <p><strong>Size:</strong> ${formatFileSize(selectedFile.size)}</p>
        <p><strong>Upload ID:</strong> ${data.uploadId || 'N/A'}</p>
        <p><strong>Status:</strong> Processing started</p>
    `;
    statusDetails.style.display = 'block';
}

function showError(title, message) {
    uploadCard.style.display = 'none';
    statusCard.style.display = 'block';

    statusIcon.className = 'status-icon error';
    statusIcon.innerHTML = `
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
        </svg>
    `;

    statusTitle.textContent = title;
    statusMessage.textContent = message;
    statusDetails.style.display = 'none';
}

function resetUI() {
    selectedFile = null;
    fileInput.value = '';
    
    // Reset upload card
    uploadCard.style.display = 'block';
    uploadArea.style.display = 'block';
    filePreview.style.display = 'none';
    progressContainer.style.display = 'none';
    uploadBtn.disabled = true;
    uploadBtn.innerHTML = `
        <span>Upload & Process</span>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="5" y1="12" x2="19" y2="12"/>
            <polyline points="12 5 19 12 12 19"/>
        </svg>
    `;

    // Reset progress
    progressFill.style.width = '0%';
    progressPercent.textContent = '0%';
    progressText.textContent = 'Uploading...';

    // Hide status card
    statusCard.style.display = 'none';
}
