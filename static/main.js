/* ─── Helpers ───────────────────────────────────────────────────── */
function isTestMode() {
    return document.getElementById('test-mode-toggle').checked;
}

function toggleTestMode() {
    const active = document.querySelector('.tab.active');
    if (active && active.id === 'btn-camera') {
        document.getElementById('live-stream').src = '/video_feed?test_mode=' + isTestMode();
    }
}

/* ─── View Switching ────────────────────────────────────────────── */
function switchMode(mode) {
    // Tabs
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.getElementById(`btn-${mode}`).classList.add('active');

    // Views
    document.querySelectorAll('.view').forEach(v => {
        v.classList.remove('active');
        v.classList.add('hidden');
    });

    const target = document.getElementById(`view-${mode}`);
    target.classList.remove('hidden');
    setTimeout(() => target.classList.add('active'), 10);

    // Stream management
    const stream = document.getElementById('live-stream');
    stream.src = mode === 'camera' ? '/video_feed?test_mode=' + isTestMode() : '';
}

/* ─── Drag & Drop ───────────────────────────────────────────────── */
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');

['dragenter', 'dragover', 'dragleave', 'drop'].forEach(ev => {
    dropZone.addEventListener(ev, e => { e.preventDefault(); e.stopPropagation(); });
});

['dragenter', 'dragover'].forEach(ev =>
    dropZone.addEventListener(ev, () => dropZone.classList.add('dragover'))
);

['dragleave', 'drop'].forEach(ev =>
    dropZone.addEventListener(ev, () => dropZone.classList.remove('dragover'))
);

dropZone.addEventListener('drop', e => handleFiles(e.dataTransfer.files));
fileInput.addEventListener('change', function () { handleFiles(this.files); });

/* ─── File Handling ─────────────────────────────────────────────── */
function handleFiles(files) {
    if (!files.length) return;
    const file = files[0];
    if (file.type !== 'video/mp4') {
        alert('Please upload an MP4 video file.');
        return;
    }
    uploadFile(file);
}

function uploadFile(file) {
    dropZone.classList.add('hidden');
    document.getElementById('upload-progress').classList.remove('hidden');

    const formData = new FormData();
    formData.append('video', file);
    formData.append('test_mode', isTestMode());

    fetch('/upload', { method: 'POST', body: formData })
        .then(r => r.json())
        .then(data => {
            if (data.error) throw new Error(data.error);

            document.getElementById('upload-progress').classList.add('hidden');
            document.getElementById('result-container').classList.remove('hidden');

            document.getElementById('result-video').src = data.view_url + '?t=' + Date.now();
            document.getElementById('download-btn').href = data.download_url;
        })
        .catch(err => {
            alert('Upload failed: ' + err.message);
            resetUpload();
        });
}

function resetUpload() {
    dropZone.classList.remove('hidden');
    document.getElementById('upload-progress').classList.add('hidden');
    document.getElementById('result-container').classList.add('hidden');
    fileInput.value = '';
    document.getElementById('result-video').src = '';
}
