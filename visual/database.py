"""
Database access layer for SAPMS.

Handles MySQL connections, table creation, and every CRUD operation used by
the attendance tracker, the enrollment script, and the Streamlit dashboard.
All other modules should go through this file rather than writing raw SQL
themselves.
"""

from datetime import datetime, date

import mysql.connector

import config


def get_connection():
    """Opens a fresh MySQL connection using the credentials in config.py"""
    return mysql.connector.connect(**config.DB_CONFIG)


def create_database_if_missing():
    """Connects without selecting a database and creates it if needed."""
    cfg = config.DB_CONFIG.copy()
    db_name = cfg.pop("database")
    conn = mysql.connector.connect(**cfg)
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
    conn.commit()
    cursor.close()
    conn.close()


def create_tables():
    """Creates all required tables if they do not already exist."""
    create_database_if_missing()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS persons (
            person_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            role VARCHAR(50) DEFAULT 'Student',
            registered_on DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            attendance_id INT AUTO_INCREMENT PRIMARY KEY,
            person_id INT NOT NULL,
            session_date DATE NOT NULL,
            check_in_time DATETIME NOT NULL,
            check_out_time DATETIME NULL,
            FOREIGN KEY (person_id) REFERENCES persons(person_id),
            UNIQUE KEY unique_person_day (person_id, session_date)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            log_id INT AUTO_INCREMENT PRIMARY KEY,
            attendance_id INT NOT NULL,
            person_id INT NOT NULL,
            log_time DATETIME NOT NULL,
            state VARCHAR(10) NOT NULL,
            duration_seconds INT NOT NULL,
            FOREIGN KEY (attendance_id) REFERENCES attendance(attendance_id),
            FOREIGN KEY (person_id) REFERENCES persons(person_id)
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()


# ---------------- Person management ----------------

def add_person(name, role="Student"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO persons (name, role) VALUES (%s, %s)", (name, role))
    conn.commit()
    person_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return person_id


def get_all_persons():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM persons ORDER BY name")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def get_person_name(person_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM persons WHERE person_id = %s", (person_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else "Unknown"


# ---------------- Attendance ----------------

def get_open_attendance(person_id):
    """Returns today's attendance row for person_id, if one already exists."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM attendance WHERE person_id = %s AND session_date = %s",
        (person_id, date.today()),
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row


def check_in(person_id):
    """Creates today's attendance row if it doesn't exist yet. Returns attendance_id."""
    existing = get_open_attendance(person_id)
    if existing:
        return existing["attendance_id"]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO attendance (person_id, session_date, check_in_time) VALUES (%s, %s, %s)",
        (person_id, date.today(), datetime.now()),
    )
    conn.commit()
    attendance_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return attendance_id


def check_out(attendance_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE attendance SET check_out_time = %s WHERE attendance_id = %s",
        (datetime.now(), attendance_id),
    )
    conn.commit()
    cursor.close()
    conn.close()


def log_activity(attendance_id, person_id, state, duration_seconds):
    if duration_seconds <= 0:
        return
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO activity_logs (attendance_id, person_id, log_time, state, duration_seconds)
           VALUES (%s, %s, %s, %s, %s)""",
        (attendance_id, person_id, datetime.now(), state, duration_seconds),
    )
    conn.commit()
    cursor.close()
    conn.close()


# ---------------- Dashboard queries ----------------

def get_attendance_for_date(target_date):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT a.attendance_id, p.name, p.role, a.check_in_time, a.check_out_time
           FROM attendance a JOIN persons p ON a.person_id = p.person_id
           WHERE a.session_date = %s
           ORDER BY a.check_in_time""",
        (target_date,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def get_productivity_for_date(target_date):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT p.name,
                  SUM(CASE WHEN l.state = 'active' THEN l.duration_seconds ELSE 0 END) AS active_seconds,
                  SUM(CASE WHEN l.state = 'idle' THEN l.duration_seconds ELSE 0 END) AS idle_seconds
           FROM activity_logs l
           JOIN persons p ON l.person_id = p.person_id
           JOIN attendance a ON l.attendance_id = a.attendance_id
           WHERE a.session_date = %s
           GROUP BY p.name""",
        (target_date,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def get_activity_timeline(person_id, target_date):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT l.log_time, l.state, l.duration_seconds
           FROM activity_logs l
           JOIN attendance a ON l.attendance_id = a.attendance_id
           WHERE l.person_id = %s AND a.session_date = %s
           ORDER BY l.log_time""",
        (person_id, target_date),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def get_weekly_attendance_count():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT session_date, COUNT(DISTINCT person_id) AS present_count
           FROM attendance
           WHERE session_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
           GROUP BY session_date
           ORDER BY session_date"""
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


if __name__ == "__main__":
    create_tables()
    print("Database and tables are ready.")
