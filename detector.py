import cv2
import time
import os
import imageio
from ultralytics import YOLO

class ParkingMonitor:
    def __init__(self, model_path='yolov8m.pt', test_mode=True):
        self.model = YOLO(model_path)
        self.vehicle_classes = [2, 3, 5, 7] # car, motorcycle, bus, truck
        self.tracked_vehicles = {}
        self.next_display_id = 1
        self.test_mode = test_mode
        
        if self.test_mode:
            self.TIME_10_MINS = 10
            self.TIME_15_MINS = 15
        else:
            self.TIME_10_MINS = 10 * 60
            self.TIME_15_MINS = 15 * 60

    def process_frame(self, frame, current_time=None):
        if current_time is None:
            current_time = time.time()

        # Run YOLOv8 tracking (optimized for small objects in high-res aerial views)
        results = self.model.track(frame, persist=True, classes=self.vehicle_classes, conf=0.25, imgsz=1280, max_det=1000, tracker="bytetrack.yaml", verbose=False)

        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)
            classes = results[0].boxes.cls.cpu().numpy().astype(int)
            confidences = results[0].boxes.conf.cpu().numpy()

            for box, track_id, cls, conf in zip(boxes, track_ids, classes, confidences):
                x1, y1, x2, y2 = box

                # Update tracking info
                if track_id not in self.tracked_vehicles:
                    self.tracked_vehicles[track_id] = {
                        'first_seen': current_time,
                        'last_seen': current_time,
                        'display_id': self.next_display_id
                    }
                    self.next_display_id += 1
                else:
                    self.tracked_vehicles[track_id]['last_seen'] = current_time

                # Calculate duration parked
                duration = current_time - self.tracked_vehicles[track_id]['first_seen']
                display_id = self.tracked_vehicles[track_id]['display_id']

                # Determine bounding box color
                if duration <= self.TIME_10_MINS:
                    color = (0, 255, 0) # Green
                    status = "OK"
                elif duration <= self.TIME_15_MINS:
                    color = (0, 255, 255) # Yellow
                    status = "WARNING"
                else:
                    color = (0, 0, 255) # Red
                    status = "VIOLATION"

                # Draw bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                # Prepare label text
                mins = int(duration // 60) if not self.test_mode else int(duration)
                secs = int(duration % 60) if not self.test_mode else 0
                
                label = f"ID:{display_id} {mins}m {secs}s [{status}]"
                
                # Draw label background
                font_scale = 1.4
                thickness = 2
                (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
                cv2.rectangle(frame, (x1, y1 - h - 10), (x1 + w, y1), color, -1)
                cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness)

        # Cleanup old tracks
        to_delete = []
        for tid, info in self.tracked_vehicles.items():
            if current_time - info['last_seen'] > 2.0:
                to_delete.append(tid)
        for tid in to_delete:
            del self.tracked_vehicles[tid]



        return frame

def process_video_file(input_path, output_path, monitor):
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise Exception(f"Could not open video {input_path}")
        
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    
    # Use imageio with libx264, yuv420p, and faststart for web streaming
    writer = imageio.get_writer(
        output_path, 
        fps=fps, 
        codec='libx264', 
        quality=5, 
        pixelformat='yuv420p',
        output_params=['-movflags', 'faststart']
    )
    
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        simulated_time = frame_count / fps
        processed_frame = monitor.process_frame(frame, current_time=simulated_time)
        
        # Convert BGR (OpenCV) to RGB (imageio)
        rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
        
        # Resize to 720p to keep file size small and playback fast
        h, w = rgb_frame.shape[:2]
        max_w, max_h = 1280, 720
        scale = min(max_w / w, max_h / h)
        if scale < 1.0:
            new_w, new_h = int(w * scale), int(h * scale)
        else:
            new_w, new_h = w, h
            
        # Ensure dimensions are even numbers (required by libx264)
        new_w = new_w if new_w % 2 == 0 else new_w - 1
        new_h = new_h if new_h % 2 == 0 else new_h - 1
        
        if new_w != w or new_h != h:
            rgb_frame = cv2.resize(rgb_frame, (new_w, new_h))
            
        writer.append_data(rgb_frame)
        
        frame_count += 1
        
    cap.release()
    writer.close()
    return output_path

def generate_video_stream(source=0, test_mode=True):
    cap = cv2.VideoCapture(source)
    monitor = ParkingMonitor(test_mode=test_mode)
    
    # Calculate display size to avoid huge streams
    vid_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    vid_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    
    display_w, display_h = 0, 0
    if vid_w > 0 and vid_h > 0:
        max_w, max_h = 1280, 720
        scale = min(max_w / vid_w, max_h / vid_h)
        if scale < 1.0:
            display_w = int(vid_w * scale)
            display_h = int(vid_h * scale)
            
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        if display_w > 0 and display_h > 0:
            frame = cv2.resize(frame, (display_w, display_h))
            
        processed_frame = monitor.process_frame(frame)
        
        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', processed_frame)
        if not ret:
            continue
            
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    cap.release()
