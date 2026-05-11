/* ─── Helpers ────────────────────────────────────────────────────── */
function isTestMode() {
    return document.getElementById('test-mode-toggle').checked;
}

function toggleTestMode() {
    document.getElementById('mode-display').textContent = isTestMode() ? 'Test' : 'Real';
    const active = document.querySelector('.nav-tab.active');
    if (active && active.id === 'btn-camera') {
        document.getElementById('live-stream').src = '/video_feed?test_mode=' + isTestMode();
    }
}

/* ─── View Switching ─────────────────────────────────────────────── */
function switchMode(mode) {
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.getElementById(`btn-${mode}`).classList.add('active');

    document.querySelectorAll('.view').forEach(v => {
        v.classList.remove('active');
        v.classList.add('hidden');
    });

    const target = document.getElementById(`view-${mode}`);
    target.classList.remove('hidden');
    setTimeout(() => target.classList.add('active'), 10);

    const stream = document.getElementById('live-stream');
    stream.src = mode === 'camera' ? '/video_feed?test_mode=' + isTestMode() : '';

    if (mode !== 'camera') stopStatsPolling();
    else startStatsPolling();
}

/* ─── Live Stats Polling ─────────────────────────────────────────── */
let statsTimer = null;

function startStatsPolling() {
    fetchStats();
    statsTimer = setInterval(fetchStats, 1500);
}

function stopStatsPolling() {
    if (statsTimer) { clearInterval(statsTimer); statsTimer = null; }
}

function fetchStats() {
    fetch('/stats')
        .then(r => r.json())
        .then(renderStats)
        .catch(() => {});
}

function renderStats(data) {
    setText('stat-total',     data.total);
    setText('stat-ok',        data.ok);
    setText('stat-warning',   data.warning);
    setText('stat-violation', data.violation);

    const list = document.getElementById('vehicle-list');
    const footer = document.getElementById('panel-footer');

    if (!data.vehicles || data.vehicles.length === 0) {
        list.innerHTML = `
            <div class="empty-state">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>
                <p>No vehicles detected</p>
            </div>`;
        footer.textContent = '';
        return;
    }

    list.innerHTML = data.vehicles.map(v => {
        const cls = v.status === 'OK' ? 'badge-ok'
                  : v.status === 'WARNING' ? 'badge-warning'
                  : 'badge-violation';
        return `
        <div class="vehicle-row">
            <div>
                <div class="veh-id">Vehicle #${v.id}</div>
                <div class="veh-dur">${v.duration}</div>
            </div>
            <span class="veh-badge ${cls}">${v.status}</span>
        </div>`;
    }).join('');

    footer.textContent = `${data.vehicles.length} vehicle${data.vehicles.length !== 1 ? 's' : ''} tracked`;
}

function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = (val === undefined || val === null) ? '—' : val;
}

/* ─── Drag & Drop ────────────────────────────────────────────────── */
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');

['dragenter', 'dragover', 'dragleave', 'drop'].forEach(ev =>
    dropZone.addEventListener(ev, e => { e.preventDefault(); e.stopPropagation(); })
);

['dragenter', 'dragover'].forEach(ev =>
    dropZone.addEventListener(ev, () => dropZone.classList.add('dragover'))
);

['dragleave', 'drop'].forEach(ev =>
    dropZone.addEventListener(ev, () => dropZone.classList.remove('dragover'))
);

dropZone.addEventListener('drop', e => handleFiles(e.dataTransfer.files));
fileInput.addEventListener('change', function () { handleFiles(this.files); });

/* ─── File Handling ──────────────────────────────────────────────── */
function handleFiles(files) {
    if (!files.length) return;
    if (files[0].type !== 'video/mp4') { alert('Please upload an MP4 file.'); return; }
    uploadFile(files[0]);
}

function uploadFile(file) {
    dropZone.classList.add('hidden');
    document.getElementById('upload-progress').classList.remove('hidden');

    const fd = new FormData();
    fd.append('video', file);
    fd.append('test_mode', isTestMode());

    fetch('/upload', { method: 'POST', body: fd })
        .then(r => r.json())
        .then(data => {
            if (data.error) throw new Error(data.error);
            document.getElementById('upload-progress').classList.add('hidden');
            document.getElementById('result-container').classList.remove('hidden');
            document.getElementById('result-video').src = data.view_url + '?t=' + Date.now();
            document.getElementById('download-btn').href = data.download_url;
        })
        .catch(err => { alert('Upload failed: ' + err.message); resetUpload(); });
}

function resetUpload() {
    dropZone.classList.remove('hidden');
    document.getElementById('upload-progress').classList.add('hidden');
    document.getElementById('result-container').classList.add('hidden');
    fileInput.value = '';
    document.getElementById('result-video').src = '';
}

/* ─── Init ───────────────────────────────────────────────────────── */
startStatsPolling();
