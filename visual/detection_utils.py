"""
Helper functions for motion detection and on-screen annotation,
used by attendance_tracker.py.
"""

import cv2
import numpy as np

import config


def prepare_roi(gray_frame, box, size=(100, 100)):
    """Crops a region of interest from a grayscale frame and resizes it
    to a fixed size so two ROIs can always be compared pixel-for-pixel."""
    x1, y1, x2, y2 = box
    x1, y1 = max(0, x1), max(0, y1)
    roi = gray_frame[y1:y2, x1:x2]
    if roi.size == 0:
        return None
    return cv2.resize(roi, size)


def detect_motion(prev_gray_roi, curr_gray_roi):
    """
    Compares two same-size grayscale ROIs and decides whether enough
    pixels changed between them to call it "motion".

    Returns True  -> person is ACTIVE (moved since the previous frame)
            False -> person is IDLE (effectively still)
    """
    if prev_gray_roi is None or curr_gray_roi is None:
        return False

    diff = cv2.absdiff(prev_gray_roi, curr_gray_roi)
    _, thresh = cv2.threshold(diff, config.MOTION_PIXEL_THRESHOLD, 255, cv2.THRESH_BINARY)

    changed_pixels = np.count_nonzero(thresh)
    total_pixels = thresh.size
    ratio = changed_pixels / total_pixels if total_pixels else 0

    return ratio > config.MOTION_AREA_RATIO


def draw_label(frame, box, name, state):
    """Draws a bounding box plus a name + active/idle label above it."""
    x1, y1, x2, y2 = box
    color = (0, 200, 0) if state == "active" else (160, 160, 160)

    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    label = f"{name} - {state.upper()}"
    label_width = max(150, len(label) * 9)
    cv2.rectangle(frame, (x1, max(0, y1 - 25)), (x1 + label_width, y1), color, -1)
    cv2.putText(frame, label, (x1 + 5, max(15, y1 - 7)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)
