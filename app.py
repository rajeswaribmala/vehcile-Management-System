from flask import Flask, render_template, request, redirect, session, send_file,flash,url_for
import sqlite3, os
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.platypus import Table
from reportlab.lib.pagesizes import letter
from flask_mail import Mail, Message
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.pdfbase.ttfonts import TTFont

app = Flask(__name__)
app.secret_key = "vms_secret"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your_app_password'

mail = Mail(app)

def get_db():
    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    db = sqlite3.connect(DB_PATH)
    cursor = db.cursor()

   
    cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    email TEXT,
    password TEXT,
    role TEXT,
    status TEXT DEFAULT 'pending',
    branch_id INTEGER,
    is_active INTEGER DEFAULT 1,
    points INTEGER DEFAULT 0,
    FOREIGN KEY (branch_id) REFERENCES branches(id)
)
""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS service_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    price REAL DEFAULT 0
)
    """)
    cursor.execute("""
CREATE TABLE IF NOT EXISTS service_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    vehicle_id INTEGER,
    service_id INTEGER,
    branch_id INTEGER,
    mechanic_id INTEGER,

    status TEXT DEFAULT 'Pending',

    cost REAL DEFAULT 0,

    additional_repair TEXT,
    additional_cost REAL DEFAULT 0,
    additional_status TEXT DEFAULT 'None',

    payment_status TEXT DEFAULT 'Unpaid',

    start_time TEXT,
    end_time TEXT,
    completed_at TEXT,

    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
    FOREIGN KEY (service_id) REFERENCES service_categories(id),
    FOREIGN KEY (mechanic_id) REFERENCES users(id),
    FOREIGN KEY (branch_id) REFERENCES branches(id)
)
""")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    vehicle_number TEXT NOT NULL,
    model TEXT NOT NULL,
    vehicle_type TEXT NOT NULL,
    year INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
)
""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_request_id INTEGER,
        amount REAL,
        payment_date TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contact_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
    message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")
    

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_request_id INTEGER,
        user_id INTEGER,
        mechanic_id INTEGER,
        rating INTEGER,
        message TEXT,
        created_at TEXT
    )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS branches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch_name TEXT NOT NULL,
            location TEXT NOT NULL
        )
    """)
    existing_branches = cursor.execute(
        "SELECT COUNT(*) FROM branches"
    ).fetchone()[0]

    if existing_branches == 0:
        cursor.executemany("""
            INSERT INTO branches (branch_name, location)
            VALUES (?, ?)
        """, [
            ("Chennai Central", "Chennai"),
            ("Coimbatore Hub", "Coimbatore"),
            ("Madurai Service Point", "Madurai"),
        ])
    existing = cursor.execute("SELECT COUNT(*) FROM service_categories").fetchone()[0]
    if existing == 0:
       cursor.executemany("""
        INSERT INTO service_categories (name, price) VALUES (?, ?)
        """, [
                ("Oil Change", 700),
                ("Brake Service", 1200),
                ("Engine Repair", 2500),
                ("General Service", 1500),
            ])
    db.commit()
    db.close()


