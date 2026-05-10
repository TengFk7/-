import os
from flask import Flask, render_template, request, Response, jsonify, send_from_directory, url_for
from werkzeug.utils import secure_filename
from detector import generate_video_stream, process_video_file, ParkingMonitor

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['PROCESSED_FOLDER'] = 'processed'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024 # 500MB max size

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    # MJPEG stream
    test_mode = request.args.get('test_mode', 'true') == 'true'
    return Response(generate_video_stream(source=0, test_mode=test_mode),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
        
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file and file.filename.endswith('.mp4'):
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)
        
        output_filename = f"processed_{filename}"
        output_path = os.path.join(app.config['PROCESSED_FOLDER'], output_filename)
        
        try:
            # Process the video synchronously (this might take a while for large videos)
            test_mode = request.form.get('test_mode', 'true') == 'true'
            monitor = ParkingMonitor(test_mode=test_mode)
            process_video_file(input_path, output_path, monitor)
            
            # Return URL to the processed video
            download_url = url_for('download_file', filename=output_filename)
            view_url = url_for('view_file', filename=output_filename)
            return jsonify({'success': True, 'view_url': view_url, 'download_url': download_url})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    return jsonify({'error': 'Invalid file format. Only .mp4 is supported.'}), 400

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename, as_attachment=True)

@app.route('/view/<filename>')
def view_file(filename):
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename, mimetype='video/mp4')

if __name__ == '__main__':
    # Use threaded=True to handle multiple connections, which is required for streaming
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=True)
