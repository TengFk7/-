# 🅿️ Parking Monitor — ระบบตรวจจับการจอดรถผิดกฎ

ระบบ Web App ที่ใช้ YOLOv8 ตรวจจับและติดตามรถยนต์แบบ Real-time ผ่านกล้อง หรืออัพโหลดวิดีโอเพื่อวิเคราะห์

---

## ⚙️ ขั้นตอนการติดตั้งและรัน

### 1. Clone โปรเจกต์

```bash
git clone https://github.com/TengFk7/-.git
cd -
```

---

### 2. ติดตั้ง Python

ต้องใช้ **Python 3.9 – 3.11** (แนะนำ 3.10)

ดาวน์โหลดได้ที่ → https://www.python.org/downloads/

> ⚠️ ตอนติดตั้ง Python อย่าลืมติ๊ก **"Add Python to PATH"**

---

### 3. สร้าง Virtual Environment

```bash
python -m venv .venv
```

**เปิดใช้งาน venv:**

- Windows (PowerShell):
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
- Windows (CMD):
  ```cmd
  .venv\Scripts\activate.bat
  ```
- Mac / Linux:
  ```bash
  source .venv/bin/activate
  ```

---

### 4. ติดตั้ง Dependencies

```bash
pip install -r requirements.txt
```

> ⏳ ขั้นตอนนี้อาจใช้เวลาสักครู่ เพราะต้องดาวน์โหลด PyTorch และ Ultralytics

---

### 5. ดาวน์โหลดโมเดล YOLOv8

โปรเจกต์นี้ใช้ **YOLOv8m** (ไฟล์ `.pt` ไม่ได้อยู่ใน Git เพราะขนาดใหญ่เกินไป)

โมเดลจะถูกดาวน์โหลดอัตโนมัติตอนรันครั้งแรก หรือสามารถดาวน์โหลดเองได้ที่:

```bash
python -c "from ultralytics import YOLO; YOLO('yolov8m.pt')"
```

---

### 6. รันแอป

```bash
python app.py
```

เปิดเบราว์เซอร์ไปที่ → **http://127.0.0.1:5000**

---

## 🎮 วิธีใช้งาน

| ฟีเจอร์ | วิธีใช้ |
|---------|---------|
| **Live Camera** | กดปุ่ม "Live Camera" — ใช้กล้อง Webcam ของเครื่อง |
| **Upload Video** | กดปุ่ม "Upload Video" — อัพโหลดไฟล์ `.mp4` เพื่อวิเคราะห์ |
| **Test Mode** | เปิด/ปิดได้บนหน้าเว็บ — ย่อเวลา 10 นาที/15 นาที เป็นวินาที |

---

## 📊 สีของ Bounding Box

| สี | ความหมาย |
|----|----------|
| 🟢 เขียว | OK — จอดไม่เกิน 10 นาที |
| 🟡 เหลือง | WARNING — จอดเกิน 10 นาที |
| 🔴 แดง | VIOLATION — จอดเกิน 15 นาที |

---

## 🛠️ Requirements

- Python 3.9–3.11
- Webcam (สำหรับ Live Camera mode)
- RAM อย่างน้อย 4GB (แนะนำ 8GB+)
- GPU (ถ้ามีจะเร็วขึ้นมาก แต่ CPU ก็รันได้)

---

## 📁 โครงสร้างโปรเจกต์

```
.
├── app.py                    # Flask Web Server หลัก
├── detector.py               # YOLOv8 detection + tracking logic
├── parking_monitor.py        # Parking duration monitoring
├── generate_comparison_graph.py  # สร้างกราฟ performance
├── requirements.txt          # Python dependencies
├── templates/
│   └── index.html            # หน้าเว็บ Dashboard
└── static/
    ├── style.css             # Stylesheet
    └── main.js               # Frontend JavaScript
```