init_db()
@app.route("/register/user", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()

        existing = db.execute(
            "SELECT id FROM users WHERE username=?",
            (username,)
        ).fetchone()

        if existing:
            return render_template("register.html", error="Username already exists")

        db.execute("""
            INSERT INTO users (username, password, role, status, is_active, points)
            VALUES (?, ?, 'user', 'approved', 1, 0)
        """, (username, password))

        db.commit()
        return redirect("/login")

    return render_template("register.html")

@app.route("/")
def home():
    db = get_db()

    feedbacks = db.execute("""
        SELECT u.username, f.rating, f.message
        FROM feedback f
        JOIN users u ON f.user_id = u.id
        ORDER BY f.id DESC
    """).fetchall()
    rating_summary = db.execute("""
        SELECT rating, COUNT(*) as total
        FROM feedback
        GROUP BY rating
    """).fetchall()

    rating_count = {1:0,2:0,3:0,4:0,5:0}

    for r in rating_summary:
        rating_count[r["rating"]] = r["total"]

    total_feedback = sum(rating_count.values())

    return render_template(
        "home.html",
        feedbacks=feedbacks,
        rating_count=rating_count,
        total_feedback=total_feedback
    )
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form["role"]
        username = request.form["username"]
        password = request.form["password"]
        if role == "admin" and username == "admin" and password == "admin123":
            session["role"] = "admin"
            return redirect("/admin/dashboard")

        db = get_db()
        user = db.execute("""
            SELECT id, is_active FROM users
            WHERE username=? AND password=? AND role=?
        """, (username, password, role)).fetchone()

        if user:
            if user["is_active"] == 0:
                return render_template("login.html",
                                       error="Your account has been blocked by admin. Please contact support.")
            session["user_id"] = user["id"]
            session["role"] = role

            if role == "user":
                return redirect("/dashboard")

            if role == "mechanic":
                return redirect("/mechanic/dashboard")
        return render_template("login.html", error="Invalid Username or Password")

    return render_template("login.html")
@app.route("/user/add_vehicle", methods=["GET", "POST"])
def add_vehicle():
    if request.method == "POST":
        number = request.form["number"]
        model = request.form["model"]
        vehicle_type = request.form["type"]
        year = request.form["year"]
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO vehicles (user_id, vehicle_number, model, vehicle_type, year)
            VALUES (?, ?, ?, ?, ?)
        """, (session["user_id"], number, model, vehicle_type, year))
        conn.commit()
        conn.close()

        return redirect("/dashboard")

    return render_template("add_vehicle.html")
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():

    if session.get("role") != "user":
        return redirect("/")

    db = get_db()
    user = db.execute(
        "SELECT status FROM users WHERE id=?",
        (session["user_id"],)
    ).fetchone()

    if user and user["status"] == "blocked":
        session.clear()
        return render_template(
            "login.html",
            error="Your account has been blocked by admin."
        )
    vehicles = db.execute(
        "SELECT * FROM vehicles WHERE user_id=?",
        (session["user_id"],)
    ).fetchall()
    all_services = db.execute(
        "SELECT * FROM service_categories"
    ).fetchall()
    if request.method == "POST":

        user_id = session["user_id"]
        vehicle_id = request.form["vehicle"]
        service_ids = request.form.getlist("service")
        service_id_string = ",".join(service_ids)
        mechanic = db.execute("""
            SELECT id FROM users
            WHERE role='mechanic'
            AND status='approved'
            AND is_active=1
            ORDER BY id ASC
            LIMIT 1
        """).fetchone()

        mechanic_id = mechanic["id"] if mechanic else None

        db.execute("""
            INSERT INTO service_requests
            (user_id, vehicle_id, service_id, mechanic_id, status)
            VALUES (?, ?, ?, ?, 'Assigned')
        """, (user_id, vehicle_id, service_id_string, mechanic_id))

        db.commit()
    raw_requests = db.execute("""
        SELECT *
        FROM service_requests
        WHERE user_id=?
        ORDER BY id DESC
    """, (session["user_id"],)).fetchall()

    requests = []

    for r in raw_requests:

        service_value = r["service_id"]
        if isinstance(service_value, int):
            service_ids = [str(service_value)]
        else:
            service_ids = service_value.split(",")

        placeholders = ",".join("?" * len(service_ids))

        service_list = db.execute(f"""
            SELECT name, price
            FROM service_categories
            WHERE id IN ({placeholders})
        """, service_ids).fetchall()

        total_cost = sum(s["price"] for s in service_list)

        requests.append({
            "id": r["id"],
            "services": service_list,
            "status": r["status"],
            "cost": total_cost,
            "additional_cost": r["additional_cost"] or 0,
            "additional_status": r["additional_status"],
            "payment_status": r["payment_status"],
            "additional_repair": r["additional_repair"]
        })
    return render_template(
        "user_dashboard.html",
        vehicles=vehicles,
        services=all_services,
        requests=requests
    )
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
@app.route("/register/mechanic", methods=["GET", "POST"])
def register_mechanic():

    db = get_db()

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        branch_id = request.form["branch_id"]

        db.execute("""
            INSERT INTO users 
            (username, password, role, status, is_active, points, branch_id)
            VALUES (?, ?, 'mechanic', 'pending', 1, 0, ?)
        """, (username, password, branch_id))

        db.commit()
        return redirect("/login")
    branches = db.execute("SELECT * FROM branches").fetchall()

    print("Branches:", branches) 

    return render_template("register_mechanic.html", branches=branches)
@app.route("/mechanic/dashboard")
def mechanic_dashboard():

    if session.get("role") != "mechanic":
        return redirect("/")

    db = get_db()

    raw_requests = db.execute("""
        SELECT sr.*, u.username
        FROM service_requests sr
        JOIN users u ON sr.user_id = u.id
        WHERE sr.mechanic_id=?
        ORDER BY sr.id DESC
    """, (session["user_id"],)).fetchall()

    requests = []

    for r in raw_requests:

        service_ids = str(r["service_id"]).split(",")

        placeholders = ",".join("?" * len(service_ids))

        service_list = db.execute(f"""
            SELECT name, price
            FROM service_categories
            WHERE id IN ({placeholders})
        """, service_ids).fetchall()

        service_names = ", ".join(s["name"] for s in service_list)
        total_price = sum(s["price"] for s in service_list)

        requests.append({
            "id": r["id"],
            "customer": r["username"],
            "services": service_names,
            "total": total_price,
            "status": r["status"]
        })

    return render_template("mechanic_dashboard.html", requests=requests)
@app.route("/mechanic/additional/<int:request_id>", methods=["GET", "POST"])
def mechanic_additional(request_id):

    if session.get("role") != "mechanic":
        return redirect("/")

    db = get_db()

    service = db.execute("""
        SELECT *
        FROM service_requests
        WHERE id=? AND mechanic_id=?
    """, (request_id, session["user_id"])).fetchone()

    if not service:
        flash("Invalid request access")
        return redirect("/mechanic/additional_list")

    if request.method == "POST":
        repair = request.form.get("repair")
        cost = request.form.get("cost")

        db.execute("""
            UPDATE service_requests
            SET additional_repair=?,
                additional_cost=?,
                additional_status='Requested'
            WHERE id=? AND mechanic_id=?
        """, (repair, cost, request_id, session["user_id"]))

        db.commit()
        flash("Additional repair sent!")
        return redirect("/mechanic/additional_list")

    return render_template("mechanic_additional.html", service=service)
from datetime import datetime

@app.route("/mechanic/update/<int:request_id>/<status>")
def mechanic_update(request_id, status):

    if session.get("role") != "mechanic":
        return redirect("/")

    allowed = ["In Progress", "Completed"]

    if status not in allowed:
        return redirect("/mechanic/dashboard")

    db = get_db()

    if status == "Completed":
        db.execute("""
            UPDATE service_requests
            SET status=?, completed_at=?
            WHERE id=? AND mechanic_id=?
        """, (
            status,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            request_id,
            session["user_id"]
        ))

        db.execute("""
            UPDATE users
            SET points = points + 1
            WHERE id=?
        """, (session["user_id"],))

    else:
        db.execute("""
            UPDATE service_requests
            SET status=?
            WHERE id=? AND mechanic_id=?
        """, (status, request_id, session["user_id"]))

    db.commit()

    return redirect("/mechanic/dashboard")
@app.route("/admin/dashboard")
def admin_dashboard():

    if session.get("role") != "admin":
        return redirect("/")

    db = get_db()
    total_users = db.execute(
        "SELECT COUNT(*) FROM users WHERE role='user'"
    ).fetchone()[0]

    total_mechanics = db.execute(
        "SELECT COUNT(*) FROM users WHERE role='mechanic'"
    ).fetchone()[0]

    total_services = db.execute(
        "SELECT COUNT(*) FROM service_requests"
    ).fetchone()[0]

    total_revenue = db.execute("""
    SELECT SUM(
        cost +
        CASE
            WHEN additional_status='Approved'
            THEN additional_cost
            ELSE 0
        END
    )
    FROM service_requests
    WHERE payment_status='Paid'
""").fetchone()[0] or 0
    raw_requests = db.execute("""
        SELECT sr.*, u.username
        FROM service_requests sr
        LEFT JOIN users u ON sr.user_id = u.id
        ORDER BY sr.id DESC
    """).fetchall()

    services = []

    for r in raw_requests:

        service_ids = str(r["service_id"]).split(",")

        placeholders = ",".join("?" * len(service_ids))

        service_list = db.execute(f"""
            SELECT name, price
            FROM service_categories
            WHERE id IN ({placeholders})
        """, service_ids).fetchall()

        service_names = ", ".join(s["name"] for s in service_list)
        total_price = sum(s["price"] for s in service_list)

        services.append({
            "id": r["id"],
            "username": r["username"],
            "services": service_names,
            "status": r["status"],
            "total": total_price
        })

    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        total_mechanics=total_mechanics,
        total_services=total_services,
        total_revenue=total_revenue,
        services=services
    )
@app.route("/admin/mechanics")
def admin_mechanics():
    if session.get("role") != "admin":
        return redirect("/")

    db = get_db()

    mechanics = db.execute("""
        SELECT 
            u.id,
            u.username,
            u.status,
            b.branch_name,
            COUNT(sr.id) AS points
        FROM users u
        JOIN branches b ON u.branch_id = b.id
        LEFT JOIN service_requests sr 
            ON sr.mechanic_id = u.id
            AND sr.status='Completed'
            AND strftime('%m', sr.completed_at)=strftime('%m','now')
            AND strftime('%Y', sr.completed_at)=strftime('%Y','now')
        WHERE u.role='mechanic'
        GROUP BY u.id
        ORDER BY b.branch_name, points DESC
    """).fetchall()

    return render_template("admin_mechanics.html", mechanics=mechanics)
@app.route("/admin/service-history")
def admin_service_history():

    if session.get("role") != "admin":
        return redirect("/")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    raw_requests = c.execute("""
        SELECT sr.*, 
               u.username AS user_name,
               m.username AS mechanic_name
        FROM service_requests sr
        JOIN users u ON sr.user_id = u.id
        LEFT JOIN users m ON sr.mechanic_id = m.id
        WHERE strftime('%Y-%m', sr.completed_at) = strftime('%Y-%m', 'now')
        ORDER BY sr.id DESC
    """).fetchall()

    services_list = []

    for r in raw_requests:

        service_value = r["service_id"]

        if isinstance(service_value, int):
            service_ids = [str(service_value)]
        else:
            service_ids = service_value.split(",")

        placeholders = ",".join(["?"] * len(service_ids))

        services = c.execute(f"""
            SELECT name
            FROM service_categories
            WHERE id IN ({placeholders})
        """, service_ids).fetchall()

        service_names = ", ".join(s["name"] for s in services)

        service_cost = r["cost"] if r["cost"] else 0
        repair_cost = r["additional_cost"] if r["additional_cost"] else 0
        total_cost = service_cost + repair_cost

        services_list.append({
            "id": r["id"],
            "user_name": r["user_name"],
            "mechanic_name": r["mechanic_name"] if r["mechanic_name"] else "Not Assigned",
            "service_name": service_names,
            "repair": r["additional_repair"] if r["additional_repair"] else "-",
            "service_cost": service_cost,
            "repair_cost": repair_cost,
            "total_cost": total_cost,
            "completed_at": r["completed_at"] if r["completed_at"] else "-",
            "status": r["status"]
        })

    conn.close()

    return render_template("admin_service_history.html", services=services_list)
from datetime import datetime

@app.route("/admin/reports")
def admin_reports():

    if session.get("role") != "admin":
        return redirect("/")

    db = get_db()
    total_users = db.execute("""
        SELECT COUNT(*) FROM users
        WHERE role='user'
    """).fetchone()[0]
    total_mechanics = db.execute("""
        SELECT COUNT(*) FROM users
        WHERE role='mechanic'
    """).fetchone()[0]
    total_services = db.execute("""
        SELECT COUNT(*) FROM service_requests
    """).fetchone()[0]
    branch_revenue = db.execute("""
        SELECT b.branch_name,
               IFNULL(SUM(s.cost + s.additional_cost),0) AS branch_total
        FROM service_requests s
        JOIN branches b ON s.branch_id = b.id
        WHERE s.payment_status='Paid'
        AND strftime('%Y-%m', s.completed_at) = strftime('%Y-%m','now')
        GROUP BY b.branch_name
    """).fetchall()
    monthly_revenue = db.execute("""
        SELECT strftime('%Y-%m', completed_at) AS month,
               IFNULL(SUM(cost + additional_cost),0) AS monthly_total
        FROM service_requests
        WHERE payment_status='Paid'
        GROUP BY month
        ORDER BY month DESC
    """).fetchall()
    total_revenue = db.execute("""
        SELECT IFNULL(SUM(cost + additional_cost),0)
        FROM service_requests
        WHERE payment_status='Paid'
        AND strftime('%Y-%m', completed_at) = strftime('%Y-%m','now')
    """).fetchone()[0]
    current_month = datetime.now().strftime("%B %Y")
    return render_template(
        "admin_reports.html",
        total_users=total_users,
        total_mechanics=total_mechanics,
        total_services=total_services,
        branch_revenue=branch_revenue,
        monthly_revenue=monthly_revenue,
        total_revenue=total_revenue,
        current_month=current_month
    )
@app.route("/admin/feedback")
def admin_feedback():
    if session.get("role") != "admin":
        return redirect("/")
    db = get_db()
    feedbacks = db.execute("""
        SELECT f.id,
               u.username AS customer,
               m.username AS mechanic,
               f.rating,
               f.message,
               f.created_at
        FROM feedback f
        LEFT JOIN users u ON f.user_id = u.id
        LEFT JOIN users m ON f.mechanic_id = m.id
        ORDER BY f.id DESC
    """).fetchall()
    return render_template("admin_feedback.html", feedbacks=feedbacks)
@app.route("/admin/mechanic/approve/<int:id>")
def approve_mechanic(id):
    if session.get("role") != "admin":
        return redirect("/")
    db = get_db()
    db.execute("""
        UPDATE users
        SET status='approved'
        WHERE id=?
    """, (id,))
    db.commit()
    return redirect("/admin/mechanics")
from datetime import datetime
@app.route("/user/payment/<int:request_id>", methods=["GET", "POST"])
def payment(request_id):
    if session.get("role") != "user":
        return redirect("/")
    db = get_db()
    service = db.execute("""
        SELECT *
        FROM service_requests
        WHERE id=? AND user_id=?
    """, (request_id, session["user_id"])).fetchone()
    if not service:
        return redirect("/dashboard")
    if request.method == "POST":
        method = request.form["method"]
        if method == "card":
            card = request.form["card_number"]
            if len(card) != 16:
                return "Invalid Card Number"
        elif method == "upi":
            upi = request.form["upi_id"]
            if "@" not in upi:
                return "Invalid UPI ID"
        base = service["cost"] or 0
        additional = 0
        if service["additional_status"] == "Approved":
            additional = service["additional_cost"] or 0
        total = base + additional
        db.execute("""
            UPDATE service_requests
            SET payment_status='Paid'
            WHERE id=? AND user_id=?
        """, (request_id, session["user_id"]))
        db.execute("""
            INSERT INTO payments (service_request_id, amount, payment_date)
            VALUES (?, ?, ?)
        """, (
            request_id,
            total,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        db.commit()
        return redirect(url_for("show_bill", service_id=request_id))
    return render_template("payment.html", service=service)
@app.route("/feedback/<int:service_id>")
def feedback(service_id):
    if session.get("role") != "user":
        return redirect("/")
    return render_template("feedback_page.html", service_id=service_id)
@app.route("/submit_feedback", methods=["POST"])
def submit_feedback():
    if session.get("role") != "user":
        return redirect("/")
    service_id = request.form.get("service_id")
    rating = request.form.get("rating")
    message = request.form.get("message")
    if not rating:
        return "Please select a rating"
    db = get_db()
    service = db.execute("""
        SELECT mechanic_id
        FROM service_requests
        WHERE id=? AND user_id=?
    """, (service_id, session["user_id"])).fetchone()
    if not service:
        return "Invalid service"
    mechanic_id = service["mechanic_id"]
    db.execute("""
        INSERT INTO feedback
        (service_request_id, user_id, mechanic_id, rating, message, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        service_id,
        session["user_id"],
        mechanic_id,
        rating,
        message,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    db.commit()
    return redirect("/dashboard")  
def admin_categories():
    if session.get("role") != "admin":
        return redirect("/")
    db = get_db()
    categories = db.execute("""
        SELECT id, name
        FROM service_categories
        ORDER BY id DESC
    """).fetchall()
    return render_template("admin_categories.html", categories=categories)
@app.route("/admin/category/add", methods=["POST"])
def add_category():
    if session.get("role") != "admin":
        return redirect("/")
    name = request.form.get("name")
    db = get_db()
    db.execute("""
        INSERT INTO service_categories (name)
        VALUES (?)
    """, (name,))
    db.commit()
    return redirect("/admin/categories")
@app.route("/admin/category/delete/<int:id>")
def delete_category(id):
    if session.get("role") != "admin":
        return redirect("/")
    db = get_db()
    db.execute("DELETE FROM service_categories WHERE id=?", (id,))
    db.commit()
    return redirect("/admin/categories")
@app.route("/admin/users")
def manage_users():
    if session.get("role") != "admin":
        return redirect("/")
    db = get_db()
    users = db.execute("""
        SELECT id, username, role, status
        FROM users
        WHERE role='user'
        ORDER BY id DESC
    """).fetchall()
    return render_template("admin_users.html", users=users)
@app.route("/admin/user/block/<int:user_id>")
def block_user(user_id):
    if session.get("role") != "admin":
        return redirect("/")
    db = get_db()
    user = db.execute(
        "SELECT status FROM users WHERE id=?",
        (user_id,)
    ).fetchone()
    if user:
        new_status = "blocked" if user["status"] == "active" else "active"
        db.execute(
            "UPDATE users SET status=? WHERE id=?",
            (new_status, user_id)
        )
        db.commit()
    return redirect("/admin/users")
@app.route("/admin/user/delete/<int:user_id>")
def delete_user(user_id):
    if session.get("role") != "admin":
        return redirect("/")
    db = get_db()
    db.execute("DELETE FROM users WHERE id=?", (user_id,))
    db.commit()
    return redirect("/admin/users")
@app.route("/mechanic/additional_repair/<int:service_id>", methods=["POST"])
def additional_repair(service_id):
    if session.get("role") != "mechanic":
        return redirect("/")
    additional_repair = request.form.get("additional_repair")
    additional_cost = request.form.get("additional_cost")
    if not additional_repair or not additional_cost:
        return "All fields required"
    additional_cost = float(additional_cost)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE service_requests
        SET additional_repair=?,
            additional_cost=?,
            additional_status='Pending'
        WHERE id=? AND mechanic_id=?
    """, (additional_repair, additional_cost, service_id, session["user_id"]))
    conn.commit()
    conn.close()
    return redirect("/mechanic/dashboard")
@app.route("/confirm_additional/<int:service_id>")
def confirm_additional(service_id):
    if session.get("role") != "user":
        return redirect("/")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE service_requests
        SET additional_status='Approved'
        WHERE id=? AND user_id=?
    """, (service_id, session["user_id"]))
    conn.commit()
    conn.close()
    return redirect("/dashboard")
@app.route("/mechanic/complete/<int:service_id>", methods=["POST"])
def complete_service(service_id):
    if session.get("role") != "mechanic":
        return redirect("/")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT mechanic_id FROM service_requests
        WHERE id=? AND mechanic_id=?
    """, (service_id, session["user_id"]))
    service = c.fetchone()
    if not service:
        conn.close()
        return "Invalid service"
    c.execute("""
        UPDATE service_requests
        SET status='Completed',
            completed_at=datetime('now')
        WHERE id=?
    """, (service_id,))
    c.execute("""
        UPDATE users
        SET points = points + 1
        WHERE id=?
    """, (session["user_id"],))
    conn.commit()
    conn.close()
    return redirect("/mechanic/dashboard")
@app.route("/download_bill/<int:service_id>")
def download_bill(service_id):
    if session.get("role") != "user":
        return redirect("/")
    db = get_db()
    service = db.execute("""
        SELECT sr.*,
               u.username AS customer_name,
               v.vehicle_number AS vehicle_number,
               m.username AS mechanic_name
        FROM service_requests sr
        JOIN users u ON sr.user_id = u.id
        JOIN vehicles v ON sr.vehicle_id = v.id
        LEFT JOIN users m ON sr.mechanic_id = m.id
        WHERE sr.id=? AND sr.user_id=?
    """, (service_id, session["user_id"])).fetchone()
    if not service:
        return redirect("/dashboard")
    from datetime import datetime
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.lib.pagesizes import A4
    file_path = f"invoice_{service_id}.pdf"
    doc = SimpleDocTemplate(file_path, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    title_style.alignment = 1
    elements.append(Paragraph("AutoCare Vehicle Service Center", title_style))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph("24, Anna Salai, T Nagar, Chennai - 600017", styles["Normal"]))
    elements.append(Paragraph("Phone: +91 98765 43210", styles["Normal"]))
    elements.append(Spacer(1, 0.3 * inch))
    base = service["cost"] if service["cost"] else 0
    additional = 0
    if service["additional_status"] == "Approved":
        additional = service["additional_cost"] if service["additional_cost"] else 0
    total = base + additional
    invoice_date = service["created_at"] if "created_at" in service.keys() else datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    mechanic_name = service["mechanic_name"] if service["mechanic_name"] else "Not Assigned"
    additional_work = service["additional_repair"] if service["additional_repair"] else "-"
    data = [
        ["Invoice No", f"INV{service_id}"],
        ["Date & Time", invoice_date],
        ["Customer Name", service["customer_name"]],
        ["Vehicle Number", service["vehicle_number"]],
        ["Mechanic Name", mechanic_name],
        ["Service Cost", f"₹ {base}"],
        ["Additional Work", additional_work],
        ["Additional Cost", f"₹ {additional}"],
        ["TOTAL PAID", f"₹ {total}"]
    ]
    table = Table(data, colWidths=[2.5 * inch, 3.5 * inch])
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.green),
        ('FONTSIZE', (0, -1), (-1, -1), 13),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(Paragraph("Thank you for choosing AutoCare. Drive Safe!", styles["Normal"]))
    doc.build(elements)
    return send_file(file_path, as_attachment=True)
@app.route("/user/track/<int:id>")
def track_service(id):
    if session.get("role") != "user":
        return redirect("/")
    db = get_db()
    request_data = db.execute("""
        SELECT *
        FROM service_requests
        WHERE id=? AND user_id=?
    """, (id, session["user_id"])).fetchone()
    if not request_data:
        return redirect("/dashboard")
    service_value = request_data["service_id"]
    if isinstance(service_value, int):
        service_ids = [str(service_value)]
    else:
        service_ids = service_value.split(",")
    placeholders = ",".join("?" * len(service_ids))
    service_list = db.execute(f"""
        SELECT name
        FROM service_categories
        WHERE id IN ({placeholders})
    """, service_ids).fetchall()
    return render_template(
        "service_timeline.html",
        service=request_data,
        service_list=service_list
    )
@app.route("/user/additional/<int:request_id>", methods=["GET", "POST"])
def user_additional_page(request_id):
    if session.get("role") != "user":
        return redirect("/")
    db = get_db()
    if request.method == "POST":
        action = request.form["action"]
        if action == "approve":
            db.execute("""
                UPDATE service_requests
                SET additional_status='Approved'
                WHERE id=? AND user_id=?
            """, (request_id, session["user_id"]))
        elif action == "reject":
            db.execute("""
                UPDATE service_requests
                SET additional_status='Rejected'
                WHERE id=? AND user_id=?
            """, (request_id, session["user_id"]))
        db.commit()
        return redirect("/dashboard")
    service = db.execute("""
        SELECT additional_repair, additional_cost, additional_status
        FROM service_requests
        WHERE id=? AND user_id=?
    """, (request_id, session["user_id"])).fetchone()

    return render_template("additional.html", service=service)
@app.route("/mechanic/additional_list")
def mechanic_additional_list():
    if session.get("role") != "mechanic":
        return redirect("/")
    db = get_db()
    raw_requests = db.execute("""
        SELECT sr.id,
               u.username AS customer,
               sr.service_id,
               sr.additional_status
        FROM service_requests sr
        JOIN users u ON sr.user_id = u.id
        WHERE sr.mechanic_id = ?
        ORDER BY sr.id DESC
    """, (session["user_id"],)).fetchall()
    requests = []
    for r in raw_requests:
        service_ids = str(r["service_id"]).split(",")
        placeholders = ",".join("?" * len(service_ids))
        service_list = db.execute(f"""
            SELECT name
            FROM service_categories
            WHERE id IN ({placeholders})
        """, service_ids).fetchall()
        service_names = ", ".join(s["name"] for s in service_list)
        requests.append({
            "id": r["id"],
            "customer": r["customer"],
            "service": service_names,
            "additional_status": r["additional_status"]
        })
    return render_template(
        "mechanic_additional_list.html",
        requests=requests
    )
from datetime import datetime
@app.route("/show_bill/<int:service_id>")
def show_bill(service_id):
    if session.get("role") != "user":
        return redirect("/")
    db = get_db()
    service = db.execute("""
        SELECT *
        FROM service_requests
        WHERE id=? AND user_id=?
    """, (service_id, session["user_id"])).fetchone()
    if not service:
        return redirect("/dashboard")
    user = db.execute("""
        SELECT username
        FROM users
        WHERE id=?
    """, (service["user_id"],)).fetchone()
    vehicle = db.execute("""
        SELECT vehicle_number
        FROM vehicles
        WHERE id=?
    """, (service["vehicle_id"],)).fetchone()
    mechanic = db.execute("""
        SELECT username
        FROM users
        WHERE id=?
    """, (service["mechanic_id"],)).fetchone()
    service_ids = str(service["service_id"]).split(",")
    placeholders = ",".join("?" * len(service_ids))

    service_list = db.execute(f"""
        SELECT name
        FROM service_categories
        WHERE id IN ({placeholders})
    """, service_ids).fetchall()
    service_names = ", ".join(s["name"] for s in service_list)
    base_cost = service["cost"] or 0
    additional_cost = 0
    additional_repair = ""
    if service["additional_status"] == "Approved":
        additional_cost = service["additional_cost"] or 0
        additional_repair = service["additional_repair"] or ""
    total_amount = base_cost + additional_cost
    return render_template(
        "bill.html",
        service=service,
        current_datetime=datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
        user_name=user["username"] if user else "",
        vehicle_number=vehicle["vehicle_number"] if vehicle else "",
        mechanic_name=mechanic["username"] if mechanic else "",
        service_name=service_names,
        service_cost=base_cost,
        additional_cost=additional_cost,
        additional_repair=additional_repair,
        total_amount=total_amount
    )
@app.route("/reject_additional/<int:service_id>")
def reject_additional(service_id):

    if session.get("role") != "user":
        return redirect("/")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE service_requests
        SET additional_status='Rejected',
            additional_cost=0,
            additional_repair=NULL
        WHERE id=? AND user_id=?
    """, (service_id, session["user_id"]))
    conn.commit()
    conn.close()
    return redirect("/dashboard")
