from flask import Flask, render_template, request, redirect, session
import sqlite3
import datetime
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = "secret123"

def get_db():
    return sqlite3.connect("database.db")

# ---------- EMAIL ----------
def send_email(to_email, task):
    sender = "yourgmail@gmail.com"
    password = "your_app_password"

    msg = MIMEText(f"You have been assigned: {task}")
    msg["Subject"] = "Task Assigned"
    msg["From"] = sender
    msg["To"] = to_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print("Email error:", e)

# ---------- INIT DB ----------
def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS volunteers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        skills TEXT,
        experience INTEGER,
        email TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task TEXT,
        volunteer TEXT,
        work_type TEXT,
        assign_date TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password TEXT
    )""")

    conn.commit()
    conn.close()

init_db()

# ---------- HOME ----------
@app.route("/")
def home():
    return render_template("dashboard.html")

# ---------- VOLUNTEER ----------
@app.route("/volunteers", methods=["GET","POST"])
def volunteers():
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()

        name = request.form["name"]
        email = request.form["email"]
        skills = ",".join(request.form.getlist("skills"))
        exp = request.form["exp"]

        # 🔥 ALWAYS AVAILABLE (no checkbox issue)
        cur.execute("""
            INSERT INTO volunteers (name, skills, experience, email)
            VALUES (?, ?, ?, ?)
        """, (name, skills, exp, email))

        conn.commit()
        conn.close()

        return render_template("volunteers.html", success=True)

    return render_template("volunteers.html")

# ---------- REGISTER ----------
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()

        cur.execute("INSERT INTO admin (email,password) VALUES (?,?)",
                    (request.form["email"], request.form["password"]))

        conn.commit()
        conn.close()
        return redirect("/login")

    return render_template("register.html")

# ---------- LOGIN ----------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()

        user = cur.execute("""
            SELECT * FROM admin WHERE email=? AND password=?
        """, (request.form["email"], request.form["password"])).fetchone()

        if user:
            session["admin"] = True
            return redirect("/admin")

        return "Invalid login"

    return render_template("login.html")

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/")

# ---------- ADMIN ----------
@app.route("/admin", methods=["GET","POST"])
def admin():
    if "admin" not in session:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    volunteers = []
    task = ""
    work_type = ""

    if request.method == "POST":
        task = request.form["task"]
        skill = request.form["skill"]
        work_type = request.form["work_type"]

        # 🔥 FIXED SEARCH (case insensitive)
        all_volunteers = cur.execute("""
            SELECT * FROM volunteers
            WHERE LOWER(skills) LIKE LOWER(?)
        """, ('%' + skill + '%',)).fetchall()

        # 🔥 2-DAY BLOCK FIX
        assignments = cur.execute("""
            SELECT volunteer, MAX(assign_date)
            FROM assignments
            GROUP BY volunteer
        """).fetchall()

        blocked = []

        for name, date_str in assignments:
            if not date_str:
                continue
            try:
                d = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            except:
                continue

            if (datetime.datetime.now() - d).days < 2:
                blocked.append(name)

        volunteers = [v for v in all_volunteers if v[1] not in blocked]

    return render_template("admin.html",
                           volunteers=volunteers,
                           task=task,
                           work_type=work_type)

# ---------- ASSIGN ----------
@app.route("/assign_task", methods=["POST"])
def assign_task():
    conn = get_db()
    cur = conn.cursor()

    task = request.form["task"]
    volunteer = request.form["volunteer"]
    work_type = request.form["work_type"]

    date = datetime.datetime.now().strftime("%Y-%m-%d")

    # send email
    user = cur.execute("SELECT email FROM volunteers WHERE name=?",
                       (volunteer,)).fetchone()

    if user and user[0]:
        send_email(user[0], task)

    cur.execute("""
        INSERT INTO assignments (task, volunteer, work_type, assign_date)
        VALUES (?,?,?,?)
    """, (task, volunteer, work_type, date))

    conn.commit()
    conn.close()

    return redirect("/admin")

# ---------- VIEW ASSIGNMENTS ----------
@app.route("/view_assignments")
def view_assignments():
    if "admin" not in session:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    data = cur.execute("SELECT * FROM assignments").fetchall()
    conn.close()

    return render_template("assignments.html", assignments=data)

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True)