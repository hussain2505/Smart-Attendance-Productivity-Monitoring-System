"""
Configuration settings for the Smart Attendance & Productivity Monitoring
System (SAPMS). Edit the values below to match your environment before
running enroll.py, attendance_tracker.py, or dashboard.py.
"""

import os
import cv2

# ---------------- MySQL Database Settings ----------------
# Update these to match your local MySQL setup.
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "YourPassword123!",   # <-- change this
    "database": "sapms_db",
}

# ---------------- Paths ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")     # enrolled face images, one folder per person_id
MODEL_DIR = os.path.join(BASE_DIR, "models")
LBPH_MODEL_PATH = os.path.join(MODEL_DIR, "lbph_trainer.yml")

# OpenCV ships the Haar cascade XML inside its own install folder.
HAAR_CASCADE_PATH = os.path.join(
    os.path.dirname(cv2.__file__), "data", "haarcascade_frontalface_default.xml"
)

# Ultralytics will auto-download this the first time YOLO(...) is called,
# as long as the machine has internet access.
YOLO_MODEL_PATH = "yolov8n.pt"

# ---------------- Detection / Tracking Thresholds ----------------
YOLO_CONFIDENCE_THRESHOLD = 0.5     # minimum confidence to accept a YOLO "person" detection
FACE_RECOGNITION_CONFIDENCE = 70    # LBPH distance threshold -> LOWER value means a stricter match
LOG_INTERVAL_SECONDS = 10           # how often accumulated active/idle time is written to MySQL
ABSENCE_TIMEOUT_SECONDS = 30        # seconds unseen before a person is auto checked-out
MOTION_PIXEL_THRESHOLD = 25         # per-pixel intensity diff to count a pixel as "changed"
MOTION_AREA_RATIO = 0.02            # fraction of ROI pixels that must change to flag "active"
FACE_SAMPLES_TO_CAPTURE = 40        # number of face images captured per person during enrollment

# Make sure required folders exist
os.makedirs(DATASET_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)