def assign_mechanic(branch_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM users
        WHERE role = 'mechanic'
        AND branch_id = ?
        AND is_active = 1
        AND status = 'approved'
    """, (branch_id,))
    mechanics = cursor.fetchall()
    for mech in mechanics:
        mech_id = mech[0]
        cursor.execute("""
            SELECT COUNT(*) FROM service_requests
            WHERE mechanic_id = ?
            AND status IN ('Assigned', 'In Progress')
        """, (mech_id,))
        active_jobs = cursor.fetchone()[0]
        if active_jobs == 0:
            conn.close()
            return mech_id
    conn.close()
    return None
@app.route("/mechanic/start/<int:request_id>")
def mechanic_start(request_id):
    if session.get("role") != "mechanic":
        return redirect("/")
    db = get_db()
    db.execute("""
        UPDATE service_requests
        SET status = 'In Progress'
        WHERE id = ?
    """, (request_id,))
    db.commit()
    return redirect("/mechanic/dashboard")
@app.route("/admin/mechanic/delete/<int:id>")
def delete_mechanic(id):
    if session.get("role") != "admin":
        return redirect("/")
    db = get_db()
    db.execute("DELETE FROM users WHERE id=? AND role='mechanic'", (id,))
    db.commit()
    return redirect("/admin/mechanics")
@app.route("/mechanic/update_status/<int:request_id>/<status>")
def update_status(request_id, status):
    if session.get("role") != "mechanic":
        return redirect("/")
    db = get_db()
    db.execute("""
        UPDATE service_requests
        SET status=?
        WHERE id=? AND mechanic_id=?
    """, (status, request_id, session["user_id"]))
    db.commit()
    return redirect("/mechanic/dashboard")
@app.route("/user/book_service", methods=["GET", "POST"])
def book_service():
    if session.get("role") != "user":
        return redirect("/")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT id, branch_name FROM branches")
    branches = c.fetchall()

    c.execute("""
        SELECT id, vehicle_number 
        FROM vehicles 
        WHERE user_id=?
    """, (session["user_id"],))
    vehicles = c.fetchall()

    c.execute("SELECT id, name, price FROM service_categories")
    services = c.fetchall()

    if request.method == "POST":
        branch_id = request.form["branch_id"]
        vehicle_id = request.form["vehicle_id"]
        mechanic_id = request.form.get("mechanic_id")
        service_ids = request.form.getlist("service_ids")

        if not service_ids:
            conn.close()
            return "Please select at least one service"

        placeholders = ",".join("?" * len(service_ids))
        c.execute(f"""
            SELECT SUM(price) as total
            FROM service_categories
            WHERE id IN ({placeholders})
        """, service_ids)

        total_price = c.fetchone()["total"]
        service_id_string = ",".join(service_ids)

        if not mechanic_id:
            mechanic_id = assign_mechanic(branch_id)

        if not mechanic_id:
            conn.close()
            return "No mechanic available"

        c.execute("""
            INSERT INTO service_requests
            (user_id, vehicle_id, service_id, mechanic_id,
             branch_id, cost, status, payment_status)
            VALUES (?, ?, ?, ?, ?, ?, 'Assigned', 'Unpaid')
        """, (
            session["user_id"],
            vehicle_id,
            service_id_string,
            mechanic_id,
            branch_id,
            total_price
        ))

        conn.commit()
        conn.close()
        return redirect("/dashboard")

    conn.close()
    return render_template(
        "book_service.html",
        branches=branches,
        vehicles=vehicles,
        services=services
    )
@app.route("/admin/categories")
def admin_categories():
    if session.get("role") != "admin":
        return redirect("/")

    db = get_db()
    categories = db.execute("""
        SELECT id, name
        FROM service_categories
        ORDER BY id DESC
    """).fetchall()

    return render_template("admin_categories.html", categories=categories)
def assign_mechanic(branch_id):
    db = get_db()

    mechanic = db.execute("""
        SELECT u.id, COUNT(sr.id) as total_jobs
        FROM users u
        LEFT JOIN service_requests sr 
            ON u.id = sr.mechanic_id 
            AND sr.status IN ('Assigned', 'In Progress')
        WHERE u.role='mechanic'
        AND u.branch_id=?
        AND u.status='approved'
        AND u.is_active=1
        GROUP BY u.id
        ORDER BY total_jobs ASC
        LIMIT 1
    """, (branch_id,)).fetchone()

    return mechanic["id"] if mechanic else None
@app.route("/about")
def about():
    return render_template("about.html")
@app.route("/contact", methods=["GET","POST"])
def contact():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        message = request.form["message"]
        db = get_db()
        db.execute("""
        INSERT INTO contact_messages(name,email,message)
        VALUES(?,?,?)
        """,(name,email,message))
        db.commit()
        flash("Message sent successfully!")
        return redirect("/contact")
    return render_template("contact.html")
@app.route("/mechanic/points")
def mechanic_points():
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    mechanic_id = session["user_id"]
    mechanic = db.execute(
        "SELECT username FROM users WHERE id=?",
        (mechanic_id,)
    ).fetchone()
    monthly_points = db.execute("""
        SELECT COUNT(*) 
        FROM service_requests
        WHERE mechanic_id=?
        AND status='Completed'
        AND strftime('%m', completed_at)=strftime('%m','now')
        AND strftime('%Y', completed_at)=strftime('%Y','now')
    """, (mechanic_id,)).fetchone()[0]
    history = db.execute("""
        SELECT 
            strftime('%m', completed_at) AS month,
            strftime('%Y', completed_at) AS year,
            COUNT(*) AS points
        FROM service_requests
        WHERE mechanic_id=? 
        AND status='Completed'
        GROUP BY year, month
        ORDER BY year DESC, month DESC
    """, (mechanic_id,)).fetchall()
    return render_template(
        "mechanic_points.html",
        mechanic=mechanic,
        monthly_points=monthly_points,
        history=history
    )
@app.route("/admin/mechanic/points/<int:mechanic_id>")
def admin_view_mechanic_points(mechanic_id):
    db = get_db()
    mechanic = db.execute(
        "SELECT username FROM users WHERE id=?",
        (mechanic_id,)
    ).fetchone()
    monthly_points = db.execute("""
        SELECT COUNT(*) 
        FROM service_requests
        WHERE mechanic_id=?
        AND status='Completed'
        AND strftime('%m', completed_at)=strftime('%m','now')
        AND strftime('%Y', completed_at)=strftime('%Y','now')
    """, (mechanic_id,)).fetchone()[0]
    history = db.execute("""
        SELECT 
            strftime('%m', completed_at) AS month,
            strftime('%Y', completed_at) AS year,
            COUNT(*) AS points
        FROM service_requests
        WHERE mechanic_id=? 
        AND status='Completed'
        GROUP BY year, month
        ORDER BY year DESC, month DESC
    """, (mechanic_id,)).fetchall()
    return render_template(
        "admin_mechanic_points.html",
        mechanic=mechanic,
        monthly_points=monthly_points,
        history=history
    )
@app.route("/get_mechanics/<int:branch_id>")
def get_mechanics(branch_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""SELECT id, username FROM usersWHERE role='mechanic'
        AND branch_id=?
        AND status='approved'
        AND is_active=1
    """, (branch_id,))

    mechanics = [dict(row) for row in c.fetchall()]
    conn.close()
    return fetch(mechanics)
if __name__ == "__main__":
    app.run(debug=True)
