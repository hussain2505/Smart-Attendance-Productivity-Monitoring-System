"""
Webcam-based attendance script for SAPMS.

Loads the trained LBPH model, opens the webcam, detects and recognizes
faces, and marks check-in / check-out times in MySQL via database.py.
Recognized people appear with a green box and name; unrecognized faces
appear in red as "Unknown".

Run this during attendance hours; press Q in the video window to stop.
Anyone still "checked in" when you quit gets automatically checked out.

    python attendance.py

Requires: pip install opencv-contrib-python --break-system-packages
You must run enroll.py at least once before this will recognize anyone.
"""

import os
import time

import cv2

import database

TRAINER_FILE = os.path.join("trainer", "trainer.yml")
CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"

# LBPH outputs a "distance" score, not a confidence percentage — LOWER means
# a closer match. Start around 70; lower it (e.g. 50) if strangers are being
# misidentified as known people, raise it if known people show as "Unknown".
CONFIDENCE_THRESHOLD = 70

# Don't spam check-ins for the same person every frame — only re-attempt
# after this many seconds (default 30 min).
RECHECK_COOLDOWN = 30 * 60


def load_recognizer():
    if not os.path.exists(TRAINER_FILE):
        print("ERROR: No trained model found at trainer/trainer.yml.")
        print("Run enroll.py first to register at least one person.")
        return None
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(TRAINER_FILE)
    return recognizer


def run_attendance():
    recognizer = load_recognizer()
    if recognizer is None:
        return

    face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
    cam = cv2.VideoCapture(0)

    if not cam.isOpened():
        print("ERROR: Could not open webcam. Check it isn't already in use by another app.")
        return

    last_checked_in = {}     # person_id -> timestamp of last successful check-in
    active_attendance = {}   # person_id -> attendance_id, so we can check out on exit

    print("Attendance running. Press Q in the video window to stop.")

    while True:
        ok, frame = cam.read()
        if not ok:
            print("ERROR: Failed to read frame from webcam.")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            face_img = gray[y:y + h, x:x + w]
            person_id, confidence = recognizer.predict(face_img)

            if confidence < CONFIDENCE_THRESHOLD:
                name = database.get_person_name(person_id)
                color = (0, 255, 0)
                label = f"{name} ({confidence:.0f})"

                now = time.time()
                last_time = last_checked_in.get(person_id, 0)
                if now - last_time > RECHECK_COOLDOWN:
                    attendance_id = database.check_in(person_id)
                    active_attendance[person_id] = attendance_id
                    last_checked_in[person_id] = now
                    print(f"Checked in: {name} (attendance_id={attendance_id})")
            else:
                color = (0, 0, 255)
                label = "Unknown"

            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(frame, label, (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        cv2.imshow("SAPMS Attendance - press Q to quit", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Auto check-out everyone still active when the session ends.
    for person_id, attendance_id in active_attendance.items():
        database.check_out(attendance_id)
        print(f"Checked out person_id={person_id}")

    cam.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    run_attendance()
