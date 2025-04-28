
import streamlit as st
import sqlite3
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from reportlab.pdfgen import canvas
import tempfile
from uuid import uuid4
import base64
import io

# --- Streamlit Config for Performance ---
st.set_page_config(page_title="Ky'ra Internship Dashboard", layout="wide", initial_sidebar_state="expanded")
sns.set_style("whitegrid")

# --- DB Functions ---
def get_connection():
    db_path = os.path.join(os.getcwd(), "internship_tracking.db")
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
            msme_digitalized INTEGER DEFAULT 0,
            FOREIGN KEY (student_id) REFERENCES students (student_id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            rating INTEGER,
            comments TEXT,
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

def log_internship(email, company, duration, feedback, msme_digitalized):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT student_id FROM students WHERE email = ?", (email,))
        result = cur.fetchone()
        if result:
            student_id = result[0]
            cur.execute("INSERT INTO internships (student_id, company_name, duration, feedback, msme_digitalized) VALUES (?, ?, ?, ?, ?)",
                        (student_id, company, duration, feedback, msme_digitalized))
            conn.commit()
            conn.close()
            return True
        else:
            st.error("Student email not found.")
            return False
    except sqlite3.Error as e:
        st.error(f"Error logging internship: {e}")
        return False

def log_feedback(student_id, rating, comments):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO feedback (student_id, rating, comments) VALUES (?, ?, ?)",
                    (student_id, rating, comments))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        st.error(f"Error logging feedback: {e}")
        return False

def fetch_student_data(email):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT student_id, name FROM students WHERE email = ?", (email,))
        student = cur.fetchone()
        if student:
            cur.execute("SELECT company_name, duration, feedback, msme_digitalized FROM internships WHERE student_id = ?", (student[0],))
            internships = cur.fetchall()
            conn.close()
            return {"student_id": student[0], "name": student[1], "internships": internships}
        conn.close()
        return None
    except sqlite3.Error as e:
        st.error(f"Error fetching student data: {e}")
        return None

