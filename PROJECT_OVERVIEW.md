# 🅿️ ParkMonitor — ระบบตรวจจับการจอดรถอัจฉริยะ

> เอกสารอธิบายระบบทั้งหมดของโปรเจค Smart Parking Monitor ด้วย YOLOv8 + Flask

---

## 📋 สารบัญ

1. [ภาพรวมระบบ](#-ภาพรวมระบบ)
2. [โครงสร้างไฟล์](#-โครงสร้างไฟล์)
3. [Tech Stack](#-tech-stack)
4. [การทำงานของระบบ](#-การทำงานของระบบ)
5. [ไฟล์หลักและหน้าที่](#-ไฟล์หลักและหน้าที่)
6. [API Endpoints](#-api-endpoints)
7. [โหมดการทำงาน (Test Mode / Real Mode)](#-โหมดการทำงาน)
8. [ระบบ Tracking และ Status](#-ระบบ-tracking-และ-status)
9. [Frontend UI](#-frontend-ui)
10. [สคริปต์เสริม (Analysis Tools)](#-สคริปต์เสริม)
11. [วิธีรันโปรเจค](#-วิธีรันโปรเจค)
12. [Dependencies](#-dependencies)

---

## 🌐 ภาพรวมระบบ

**ParkMonitor** คือเว็บแอปพลิเคชันสำหรับตรวจจับและติดตามยานพาหนะในพื้นที่จอดรถ แบบ Real-time โดยใช้ AI Model **YOLOv8** ผ่าน Browser

### ความสามารถหลัก
- ✅ ตรวจจับยานพาหนะแบบ Real-time จากกล้อง Webcam
- ✅ อัปโหลดไฟล์วิดีโอ `.mp4` เพื่อวิเคราะห์
- ✅ ติดตาม ID ของยานพาหนะแต่ละคัน (ByteTrack)
- ✅ คำนวณระยะเวลาจอดรถ และแสดงสถานะ OK / WARNING / VIOLATION
- ✅ Dashboard แสดงสถิติแบบ Live ผ่าน API polling
- ✅ ดาวน์โหลดวิดีโอที่ผ่านการประมวลผลแล้ว

---

## 📁 โครงสร้างไฟล์

```
Project จอด/
│
├── app.py                          # Flask web server (entry point)
├── detector.py                     # ParkingMonitor class + video processing
├── parking_monitor.py              # Standalone CLI version (ไม่ใช้ Flask)
├── generate_comparison_graph.py    # สร้างกราฟเปรียบเทียบ 2 วิดีโอ
├── requirements.txt                # Python dependencies
├── yolov8m.pt                      # YOLOv8 Medium model weights (~52 MB)
├── yolov8n.pt                      # YOLOv8 Nano model weights (~6.5 MB)
├── yolo26n.pt                      # Custom trained model weights (~5.5 MB)
│
├── templates/
│   └── index.html                  # หน้าเว็บหลัก (Jinja2 template)
│
├── static/
│   ├── style.css                   # CSS ทั้งหมด (Vanilla CSS, design system)
│   └── main.js                     # JavaScript ทั้งหมด (fetch API, UI logic)
│
├── uploads/                        # วิดีโอที่ผู้ใช้อัปโหลด
│   ├── 3156802-uhd_3840_2160_30fps.mp4
│   ├── 4062994-uhd_3840_2160_30fps.mp4
│   ├── 9010418-uhd_3840_2160_30fps.mp4
│   └── all train/                  # สคริปต์และข้อมูลสำหรับ Training Analysis
│       ├── generate_comparison_training_graph.py
│       ├── generate_performance_graph.py
│       ├── plot_training_graph.py
│       ├── detection_performance.csv
│       ├── vid1_data.csv
│       ├── vid2_data.csv
│       ├── dummy_results.csv
│       └── performance_graph.png
│
├── processed/                      # วิดีโอที่ผ่าน AI processing แล้ว (auto-generated)
├── runs/                           # YOLOv8 training output (Roboflow training)
│   └── roboflow_training/
│
├── comparison_training_graph.png   # กราฟเปรียบเทียบ 2 วิดีโอ (output)
└── training_accuracy_graph.png     # กราฟ training accuracy (output)
```

---

## 🛠 Tech Stack

| ชั้น | เทคโนโลยี | หน้าที่ |
|------|-----------|---------|
| **Backend** | Flask 3.0.0 | Web server, routing, API |
| **AI / CV** | Ultralytics YOLOv8 | Object detection + tracking |
| **Video** | OpenCV (`cv2`) | อ่าน/เขียน/ประมวลผล frame |
| **Video Export** | imageio + imageio-ffmpeg | Export วิดีโอ web-compatible (H.264) |
| **Frontend** | HTML5 + Vanilla CSS + Vanilla JS | UI Dashboard |
| **Font** | Inter (Google Fonts) | Typography |
| **Tracker** | ByteTrack (built-in YOLO) | Multi-object tracking |
| **Graphing** | Matplotlib + NumPy | สร้างกราฟ performance |
| **Data** | Pandas | อ่าน CSV สำหรับ analysis |

---

## ⚙️ การทำงานของระบบ

### Flow หลัก (Live Camera)

```
Browser → GET /video_feed
    → Flask stream()
        → cv2.VideoCapture(0)  [เปิด Webcam]
        → loop: cap.read() → frame
            → monitor.process_frame(frame)
                → YOLO model.track()  [detect + track vehicles]
                → อัปเดต tracked_vehicles dict
                → คำนวณ duration + status
                → วาด bounding box + label บน frame
                → อัปเดต _live_stats (thread-safe)
            → cv2.imencode('.jpg') → JPEG bytes
            → yield multipart MJPEG stream
    → Browser แสดง <img src="/video_feed">

Browser → GET /stats (ทุก 1.5 วินาที)
    → Flask คืน JSON จาก _live_stats
    → JS renderStats() → อัปเดต Dashboard
```

### Flow อัปโหลดวิดีโอ

```
Browser → POST /upload (FormData: video file)
    → Flask บันทึกไฟล์ใน uploads/
    → process_video_file(input_path, output_path, monitor)
        → cv2.VideoCapture(input_path)
        → imageio.get_writer() [H.264, yuv420p, faststart]
        → loop: frame → monitor.process_frame(frame, simulated_time)
            → simulated_time = frame_count / fps  [เวลาจาก frame ไม่ใช่ wall clock]
        → resize ให้ ≤ 1280×720 (even dimensions สำหรับ libx264)
        → บันทึกผล → processed/processed_<filename>.mp4
    → คืน JSON { view_url, download_url }
```

---

## 📄 ไฟล์หลักและหน้าที่

### `app.py` — Flask Web Server

| ส่วน | หน้าที่ |
|------|---------|
| `_live_stats` | Dict กลางที่เก็บสถิติล่าสุด (total, ok, warning, violation, vehicles list) |
| `_stats_lock` | `threading.Lock()` ป้องกัน race condition |
| `_make_monitor_with_stats()` | สร้าง ParkingMonitor แบบ monkey-patch ให้ push stats ทุก frame |
| Routes | `/`, `/video_feed`, `/stats`, `/upload`, `/download/<filename>`, `/view/<filename>` |

**จุดสำคัญ:** `_make_monitor_with_stats()` ใช้เทคนิค wrapping `process_frame` เพื่อดักจับข้อมูลสถิติโดยไม่แก้ไข `detector.py` โดยตรง

---

### `detector.py` — Core Detection Engine

#### Class `ParkingMonitor`

```python
ParkingMonitor(model_path='yolov8m.pt', test_mode=True)
```

| Attribute | ค่า | ความหมาย |
|-----------|-----|----------|
| `vehicle_classes` | `[2, 3, 5, 7]` | COCO class IDs: car, motorcycle, bus, truck |
| `tracked_vehicles` | `dict` | `{track_id: {first_seen, last_seen, display_id}}` |
| `TIME_10_MINS` | 10 (test) / 600 (real) | เกณฑ์ WARNING (วินาที) |
| `TIME_15_MINS` | 15 (test) / 900 (real) | เกณฑ์ VIOLATION (วินาที) |

**YOLO Config ใน `process_frame()`:**
- `conf=0.25` — Confidence threshold
- `imgsz=1280` — Input resolution ให้ YOLO
- `max_det=1000` — จำนวน detection สูงสุดต่อ frame
- `tracker="bytetrack.yaml"` — ใช้ ByteTrack algorithm
- `persist=True` — รักษา track ID ข้ามเฟรม

**Cleanup Logic:** ลบ track ที่ไม่เจอมากกว่า 2 วินาที (`last_seen > 2.0s`)

#### Functions

| Function | หน้าที่ |
|----------|---------|
| `process_video_file(input, output, monitor)` | ประมวลผลวิดีโอทั้งไฟล์ ใช้ `simulated_time = frame_count/fps` |
| `generate_video_stream(source, test_mode)` | Generator สำหรับ MJPEG stream (legacy, ไม่ถูกใช้ใน app.py ปัจจุบัน) |

---

### `parking_monitor.py` — CLI Standalone Version

รันโดยตรงโดยไม่ต้องใช้ Flask:
```bash
python parking_monitor.py --source 3156802-uhd_3840_2160_30fps.mp4 --test
```

- เปิดหน้าต่าง OpenCV แสดงผลแบบ real-time
- กด `q` เพื่อออก
- ใช้ `conf=0.4` (สูงกว่า detector.py เล็กน้อย)

---

## 🔌 API Endpoints

| Method | Route | หน้าที่ | Response |
|--------|-------|---------|---------|
| `GET` | `/` | แสดงหน้าเว็บ Dashboard | HTML |
| `GET` | `/video_feed` | MJPEG stream จาก Webcam | `multipart/x-mixed-replace` |
| `GET` | `/video_feed?test_mode=false` | Stream ด้วย Real Mode | MJPEG |
| `GET` | `/stats` | ดึงสถิติปัจจุบัน | JSON |
| `POST` | `/upload` | อัปโหลดและประมวลผลวิดีโอ | JSON |
| `GET` | `/view/<filename>` | ดูวิดีโอที่ประมวลผลแล้ว | `video/mp4` |
| `GET` | `/download/<filename>` | ดาวน์โหลดวิดีโอ | attachment |

### ตัวอย่าง `/stats` Response

```json
{
  "total": 5,
  "ok": 3,
  "warning": 1,
  "violation": 1,
  "vehicles": [
    { "id": 1, "duration": "3m 0s", "status": "OK" },
    { "id": 2, "duration": "12m 0s", "status": "WARNING" },
    { "id": 3, "duration": "18m 0s", "status": "VIOLATION" }
  ]
}
```

---

## 🔄 โหมดการทำงาน

### Test Mode (Default: เปิด)
- 1 วินาทีจริง = 1 นาทีจำลอง
- เวลา WARNING เริ่มที่ **10 วินาที** (แทน 10 นาที)
- เวลา VIOLATION เริ่มที่ **15 วินาที** (แทน 15 นาที)
- เหมาะสำหรับ Demo และทดสอบ

### Real Mode (ปิด Test Mode)
- ใช้เวลาจริง
- WARNING: จอดนาน **10 นาที** ขึ้นไป
- VIOLATION: จอดนาน **15 นาที** ขึ้นไป
- เหมาะสำหรับ Production

Toggle ได้จากปุ่มในหน้าเว็บ (ด้านขวาบนของ navbar)

---

## 🚦 ระบบ Tracking และ Status

### สถานะยานพาหนะ

| สถานะ | สี | เงื่อนไข |
|-------|-----|---------|
| **OK** | 🟢 Green `(0,255,0)` | จอดไม่เกิน 10 นาที |
| **WARNING** | 🟡 Yellow `(0,255,255)` | จอด 10–15 นาที |
| **VIOLATION** | 🔴 Red `(0,0,255)` | จอดเกิน 15 นาที |

### Display Label Format
```
ID:3 12m 0s [WARNING]
```

### Track Lifecycle
```
ตรวจพบ vehicle ครั้งแรก → สร้าง entry ใน tracked_vehicles
    → ทุก frame ที่ยังเห็น → อัปเดต last_seen
    → ไม่เห็นนาน > 2 วินาที → ลบออกจาก dict
```

---

## 🖥 Frontend UI

### Layout หลัก (Camera Mode)

```
┌─────────────────────────────────────────────────┐
│  🅿 ParkMonitor   [Live Camera] [Upload Video]   │
│                           [AI Engine ●] [Test ▪] │
├─────────────────────────────────────────────────┤
│  Total: 5  │  OK: 3  │  Warning: 1  │  Violation: 1 │
├────────────┬────────────────────────┬────────────┤
│ Detection  │                        │ Detected   │
│ Legend     │   📷 Live Video Feed   │ Vehicles   │
│            │      (MJPEG Stream)    │            │
│ Settings   │      ● LIVE            │ #1 OK      │
│ Model info │                        │ #2 WARNING │
└────────────┴────────────────────────┴────────────┘
```

### ไฟล์ Frontend

| ไฟล์ | หน้าที่ |
|------|---------|
| `templates/index.html` | โครงสร้าง HTML, 2 views (camera / upload) |
| `static/style.css` | Design system ด้วย CSS Variables, 642 บรรทัด |
| `static/main.js` | Logic ทั้งหมด: switching, polling, upload, drag&drop |

### CSS Design Tokens (`:root`)

```css
--accent:    #7c3aed;   /* Violet primary */
--green:     #16a34a;   /* OK status */
--yellow:    #d97706;   /* WARNING status */
--red:       #dc2626;   /* VIOLATION status */
--bg:        #f4f4f6;   /* Page background */
--surface:   #ffffff;   /* Card/panel background */
```

### JavaScript Functions หลัก

| Function | หน้าที่ |
|----------|---------|
| `switchMode(mode)` | สลับระหว่าง camera / upload view |
| `startStatsPolling()` | เริ่ม polling `/stats` ทุก 1.5 วินาที |
| `fetchStats()` | fetch `/stats` แล้ว render |
| `renderStats(data)` | อัปเดต stat cards + vehicle list |
| `uploadFile(file)` | POST ไฟล์ไป `/upload` แบบ async |
| `toggleTestMode()` | สลับโหมดและ reload stream |
| `resetUpload()` | คืน upload view กลับสู่สถานะเริ่มต้น |

---

## 📊 สคริปต์เสริม

### `generate_comparison_graph.py`

สร้างกราฟเปรียบเทียบ performance ของ 2 วิดีโอ แบบ YOLOv8 training chart

```bash
python generate_comparison_graph.py
```

**Input:**
- Video A (Train): `3156802-uhd_3840_2160_30fps.mp4`
- Video B (Val): `uploads/4062994-uhd_3840_2160_30fps.mp4`

**Process:**
1. Sample 50 frames จากแต่ละวิดีโอ (evenly-spaced)
2. Run YOLO detection บน frame ที่ sample
3. คำนวณ: vehicle count, mean confidence, synthetic box-loss
4. Smooth ด้วย moving average (window=3)
5. Plot 2-panel dark-theme chart

**Output:** `comparison_training_graph.png`

| Panel | X-axis | Y-axis |
|-------|--------|--------|
| Left | Epoch (1–50) | Box Loss |
| Right | Epoch (1–50) | mAP (Accuracy 0–1) |

### `uploads/all train/` — Training Analysis Tools

| ไฟล์ | หน้าที่ |
|------|---------|
| `generate_performance_graph.py` | สร้างกราฟ performance จาก detection CSV |
| `generate_comparison_training_graph.py` | เปรียบเทียบ training จาก 2 วิดีโอ |
| `plot_training_graph.py` | Plot จาก dummy/results CSV |
| `detection_performance.csv` | ข้อมูล detection performance |
| `vid1_data.csv` / `vid2_data.csv` | ข้อมูล per-frame จากวิดีโอ 2 ไฟล์ |

---

## 🚀 วิธีรันโปรเจค

### 1. ติดตั้ง Dependencies

```bash
pip install -r requirements.txt
```

### 2. รัน Web App

```bash
python app.py
```

เปิด Browser ไปที่: **http://localhost:5000**

### 3. รัน CLI Version (ไม่ต้องใช้ Browser)

```bash
# Test mode (default)
python parking_monitor.py

# ระบุ source วิดีโอ
python parking_monitor.py --source uploads/4062994-uhd_3840_2160_30fps.mp4

# Real mode (เวลาจริง)
python parking_monitor.py --source 0  # 0 = webcam
```

### 4. สร้างกราฟเปรียบเทียบ

```bash
python generate_comparison_graph.py
```

---

## 📦 Dependencies

```
Flask==3.0.0          # Web framework
ultralytics           # YOLOv8 (detection + tracking)
opencv-python         # Computer vision
werkzeug              # File upload utilities
imageio               # Video export
imageio-ffmpeg        # FFmpeg backend สำหรับ H.264
pandas                # CSV reading
matplotlib            # Graph plotting
```

### Model Weights

| ไฟล์ | ขนาด | ใช้ใน |
|------|------|-------|
| `yolov8m.pt` | ~52 MB | หลัก: ใช้ใน `detector.py` และ `app.py` |
| `yolov8n.pt` | ~6.5 MB | Nano model (สำรอง/ทดสอบ) |
| `yolo26n.pt` | ~5.5 MB | Custom trained model (Roboflow) |

---

## 🔧 Configuration สำคัญ

| Parameter | ค่า | ไฟล์ | หมายเหตุ |
|-----------|-----|------|---------|
| Port | `5000` | `app.py` | Flask port |
| Max upload | `500 MB` | `app.py` | `MAX_CONTENT_LENGTH` |
| YOLO conf | `0.25` | `detector.py` | Detection threshold |
| YOLO imgsz | `1280` | `detector.py` | Input image size |
| Stream FPS | Webcam default | `app.py` | ขึ้นกับ hardware |
| Video resize | ≤ 1280×720 | `detector.py` | สำหรับ stream + export |
| Stats poll | 1500 ms | `main.js` | Interval ดึง `/stats` |
| Vehicle list cap | 20 | `app.py` | แสดง max 20 คัน |
| Track timeout | 2.0 วินาที | `detector.py` | ลบ track ที่หายไป |

---

## 📝 หมายเหตุสำคัญ

> **Test Mode vs Real Mode:** เมื่อประมวลผลไฟล์วิดีโอ (upload mode) ระบบใช้ `simulated_time = frame_count / fps` ไม่ใช่เวลาจริง ทำให้ duration ถูกต้องตามเวลาในวิดีโอ

> **Thread Safety:** `_live_stats` dict ถูก protect ด้วย `threading.Lock()` เพราะ stream thread และ stats route อาจ access พร้อมกัน

> **Video Export:** ใช้ `imageio` แทน `cv2.VideoWriter` เพราะ OpenCV บน Windows มักมีปัญหา H.264 codec ที่ browser เปิดไม่ได้ imageio+ffmpeg ผลิต `faststart` mp4 ที่ stream ได้ทันที

> **YOLO Model:** ใช้ `yolov8m` (medium) เพื่อ balance ระหว่าง accuracy และ speed สำหรับกล้อง aerial view

---

*อัปเดตล่าสุด: 2026-05-12 | โปรเจคนี้พัฒนาด้วย Python + Flask + YOLOv8*
