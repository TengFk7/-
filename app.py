import os
import json
import time
import threading
from flask import Flask, render_template, request, Response, jsonify, send_from_directory, url_for
from werkzeug.utils import secure_filename
from detector import generate_video_stream, process_video_file, ParkingMonitor

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['PROCESSED_FOLDER'] = 'processed'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

# ── Shared live stats (updated by stream thread) ───────────────────
_live_stats = {
    'total': 0,
    'ok': 0,
    'warning': 0,
    'violation': 0,
    'vehicles': []   # list of {id, duration_s, status}
}
_stats_lock = threading.Lock()

def _make_monitor_with_stats(test_mode=True):
    """Return a ParkingMonitor whose process_frame also pushes stats."""
    monitor = ParkingMonitor(test_mode=test_mode)
    original_pf = monitor.process_frame

    def patched_process_frame(frame, current_time=None):
        if current_time is None:
            current_time = time.time()
        out = original_pf(frame, current_time)

        vehicles = []
        ok = warning = violation = 0
        for tid, info in monitor.tracked_vehicles.items():
            dur = current_time - info['first_seen']
            if dur <= monitor.TIME_10_MINS:
                status = 'OK'; ok += 1
            elif dur <= monitor.TIME_15_MINS:
                status = 'WARNING'; warning += 1
            else:
                status = 'VIOLATION'; violation += 1
            if monitor.test_mode:
                dur_label = f"{int(dur)}m 0s"
            else:
                dur_label = f"{int(dur//60)}m {int(dur%60)}s"
            vehicles.append({
                'id': info['display_id'],
                'duration': dur_label,
                'status': status
            })

        vehicles.sort(key=lambda v: v['id'])

        with _stats_lock:
            _live_stats['total']     = ok + warning + violation
            _live_stats['ok']        = ok
            _live_stats['warning']   = warning
            _live_stats['violation'] = violation
            _live_stats['vehicles']  = vehicles[:20]   # cap list

        return out

    monitor.process_frame = patched_process_frame
    return monitor


# ── Routes ─────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    test_mode = request.args.get('test_mode', 'true') == 'true'
    monitor   = _make_monitor_with_stats(test_mode=test_mode)

    def stream():
        import cv2
        cap = cv2.VideoCapture(0)
        vid_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        vid_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        display_w = display_h = 0
        if vid_w > 0 and vid_h > 0:
            scale = min(1280 / vid_w, 720 / vid_h)
            if scale < 1.0:
                display_w = int(vid_w * scale)
                display_h = int(vid_h * scale)

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if display_w > 0:
                frame = cv2.resize(frame, (display_w, display_h))
            processed = monitor.process_frame(frame)
            ret2, buf = cv2.imencode('.jpg', processed)
            if not ret2:
                continue
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                   + buf.tobytes() + b'\r\n')
        cap.release()

    return Response(stream(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/stats')
def stats():
    with _stats_lock:
        return jsonify(dict(_live_stats))


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and file.filename.endswith('.mp4'):
        filename    = secure_filename(file.filename)
        input_path  = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)
        output_filename = f"processed_{filename}"
        output_path     = os.path.join(app.config['PROCESSED_FOLDER'], output_filename)
        try:
            test_mode = request.form.get('test_mode', 'true') == 'true'
            monitor   = ParkingMonitor(test_mode=test_mode)
            process_video_file(input_path, output_path, monitor)
            return jsonify({
                'success':      True,
                'view_url':     url_for('view_processed', filename=output_filename),
                'download_url': url_for('download_file',  filename=output_filename)
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'Invalid file format. Only .mp4 is supported.'}), 400


@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename, as_attachment=True)


@app.route('/view/<filename>')
def view_processed(filename):
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename, mimetype='video/mp4')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=True)
