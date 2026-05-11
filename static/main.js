/* ─── Helpers ────────────────────────────────────────────────────── */
function isTestMode() {
    return document.getElementById('test-mode-toggle').checked;
}

function toggleTestMode() {
    // ปิด popup เก่าและ reset UI
    closeAlertModal();

    const testMode = isTestMode();
    const modeText = testMode ? 'Test' : 'Real';
    document.getElementById('mode-display').textContent = modeText;
    const upMode = document.getElementById('up-mode-display');
    if (upMode) upMode.textContent = modeText;

    // อัปเดต mode บน server โดยไม่ restart กล้อง
    fetch('/set_test_mode?test_mode=' + testMode).catch(() => {});
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
        .then(data => {
            // Show modal popup when new alerts arrive
            if (data.alerts && data.alerts.length > 0) {
                showAlertModal(data);
            }
            renderStats(data);
        })
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
            const rc = document.getElementById('result-container');
            rc.classList.remove('hidden');
            document.getElementById('result-video').src = data.view_url + '?t=' + Date.now();
            document.getElementById('download-btn').href = data.download_url;

            // Show bottom action bar
            const bar = document.getElementById('upload-bottom-bar');
            if (bar) bar.style.display = 'flex';

            // Populate upload stats if backend returns them
            if (data.stats) {
                setText('up-stat-total',     data.stats.total);
                setText('up-stat-ok',        data.stats.ok);
                setText('up-stat-warning',   data.stats.warning);
                setText('up-stat-violation', data.stats.violation);
                renderUploadVehicleList(data.stats.vehicles);
            }
        })
        .catch(err => { alert('Upload failed: ' + err.message); resetUpload(); });
}

function resetUpload() {
    dropZone.classList.remove('hidden');
    document.getElementById('upload-progress').classList.add('hidden');
    document.getElementById('result-container').classList.add('hidden');
    const bar = document.getElementById('upload-bottom-bar');
    if (bar) bar.style.display = 'none';
    fileInput.value = '';
    document.getElementById('result-video').src = '';
    // Reset upload stats
    ['up-stat-total','up-stat-ok','up-stat-warning','up-stat-violation'].forEach(id => setText(id, '—'));
    const ul = document.getElementById('up-vehicle-list');
    if (ul) ul.innerHTML = `
        <div class="empty-state">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>
            <p>No results yet</p>
            <p style="font-size:11px;color:var(--muted-2)">Upload a video to start</p>
        </div>`;
    const footer = document.getElementById('up-panel-footer');
    if (footer) footer.textContent = '';
}

function renderUploadVehicleList(vehicles) {
    const list = document.getElementById('up-vehicle-list');
    const footer = document.getElementById('up-panel-footer');
    if (!list) return;

    if (!vehicles || vehicles.length === 0) {
        list.innerHTML = `
            <div class="empty-state">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>
                <p>No vehicles found</p>
            </div>`;
        if (footer) footer.textContent = '';
        return;
    }

    list.innerHTML = vehicles.map(v => {
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

    if (footer) footer.textContent = `${vehicles.length} vehicle${vehicles.length !== 1 ? 's' : ''} tracked`;
}

/* ─── Alert Modal Popup ──────────────────────────────────────────────── */
function showAlertModal(data) {
    // ปิด modal เก่าทันที (ไม่มี animation) แล้วเปิดใหม่
    const existing = document.getElementById('alert-modal');
    if (existing) existing.remove();

    const violations = (data.vehicles || []).filter(v => v.status === 'VIOLATION');
    const warnings   = (data.vehicles || []).filter(v => v.status === 'WARNING');

    // Determine severity for header style
    const hasViolation = violations.length > 0;
    const headerClass  = hasViolation ? 'modal-header-violation' : 'modal-header-warning';
    const headerIcon   = hasViolation
        ? `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`
        : `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
    const headerTitle  = hasViolation ? 'Parking Violation Detected!' : 'Parking Warning';
    const headerSub    = hasViolation
        ? 'The following vehicles have exceeded the maximum parking time.'
        : 'The following vehicles are approaching the parking time limit.';

    function vehicleRows(list, cls, label) {
        if (!list.length) return '';
        return `
        <div class="modal-section">
            <div class="modal-section-label modal-label-${cls}">
                <span class="modal-label-dot"></span>${label} (${list.length})
            </div>
            <div class="modal-vehicle-list">
                ${list.map(v => `
                <div class="modal-vehicle-row modal-row-${cls}">
                    <div class="modal-veh-info">
                        <span class="modal-veh-id">Vehicle #${v.id}</span>
                        <span class="modal-veh-dur">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                            ${v.duration}
                        </span>
                    </div>
                    <span class="modal-veh-badge modal-badge-${cls}">${v.status}</span>
                </div>`).join('')}
            </div>
        </div>`;
    }

    const modal = document.createElement('div');
    modal.id = 'alert-modal';
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal-box" role="dialog" aria-modal="true" aria-labelledby="modal-title">
            <div class="modal-header ${headerClass}">
                <span class="modal-header-icon">${headerIcon}</span>
                <div>
                    <div class="modal-title" id="modal-title">${headerTitle}</div>
                    <div class="modal-subtitle">${headerSub}</div>
                </div>
                <button class="modal-close-btn" onclick="closeAlertModal()" aria-label="Close">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
            </div>

            <div class="modal-body">
                ${vehicleRows(violations, 'violation', 'VIOLATION')}
                ${vehicleRows(warnings, 'warning', 'WARNING')}
            </div>

            <div class="modal-footer">
                <span class="modal-time">Updated just now</span>
                <button class="modal-dismiss-btn" onclick="closeAlertModal()">Dismiss</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Animate in
    requestAnimationFrame(() => modal.classList.add('modal-visible'));

    // Close on backdrop click
    modal.addEventListener('click', e => { if (e.target === modal) closeAlertModal(); });
}

function closeAlertModal() {
    const modal = document.getElementById('alert-modal');
    if (!modal) return;
    modal.classList.remove('modal-visible');
    modal.addEventListener('transitionend', () => modal.remove(), { once: true });
}

/* ─── Init ──────────────────────────────────────────────────────────── */
startStatsPolling();
