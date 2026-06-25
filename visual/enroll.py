"""
Face enrollment script for SAPMS.

Captures face images from the webcam for a new person, trains (or retrains)
the LBPH face recognizer on all enrolled faces, and registers the person in
the MySQL `persons` table via database.add_person().

Run this once per new person you want attendance.py to recognize.

    python enroll.py

Requires: pip install opencv-contrib-python --break-system-packages
(opencv-contrib-python is needed for cv2.face — plain opencv-python does NOT
include it, so if you get "module 'cv2' has no attribute 'face'", that's why.)
"""

import os
import cv2
import numpy as np

import database

DATASET_DIR = "dataset"
TRAINER_DIR = "trainer"
TRAINER_FILE = os.path.join(TRAINER_DIR, "trainer.yml")
CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
SAMPLES_PER_PERSON = 40


def capture_faces(person_id, person_name):
    os.makedirs(DATASET_DIR, exist_ok=True)
    face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
    cam = cv2.VideoCapture(0)

    if not cam.isOpened():
        print("ERROR: Could not open webcam. Check it isn't already in use by another app.")
        return False

    count = 0
    print(f"Look at the camera. Capturing {SAMPLES_PER_PERSON} samples for {person_name}...")

    while count < SAMPLES_PER_PERSON:
        ok, frame = cam.read()
        if not ok:
            print("ERROR: Failed to read frame from webcam.")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            count += 1
            face_img = gray[y:y + h, x:x + w]
            filename = os.path.join(DATASET_DIR, f"person_{person_id}_{count}.jpg")
            cv2.imwrite(filename, face_img)

            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, f"Sample {count}/{SAMPLES_PER_PERSON}", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        cv2.imshow("Enrolling - press Q to cancel", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cam.release()
    cv2.destroyAllWindows()

    if count < SAMPLES_PER_PERSON:
        print("Enrollment incomplete — not enough samples captured.")
        return False

    print(f"Captured {count} face samples for {person_name}.")
    return True


def train_model():
    """Retrains the LBPH recognizer on every image currently in dataset/."""
    os.makedirs(TRAINER_DIR, exist_ok=True)
    recognizer = cv2.face.LBPHFaceRecognizer_create()

    faces = []
    labels = []

    for filename in os.listdir(DATASET_DIR):
        if not filename.startswith("person_"):
            continue
        # filename format: person_<person_id>_<n>.jpg
        person_id = int(filename.split("_")[1])
        img_path = os.path.join(DATASET_DIR, filename)
        gray_img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if gray_img is None:
            continue
        faces.append(gray_img)
        labels.append(person_id)

    if not faces:
        print("No training data found in dataset/. Enroll at least one person first.")
        return

    recognizer.train(faces, np.array(labels))
    recognizer.save(TRAINER_FILE)
    print(f"Model trained on {len(faces)} images and saved to {TRAINER_FILE}")


def enroll_new_person():
    name = input("Enter full name: ").strip()
    role = input("Enter role (Student/Staff) [Student]: ").strip() or "Student"

    person_id = database.add_person(name, role)
    print(f"Registered '{name}' in MySQL with person_id={person_id}")

    success = capture_faces(person_id, name)
    if success:
        train_model()
        print("Enrollment complete. This person can now be recognized by attendance.py")
    else:
        print("Enrollment failed during face capture. The person is still saved in MySQL; "
              "you can re-run this script to retry capture, or remove them from the "
              "persons table if you want to start over.")


if __name__ == "__main__":
    database.create_tables()
    enroll_new_person()
