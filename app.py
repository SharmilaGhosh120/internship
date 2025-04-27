
import streamlit as st
import sqlite3
import os
import reportlab
from reportlab.pdfgen import canvas
import tempfile

# --- DB Functions ---
def get_connection():
    # Use a dynamic path in the current working directory for local development
    db_path = os.path.join(os.getcwd(), "internship_tracking.db")
    # For Streamlit Cloud, ensure the path is writable (e.g., /tmp)
    if "STREAMLIT_CLOUD" in os.environ:
        db_path = os.path.join("/tmp", "internship_tracking.db")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    return conn

def initialize_database():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS internships (
            internship_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            company_name TEXT NOT NULL,
            duration TEXT NOT NULL,
            feedback TEXT,
            FOREIGN KEY (student_id) REFERENCES students (student_id)
        )
    """)
    conn.commit()
    conn.close()

def register_student(name, email):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO students (name, email) VALUES (?, ?)", (name, email))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        st.error(f"Error registering student: {e}")
        return False

def log_internship(email, company, duration, feedback):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT student_id FROM students WHERE email = ?", (email,))
        result = cur.fetchone()
        if result:
            student_id = result[0]
            cur.execute("INSERT INTO internships (student_id, company_name, duration, feedback) VALUES (?, ?, ?, ?)",
                        (student_id, company, duration, feedback))
            conn.commit()
            conn.close()
            return True
        else:
            st.error("Student email not found.")
            return False
    except sqlite3.Error as e:
        st.error(f"Error logging internship: {e}")
        return False

def fetch_reports():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT s.name, s.email, i.company_name, i.duration, i.feedback
            FROM students s
            JOIN internships i ON s.student_id = i.student_id
        """)
        data = cur.fetchall()
        conn.close()
        return data
    except sqlite3.Error as e:
        st.error(f"Error fetching reports: {e}")
        return []

def generate_pdf_report(data):
    # Use temporary file for PDF to avoid permission issues
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf_path = tmp.name
    c = canvas.Canvas(pdf_path)
    c.setFont("Helvetica", 12)
    y = 800
    for row in data:
        text = f"Name: {row[0]}, Email: {row[1]}, Company: {row[2]}, Duration: {row[3]}, Feedback: {row[4]}"
        c.drawString(30, y, text)
        y -= 20
        if y < 40:
            c.showPage()
            y = 800
    c.save()
    return pdf_path

# Initialize database on app start
initialize_database()

# --- Streamlit UI ---
st.title("🎓 Internship Tracking System")

menu = ["Register Student", "Log Internship", "Generate Report"]
choice = st.sidebar.selectbox("Menu", menu)

if choice == "Register Student":
    st.subheader("📝 Student Registration")
    name = st.text_input("Name")
    email = st.text_input("Email")
    if st.button("Register"):
        if name and email:
            if register_student(name, email):
                st.success("Student registered successfully!")
        else:
            st.error("Please enter name and email.")

elif choice == "Log Internship":
    st.subheader("🛠️ Log Internship")
    email = st.text_input("Student Email")
    company = st.text_input("Company Name")
    duration = st.text_input("Duration (e.g., 3 months)")
    feedback = st.text_area("Feedback")
    if st.button("Submit Internship"):
        if email and company and duration:
            if log_internship(email, company, duration, feedback):
                st.success("Internship logged successfully!")
        else:
            st.error("Please fill in all required fields.")

elif choice == "Generate Report":
    st.subheader("📄 Generate Internship Report")
    data = fetch_reports()
    if data:
        if st.button("Generate PDF"):
            pdf_path = generate_pdf_report(data)
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="Download Report",
                    data=f,
                    file_name="internship_report.pdf",
                    mime="application/pdf"
                )
            os.remove(pdf_path)  # Clean up temporary file
    else:
        st.info("No internship data available to generate a report.")