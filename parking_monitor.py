import cv2
import time
import argparse
from ultralytics import YOLO

def main():
    parser = argparse.ArgumentParser(description="Temporary Parking Monitor")
    parser.add_argument('--source', type=str, default='3156802-uhd_3840_2160_30fps.mp4', help='Video source (file path or camera index)')
    parser.add_argument('--test', action='store_true', default=True, help='Test mode: 1 second equals 1 minute')
    args = parser.parse_args()

    # Load YOLOv8 model (using medium model for better accuracy instead of nano)
    # The system will automatically download yolov8m.pt if it's not present.
    model = YOLO('yolov8m.pt')

    # COCO classes for vehicles: 2 (car), 3 (motorcycle), 5 (bus), 7 (truck)
    vehicle_classes = [2, 3, 5, 7]

    # Try to use webcam if source is '0'
    source = int(args.source) if args.source.isdigit() else args.source
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print(f"Error: Could not open video source {args.source}")
        return

    # Dictionary to keep track of vehicle presence
    # Format: {track_id: {'first_seen': timestamp, 'last_seen': timestamp, 'display_id': id}}
    tracked_vehicles = {}
    next_display_id = 1

    # Define time thresholds in seconds
    if args.test:
        # In test mode, 1 second = 1 minute
        TIME_10_MINS = 10
        TIME_15_MINS = 15
        print("Running in TEST MODE: 1 real second = 1 simulation minute.")
    else:
        # Normal mode
        TIME_10_MINS = 10 * 60
        TIME_15_MINS = 15 * 60

    print("Starting Parking Monitor...")
    print("Press 'q' to quit.")

    # Calculate a display size that fits on a standard screen while maintaining exact aspect ratio
    vid_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    vid_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    
    display_w, display_h = 0, 0
    if vid_w > 0 and vid_h > 0:
        max_w, max_h = 1280, 720
        scale = min(max_w / vid_w, max_h / vid_h)
        if scale < 1.0: # Only scale down if the video is larger than our max bounds
            display_w = int(vid_w * scale)
            display_h = int(vid_h * scale)
        else:
            display_w = int(vid_w)
            display_h = int(vid_h)

    # Use WINDOW_AUTOSIZE so the window perfectly fits the frame we give it, preventing any squishing
    cv2.namedWindow("Parking Monitor", cv2.WINDOW_AUTOSIZE)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("End of video stream or error reading frame.")
            break

        # Resize the frame itself before any processing or drawing
        if display_w > 0 and display_h > 0 and (int(vid_w) != display_w or int(vid_h) != display_h):
            frame = cv2.resize(frame, (display_w, display_h))

        current_time = time.time()

        # Run YOLOv8 tracking on the frame, persisting tracks between frames
        # conf=0.4 to reduce false positives, tracker="bytetrack.yaml" for better object tracking
        results = model.track(frame, persist=True, classes=vehicle_classes, conf=0.4, tracker="bytetrack.yaml", verbose=False)

        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)
            classes = results[0].boxes.cls.cpu().numpy().astype(int)
            confidences = results[0].boxes.conf.cpu().numpy()

            for box, track_id, cls, conf in zip(boxes, track_ids, classes, confidences):
                x1, y1, x2, y2 = box

                # Update tracking info
                if track_id not in tracked_vehicles:
                    tracked_vehicles[track_id] = {
                        'first_seen': current_time,
                        'last_seen': current_time,
                        'display_id': next_display_id
                    }
                    next_display_id += 1
                else:
                    tracked_vehicles[track_id]['last_seen'] = current_time

                # Calculate duration parked
                duration = current_time - tracked_vehicles[track_id]['first_seen']
                display_id = tracked_vehicles[track_id]['display_id']

                # Determine bounding box color
                if duration <= TIME_10_MINS:
                    color = (0, 255, 0) # Green (BGR)
                    status = "OK"
                elif duration <= TIME_15_MINS:
                    color = (0, 255, 255) # Yellow (BGR)
                    status = "WARNING"
                else:
                    color = (0, 0, 255) # Red (BGR)
                    status = "VIOLATION"

                # Draw bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                # Prepare label text
                mins = int(duration // 60) if not args.test else int(duration)
                secs = int(duration % 60) if not args.test else 0
                
                label = f"ID:{display_id} {mins}m {secs}s [{status}]"
                
                # Draw label background for better readability
                font_scale = 1.0
                thickness = 2
                (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
                cv2.rectangle(frame, (x1, y1 - h - 10), (x1 + w, y1), color, -1)
                cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness)

        # Cleanup old tracks that haven't been seen for 2 seconds (to handle tracking loss)
        to_delete = []
        for tid, info in tracked_vehicles.items():
            if current_time - info['last_seen'] > 2.0:
                to_delete.append(tid)
        
        for tid in to_delete:
            del tracked_vehicles[tid]



        # Show frame
        cv2.imshow("Parking Monitor", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
