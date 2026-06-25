# SAPMS — Smart Attendance & Productivity Monitoring System

A final-year project that uses **YOLOv8** for human detection, **OpenCV motion
detection** for activity tracking, **LBPH face recognition** for identity,
**MySQL** for storage, and a **Streamlit dashboard** for analytics.

## How it works

```
 Webcam
   │
   ▼
 YOLOv8 ── detects every "person" bounding box in the frame
   │
   ▼
 Haar Cascade + LBPH ── finds the face inside the box and matches it
   │                     against enrolled people
   ▼
 Motion Detector ── compares this frame's region to the last one to
   │                 decide ACTIVE vs IDLE
   ▼
 MySQL ── stores check-in/out times (attendance) and active/idle
   │       seconds in 10-second buckets (activity_logs)
   ▼
 Streamlit Dashboard ── reads MySQL and shows attendance tables,
                         productivity %, and timelines
```

## Project files

| File | Purpose |
|---|---|
| `config.py` | All settings: MySQL credentials, file paths, detection thresholds |
| `database.py` | MySQL table creation + every read/write query |
| `enroll.py` | Registers a new person: captures face photos, trains the recognizer |
| `detection_utils.py` | Motion-detection math and on-screen drawing helpers |
| `attendance_tracker.py` | Main loop: runs YOLO + recognition + motion detection live |
| `dashboard.py` | Streamlit app for viewing results |
| `requirements.txt` | Python dependencies |

## Setup (Windows, Python 3.10.11, 64-bit)

1. **Install the Visual C++ Redistributable** (required by OpenCV/PyTorch):
   https://aka.ms/vs/17/release/vc_redist.x64.exe

2. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```
   The first time `attendance_tracker.py` runs, `ultralytics` will
   auto-download the `yolov8n.pt` weights file (needs internet access once).

3. **Set up MySQL:**
   - Make sure your local MySQL server is running.
   - Open `config.py` and set your MySQL `user` and `password` in
     `DB_CONFIG`. You don't need to create the database or tables manually —
     every script calls `database.create_tables()` on startup, which creates
     the `sapms_db` database and all three tables automatically.

## Running the project

Run these in order, each in its own terminal:

1. **Enroll every person who should be recognized:**
   ```
   python enroll.py
   ```
   Enter their name and role, then look at the camera while it captures
   ~40 face samples. Repeat once per person. Each run retrains the model
   on everyone enrolled so far.

2. **Start live tracking:**
   ```
   python attendance_tracker.py
   ```
   A window opens showing the webcam feed with bounding boxes labeled
   `Name - ACTIVE` (green) or `Name - IDLE` (gray). Unrecognized people
   show as `Unknown` in red. Press `q` to stop.

   Behavior:
   - First time a known person is seen today → automatic check-in.
   - Every 10 seconds → that person's active/idle seconds are saved to MySQL.
   - If unseen for 30+ seconds → automatic check-out.

3. **View the dashboard:**
   ```
   streamlit run dashboard.py
   ```
   Opens in your browser. Shows attendance for the selected date,
   productivity % per person, a per-person activity timeline, and a
   7-day attendance trend.

## Tuning

All thresholds live in `config.py`:

- `YOLO_CONFIDENCE_THRESHOLD` — raise if YOLO is detecting false positives.
- `FACE_RECOGNITION_CONFIDENCE` — lower = stricter identity matching
  (fewer false matches, but more "Unknown" results).
- `LOG_INTERVAL_SECONDS` — how often activity is saved to MySQL.
- `ABSENCE_TIMEOUT_SECONDS` — how long someone can be out of frame before
  being auto checked-out (e.g. a short walk to the printer shouldn't
  trigger a checkout — raise this if needed).
- `MOTION_AREA_RATIO` — higher = a person must move more before being
  counted as "active". Lower this if small movements like typing aren't
  being picked up.

## Possible extensions (good viva talking points)

- Swap LBPH for a deep-learning face embedding model (e.g. FaceNet) for
  more robust recognition under varied lighting.
- Add a per-person "idle alert" if someone is idle for too long.
- Export daily/weekly reports to Excel or PDF straight from the dashboard.
- Add multi-camera support for larger rooms.
- Deploy the dashboard with a login screen for admin-only access.
