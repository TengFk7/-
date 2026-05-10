function isTestMode() {
    return document.getElementById('test-mode-toggle').checked;
}

function toggleTestMode() {
    const currentMode = document.querySelector('.nav-item.active').id.replace('btn-', '');
    if (currentMode === 'camera') {
        const liveStream = document.getElementById('live-stream');
        liveStream.src = '/video_feed?test_mode=' + isTestMode();
    }
}

// View Switching Logic
function switchMode(mode) {
    // Update navigation
    document.querySelectorAll('.nav-item').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`btn-${mode}`).classList.add('active');

    // Update views
    document.querySelectorAll('.view-section').forEach(view => {
        view.classList.remove('active');
        view.classList.add('hidden');
    });
    
    const targetView = document.getElementById(`view-${mode}`);
    targetView.classList.remove('hidden');
    
    // Add small delay for animation
    setTimeout(() => {
        targetView.classList.add('active');
    }, 10);

    // Update title
    document.getElementById('mode-title').textContent = mode === 'camera' ? 'Live Camera Feed' : 'Upload Video for Analysis';

    // Handle stream state
    const liveStream = document.getElementById('live-stream');
    if (mode === 'camera') {
        liveStream.src = '/video_feed?test_mode=' + isTestMode(); // Reconnect stream
    } else {
        liveStream.src = ''; // Disconnect stream to save resources
    }
}

// File Upload Logic
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');

// Drag and drop events
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
});

dropZone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFiles(files);
});

fileInput.addEventListener('change', function() {
    handleFiles(this.files);
});

function handleFiles(files) {
    if (files.length === 0) return;
    
    const file = files[0];
    if (file.type !== 'video/mp4') {
        alert('Please upload an MP4 video file.');
        return;
    }

    uploadFile(file);
}

function uploadFile(file) {
    // Show progress UI
    document.getElementById('drop-zone').classList.add('hidden');
    document.getElementById('upload-progress').classList.remove('hidden');

    const formData = new FormData();
    formData.append('video', file);
    formData.append('test_mode', isTestMode());

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Hide progress, show result
        document.getElementById('upload-progress').classList.add('hidden');
        document.getElementById('result-container').classList.remove('hidden');
        
        // Update video player and download link
        const videoElement = document.getElementById('result-video');
        videoElement.src = data.view_url + '?t=' + new Date().getTime();
        
        const downloadBtn = document.getElementById('download-btn');
        downloadBtn.href = data.download_url;
    })
    .catch(error => {
        alert('Upload failed: ' + error.message);
        resetUpload();
    });
}

function resetUpload() {
    document.getElementById('drop-zone').classList.remove('hidden');
    document.getElementById('upload-progress').classList.add('hidden');
    document.getElementById('result-container').classList.add('hidden');
    document.getElementById('file-input').value = '';
    
    const videoElement = document.getElementById('result-video');
    videoElement.src = '';
}