def fetch_reports():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT s.name, s.email, i.company_name, i.duration, i.feedback, i.msme_digitalized
            FROM students s
            JOIN internships i ON s.student_id = i.student_id
        """)
        data = cur.fetchall()
        conn.close()
        return data
    except sqlite3.Error as e:
        st.error(f"Error fetching reports: {e}")
        return []

def fetch_metrics():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM internships")
        total_internships = cur.fetchone()[0]
        cur.execute("SELECT SUM(msme_digitalized) FROM internships")
        total_msmes = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(DISTINCT student_id) FROM internships")
        certifications_issued = cur.fetchone()[0]
        conn.close()
        return {
            "total_internships": total_internships,
            "total_msmes": total_msmes,
            "certifications_issued": certifications_issued
        }
    except sqlite3.Error as e:
        st.error(f"Error fetching metrics: {e}")
        return {}

def generate_pdf_report(data):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf_path = tmp.name
    c = canvas.Canvas(pdf_path)
    c.setFont("Helvetica", 12)
    y = 800
    for row in data:
        text = f"Name: {row[0]}, Email: {row[1]}, Company: {row[2]}, Duration: {row[3]}, Feedback: {row[4]}, MSMEs Digitalized: {row[5]}"
        c.drawString(30, y, text)
        y -= 20
        if y < 40:
            c.showPage()
            y = 800
    c.save()
    return pdf_path

def plot_internship_progress(internships):
    if not internships:
        return None
    df = pd.DataFrame(internships, columns=["Company", "Duration", "Feedback", "MSMEs Digitalized"])
    fig, ax = plt.subplots(figsize=(6, 4))
    sns.barplot(x=df.index, y=df["MSMEs Digitalized"], hue=df["Company"], ax=ax)
    ax.set_title("MSMEs Digitalized per Internship")
    ax.set_xlabel("Internship")
    ax.set_ylabel("MSMEs Digitalized")
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode()

# Initialize database
initialize_database()

# --- Streamlit UI ---
st.title("🌟 Ky'ra: Your Internship Journey Mentor")

# Welcome Page
if "page" not in st.session_state:
    st.session_state.page = "Welcome"

if st.session_state.page == "Welcome":
    st.header("Welcome to Ky'ra! 🎉")
    st.write("""
    Ky'ra is your personal mentor to guide you through your internship journey. Here's how to get started:
    - **Register**: Create your profile to track your progress.
    - **Log Internships**: Add details about your internships and impact.
    - **View Progress**: See your journey with charts, badges, and metrics.
    - **Give Feedback**: Share your experience to help us improve.
    """)
    if st.button("Get Started"):
        st.session_state.page = "Main"

# Main Dashboard
if st.session_state.page == "Main":
    # Sidebar Navigation
    menu = ["Your Progress", "Log Internship", "Opportunities", "Feedback", "Generate Report"]
    choice = st.sidebar.selectbox("Navigate", menu, help="Choose a section to explore your journey.")

    # Personalized Greeting
    email_input = st.sidebar.text_input("Enter your email to personalize", help="Enter your registered email to see your progress.")
    student_data = None
    if email_input:
        student_data = fetch_student_data(email_input)
        if student_data:
            st.sidebar.success(f"Hi {student_data['name']}! Welcome back! Here's how you're progressing today.")

    # Metrics Panel
    metrics = fetch_metrics()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Internships Completed", metrics.get("total_internships", 0))
    with col2:
        st.metric("MSMEs Supported", metrics.get("total_msmes", 0))
    with col3:
        st.metric("Certifications Issued", metrics.get("certifications_issued", 0))

    # Your Progress
    if choice == "Your Progress":
        st.header("📊 Your Progress")
        if student_data and student_data["internships"]:
            internships = student_data["internships"]
            total_internships = len(internships)
            msmes_digitalized = sum([int(i[3]) for i in internships])
            progress = min(total_internships * 20, 100)  # Example: 5 internships = 100%
            
            st.progress(progress / 100)
            st.write(f"Internship Completion: {progress}%")
            if progress >= 20:
                st.success("🎉 Badge: First Internship Completed!")
            if msmes_digitalized >= 5:
                st.success("🏆 Badge: Top Performer!")

            # Plot
            plot_data = plot_internship_progress(internships)
            if plot_data:
                st.image(f"data:image/png;base64,{plot_data}", caption="MSMEs Digitalized per Internship")

            st.write("Keep going! You're one step closer to completing your internship journey.")
        else:
            st.info("No internships logged yet. Log your first internship to see your progress!")

    # Log Internship
    elif choice == "Log Internship":
        st.header("🛠️ Log Internship")
        email = st.text_input("Student Email", help="Enter your registered email.")
        company = st.text_input("Company Name", help="Name of the company you interned with.")
        duration = st.text_input("Duration (e.g., 3 months)", help="How long was the internship?")
        feedback = st.text_area("Feedback", help="Share your experience or comments.")
        msme_digitalized = st.number_input("MSMEs Digitalized", min_value=0, help="Number of MSMEs you helped digitalize.")
        if st.button("Submit Internship"):
            if email and company and duration:
                if log_internship(email, company, duration, feedback, msme_digitalized):
                    st.success("Internship logged successfully! You're making great progress!")
            else:
                st.error("Please fill in all required fields.")

    # Opportunities
    elif choice == "Opportunities":
        st.header("🚀 Opportunities")
        st.write("Explore new internship opportunities and grow your skills!")
        st.info("Coming soon: Personalized internship recommendations based on your progress.")
        st.write("You're doing amazing! Keep exploring new possibilities.")

    # Feedback
    elif choice == "Feedback":
        st.header("🗣️ Share Your Feedback")
        if student_data:
            rating = st.slider("How was your experience today?", 1, 5, 3, help="Rate your experience from 1 to 5 stars.")
            comments = st.text_area("Comments", help="Tell us how we can improve.")
            if st.button("Submit Feedback"):
                if log_feedback(student_data["student_id"], rating, comments):
                    st.success("Thank you for your feedback! We're listening.")
        else:
            st.warning("Please enter your email in the sidebar to provide feedback.")
        
        # Testimonial
        st.subheader("What Others Say")
        st.write("> Ky'ra made tracking my internships so easy and motivating! - Sarah K.")
        st.write("Keep shining! Your feedback helps us grow.")

    # Generate Report
    elif choice == "Generate Report":
        st.header("📄 Generate Internship Report")
        data = fetch_reports()
        if data:
            if st.button("Generate PDF", help="Download a PDF report of all internships."):
                pdf_path = generate_pdf_report(data)
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="Download Report",
                        data=f,
                        file_name="internship_report.pdf",
                        mime="application/pdf"
                    )
                os.remove(pdf_path)
            st.write("Great work! Download your report to share your achievements.")
        else:
            st.info("No internship data available to generate a report.")

# --- Mobile Optimization ---
st.markdown("""
<style>
    .stButton > button {
        width: 100%;
    }
    .stTextInput > div > input {
        width: 100%;
    }
    @media (max-width: 600px) {
        .stMetric {
            font-size: 14px;
        }
    }
</style>
""", unsafe_allow_html=True)