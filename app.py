from flask import Flask, request, redirect, session, render_template_string, jsonify
import sqlite3
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = "CHANGE_THIS_SECRET_KEY"
DB = "smart_campus.db"

# ============================================================
# DATABASEpython app.py
# ============================================================

def get_db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = get_db()

    con.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        user_id TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        user_id TEXT NOT NULL,
        entry_type TEXT NOT NULL,
        action TEXT NOT NULL,
        time TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        location TEXT NOT NULL,
        message TEXT NOT NULL,
        status TEXT NOT NULL,
        time TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        subject TEXT NOT NULL,
        message TEXT NOT NULL,
        status TEXT NOT NULL,
        time TEXT NOT NULL
    );
    """)

    con.execute(
        "INSERT OR IGNORE INTO users(name,user_id,password,role) VALUES(?,?,?,?)",
        ("Campus Administrator", "admin", "admin123", "admin")
    )

    con.execute(
        "INSERT OR IGNORE INTO users(name,user_id,password,role) VALUES(?,?,?,?)",
        ("Demo Student", "student", "student123", "student")
    )

    con.commit()
    con.close()


def now():
    return datetime.now().strftime("%d-%m-%Y %H:%M:%S")


def today_prefix():
    return datetime.now().strftime("%d-%m-%Y")


# ============================================================
# AUTHENTICATION
# ============================================================

def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return func(*args, **kwargs)
    return wrapper


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            return redirect("/")
        return func(*args, **kwargs)
    return wrapper


# ============================================================
# MAIN UI
# ============================================================

BASE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>Smart & Secure Campus</title>

    <!-- Map library -->
    <link
      rel="stylesheet"
      href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
    />

    <!-- QR scanner library -->
    <script src="https://unpkg.com/html5-qrcode" defer></script>

    <style>
        :root {
            --bg: #080d18;
            --panel: #101827;
            --panel2: #141f32;
            --border: #25344d;
            --text: #eef4ff;
            --muted: #91a0b8;
            --green: #3ddc97;
            --red: #ff5d73;
            --blue: #66a3ff;
            --yellow: #f5c451;
            --purple: #a98cff;
        }

        * { box-sizing: border-box; }

        body {
            margin: 0;
            font-family: Inter, Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
        }

        button, input, textarea, select {
            font: inherit;
        }

        a {
            color: inherit;
            text-decoration: none;
        }

        .layout {
            min-height: 100vh;
            display: flex;
        }

        .sidebar {
            width: 250px;
            position: fixed;
            left: 0;
            top: 0;
            bottom: 0;
            padding: 22px 15px;
            background: #0d1524;
            border-right: 1px solid var(--border);
            z-index: 20;
        }

        .brand {
            padding: 12px;
            font-size: 21px;
            font-weight: 800;
            margin-bottom: 24px;
        }

        .brand span {
            color: var(--green);
        }

        .nav a {
            display: block;
            padding: 13px 14px;
            border-radius: 10px;
            margin: 5px 0;
            color: var(--muted);
        }

        .nav a:hover,
        .nav a.active {
            background: #1a2942;
            color: white;
        }

        .nav .danger-link {
            color: #ff8494;
        }

        .main {
            margin-left: 250px;
            width: calc(100% - 250px);
            padding: 28px;
        }

        .topbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 15px;
            margin-bottom: 25px;
        }

        .topbar h1 {
            margin: 0;
            font-size: 29px;
        }

        .subtitle {
            color: var(--muted);
            margin-top: 5px;
        }

        .profile {
            background: var(--panel);
            border: 1px solid var(--border);
            padding: 10px 14px;
            border-radius: 10px;
            white-space: nowrap;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 17px;
        }

        .grid-2 {
            display: grid;
            grid-template-columns: 1.4fr 1fr;
            gap: 17px;
            margin-top: 17px;
        }

        .card {
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 12px 35px rgba(0,0,0,.15);
        }

        .stat {
            min-height: 140px;
        }

        .label {
            color: var(--muted);
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: .7px;
        }

        .number {
            font-size: 32px;
            font-weight: 800;
            margin: 14px 0 5px;
        }

        .green { color: var(--green); }
        .red { color: var(--red); }
        .blue { color: var(--blue); }
        .yellow { color: var(--yellow); }
        .purple { color: var(--purple); }

        .status-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 13px 0;
            border-bottom: 1px solid var(--border);
        }

        .status-row:last-child {
            border-bottom: 0;
        }

        .pill {
            border-radius: 30px;
            padding: 5px 10px;
            font-size: 11px;
            font-weight: 800;
        }

        .online {
            background: #123a2b;
            color: var(--green);
        }

        .warning {
            background: #3b3115;
            color: var(--yellow);
        }

        .offline {
            background: #3a1821;
            color: var(--red);
        }

        .alert {
            padding: 13px;
            margin: 9px 0;
            border-left: 4px solid var(--red);
            background: #24151d;
            border-radius: 8px;
        }

        .activity {
            padding: 13px 0;
            border-bottom: 1px solid var(--border);
        }

        .activity:last-child {
            border-bottom: 0;
        }

        .muted {
            color: var(--muted);
        }

        .form-card {
            max-width: 700px;
        }

        label {
            display: block;
            color: var(--muted);
            margin-top: 12px;
            margin-bottom: 5px;
        }

        input, textarea, select {
            width: 100%;
            padding: 12px;
            color: white;
            background: #0a1220;
            border: 1px solid #2b3b56;
            border-radius: 9px;
            outline: none;
        }

        input:focus, textarea:focus, select:focus {
            border-color: var(--blue);
        }

        textarea {
            min-height: 120px;
            resize: vertical;
        }

        button, .button {
            border: 0;
            border-radius: 9px;
            padding: 11px 17px;
            background: var(--green);
            color: #07130d;
            font-weight: 800;
            cursor: pointer;
            display: inline-block;
        }

        button:hover, .button:hover {
            transform: translateY(-1px);
            opacity: .92;
        }

        .danger-button {
            background: var(--red);
            color: white;
        }

        .secondary-button {
            background: #273751;
            color: white;
        }

        .big-sos {
            width: 100%;
            padding: 17px;
            font-size: 18px;
            margin-top: 8px;
        }

        #map {
            height: 350px;
            border-radius: 12px;
            overflow: hidden;
        }

        .camera {
            height: 190px;
            background:
                linear-gradient(135deg, #101b2c, #050a12);
            border-radius: 12px;
            border: 1px solid var(--border);
            display: grid;
            place-items: center;
            color: var(--muted);
            position: relative;
            overflow: hidden;
        }

        .camera:after {
            content: "LIVE";
            position: absolute;
            top: 10px;
            right: 10px;
            color: var(--red);
            font-weight: 900;
            font-size: 12px;
        }

        .camera-grid {
            display: grid;
            grid-template-columns: repeat(2,1fr);
            gap: 12px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th, td {
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid var(--border);
        }

        th {
            color: var(--muted);
            font-size: 13px;
        }

        .empty {
            padding: 18px 0;
            color: var(--muted);
        }

        .chart {
            display: flex;
            align-items: end;
            gap: 12px;
            height: 180px;
            padding-top: 15px;
        }

        .bar {
            flex: 1;
            background: linear-gradient(#66a3ff, #3ddc97);
            border-radius: 7px 7px 2px 2px;
            min-height: 8px;
            position: relative;
        }

        .bar span {
            position: absolute;
            bottom: -22px;
            width: 100%;
            text-align: center;
            color: var(--muted);
            font-size: 11px;
        }

        .scan-box {
            max-width: 500px;
            margin-top: 15px;
        }

        .toast {
            position: fixed;
            right: 25px;
            bottom: 25px;
            background: #17243a;
            border: 1px solid var(--border);
            padding: 14px 18px;
            border-radius: 10px;
            display: none;
            z-index: 100;
        }

        @media(max-width: 1000px) {
            .grid { grid-template-columns: repeat(2, 1fr); }
            .grid-2 { grid-template-columns: 1fr; }
        }

        @media(max-width: 700px) {
            .sidebar {
                position: static;
                width: 100%;
                height: auto;
            }

            .layout {
                display: block;
            }

            .main {
                margin-left: 0;
                width: 100%;
                padding: 18px;
            }

            .grid {
                grid-template-columns: 1fr;
            }

            .topbar {
                align-items: flex-start;
                flex-direction: column;
            }

            .camera-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>

<body>

<div class="layout">

    <aside class="sidebar">

        <div class="brand">
            🏫 Smart <span>&</span> Secure
        </div>

        <nav class="nav">

            <a href="/" class="{{ 'active' if page == 'dashboard' else '' }}">
                ▦ Dashboard
            </a>

            <a href="/entry" class="{{ 'active' if page == 'entry' else '' }}">
                🪪 Campus Entry
            </a>

            <a href="/scan" class="{{ 'active' if page == 'scan' else '' }}">
                📷 QR Scanner
            </a>

            <a href="/sos" class="{{ 'active' if page == 'sos' else '' }}">
                🚨 Emergency SOS
            </a>

            <a href="/complaint" class="{{ 'active' if page == 'complaint' else '' }}">
                📝 Report Issue
            </a>

            <a href="/map" class="{{ 'active' if page == 'map' else '' }}">
                📍 Campus Map
            </a>

            {% if session.get('role') == 'admin' %}
            <a href="/admin" class="{{ 'active' if page == 'admin' else '' }}">
                ⚙️ Admin Panel
            </a>
            {% endif %}

            <a href="/logout" class="danger-link">
                ↪ Logout
            </a>

        </nav>

    </aside>


    <main class="main">

        <div class="topbar">

            <div>
                <h1>{{ title }}</h1>
                <div class="subtitle">
                    Smart campus security control center
                </div>
            </div>

            <div class="profile">
                👤 {{ session.get('name') }}
                · {{ session.get('role') }}
            </div>

        </div>

        {{ content | safe }}

    </main>

</div>

<div id="toast" class="toast"></div>

<script>
function toast(message) {
    const t = document.getElementById("toast");
    t.innerText = message;
    t.style.display = "block";
    setTimeout(() => t.style.display = "none", 3000);
}
</script>

</body>
</html>
"""


def page(content, title, active):
    return render_template_string(
        BASE,
        content=content,
        title=title,
        page=active
    )


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    error = ""

    if request.method == "POST":

        user_id = request.form["user_id"].strip()
        password = request.form["password"]

        con = get_db()

        user = con.execute(
            "SELECT * FROM users WHERE user_id=? AND password=?",
            (user_id, password)
        ).fetchone()

        con.close()

        if user:

            session["user_id"] = user["user_id"]
            session["name"] = user["name"]
            session["role"] = user["role"]

            return redirect("/")

        error = "Invalid user ID or password."

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>Smart Campus Login</title>

        <style>
            * { box-sizing:border-box; }

            body {
                margin:0;
                min-height:100vh;
                display:grid;
                place-items:center;
                font-family:Arial,sans-serif;
                color:white;
                background:
                    radial-gradient(circle at top,#19365c,#070c16 65%);
            }

            .box {
                width:390px;
                max-width:92%;
                background:#111b2d;
                border:1px solid #293b58;
                padding:32px;
                border-radius:18px;
                box-shadow:0 25px 70px #0008;
            }

            h1 { margin-top:0; }

            .muted { color:#91a0b8; }

            input {
                width:100%;
                padding:13px;
                margin:7px 0 15px;
                border-radius:9px;
                border:1px solid #2b3b56;
                background:#091220;
                color:white;
            }

            button {
                width:100%;
                padding:13px;
                border:0;
                border-radius:9px;
                background:#3ddc97;
                font-weight:bold;
                cursor:pointer;
            }

            .error {
                color:#ff6577;
                margin-bottom:12px;
            }

            .demo {
                margin-top:20px;
                color:#91a0b8;
                font-size:13px;
                line-height:1.7;
            }
        </style>
    </head>

    <body>

        <div class="box">

            <h1>🏫 Smart & Secure Campus</h1>

            <p class="muted">
                Sign in to the campus security system
            </p>

            {% if error %}
                <div class="error">{{ error }}</div>
            {% endif %}

            <form method="post">

                <label>User ID</label>
                <input
                    name="user_id"
                    placeholder="Enter user ID"
                    required
                >

                <label>Password</label>
                <input
                    type="password"
                    name="password"
                    placeholder="Enter password"
                    required
                >

                <button>Sign In</button>

            </form>

            <div class="demo">
                <b>Demo accounts</b><br>
                Admin: admin / admin123<br>
                Student: student / student123
            </div>

        </div>

    </body>
    </html>
    """, error=error)


@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/")
@login_required
def dashboard():

    con = get_db()

    today = today_prefix()

    today_entries = con.execute(
        "SELECT COUNT(*) AS c FROM entries WHERE time LIKE ?",
        (today + "%",)
    ).fetchone()["c"]

    total_entries = con.execute(
        "SELECT COUNT(*) AS c FROM entries"
    ).fetchone()["c"]

    active_alerts = con.execute(
        "SELECT * FROM alerts WHERE status='ACTIVE' ORDER BY id DESC LIMIT 5"
    ).fetchall()

    recent_entries = con.execute(
        "SELECT * FROM entries ORDER BY id DESC LIMIT 7"
    ).fetchall()

    open_complaints = con.execute(
        "SELECT COUNT(*) AS c FROM complaints WHERE status='OPEN'"
    ).fetchone()["c"]

    con.close()

    content = render_template_string("""
    <div class="grid">

        <div class="card stat">
            <div class="label">Campus Status</div>
            <div class="number green">● SECURE</div>
            <div class="muted">Core systems online</div>
        </div>

        <div class="card stat">
            <div class="label">Today's Entries</div>
            <div class="number blue">{{ today_entries }}</div>
            <div class="muted">Campus movements</div>
        </div>

        <div class="card stat">
            <div class="label">Active Emergencies</div>
            <div class="number red">{{ active_alerts|length }}</div>
            <div class="muted">Requires attention</div>
        </div>

        <div class="card stat">
            <div class="label">Open Reports</div>
            <div class="number yellow">{{ open_complaints }}</div>
            <div class="muted">Reported issues</div>
        </div>

    </div>


    <div class="grid-2">

        <div class="card">

            <h2>🛡️ Security Systems</h2>

            <div class="status-row">
                <span>📹 CCTV Network</span>
                <span class="pill online">ONLINE</span>
            </div>

            <div class="status-row">
                <span>🚪 Entry Monitoring</span>
                <span class="pill online">ACTIVE</span>
            </div>

            <div class="status-row">
                <span>🚨 Emergency System</span>
                <span class="pill online">READY</span>
            </div>

            <div class="status-row">
                <span>💡 Smart Lighting</span>
                <span class="pill online">ONLINE</span>
            </div>

            <div class="status-row">
                <span>📡 Campus Network</span>
                <span class="pill online">ONLINE</span>
            </div>

        </div>


        <div class="card">

            <h2>🚨 Active Alerts</h2>

            {% for a in active_alerts %}

                <div class="alert">

                    <b>{{ a["name"] }}</b>

                    <br>

                    📍 {{ a["location"] }}

                    <br>

                    <span class="muted">
                        {{ a["message"] }}
                        · {{ a["time"] }}
                    </span>

                </div>

            {% else %}

                <div class="empty">
                    ✓ No active emergency alerts.
                </div>

            {% endfor %}

        </div>

    </div>


    <div class="grid-2">

        <div class="card">

            <h2>📹 CCTV Monitoring</h2>

            <div class="camera-grid">

                <div class="camera">
                    Camera 01 · Main Gate
                </div>

                <div class="camera">
                    Camera 02 · Block A
                </div>

                <div class="camera">
                    Camera 03 · Parking
                </div>

                <div class="camera">
                    Camera 04 · Library
                </div>

            </div>

            <p class="muted">
                Demo camera panels. Connect your actual CCTV/RTSP system
                separately for live video.
            </p>

        </div>


        <div class="card">

            <h2>📊 Entry Overview</h2>

            <div class="chart">

                {% set values = [35, 55, 42, 72, 62, 88, 76] %}

                {% for value in values %}

                    <div
                        class="bar"
                        style="height:{{ value }}%"
                        title="{{ value }}%"
                    >
                        <span>{{ loop.index }}</span>
                    </div>

                {% endfor %}

            </div>

            <p class="muted">
                Illustrative activity chart for the current dashboard.
            </p>

        </div>

    </div>


    <div class="card" style="margin-top:17px">

        <h2>👥 Recent Campus Activity</h2>

        {% for e in recent_entries %}

            <div class="activity">

                👤 <b>{{ e["name"] }}</b>
                · {{ e["user_id"] }}
                · {{ e["entry_type"] }}
                · <span class="muted">{{ e["action"] }}</span>

                <div class="muted">
                    {{ e["time"] }}
                </div>

            </div>

        {% else %}

            <div class="empty">
                No campus activity recorded yet.
            </div>

        {% endfor %}

    </div>
    """,
    today_entries=today_entries,
    total_entries=total_entries,
    active_alerts=active_alerts,
    open_complaints=open_complaints,
    recent_entries=recent_entries)

    return page(content, "Dashboard", "dashboard")


# ============================================================
# CAMPUS ENTRY
# ============================================================

@app.route("/entry", methods=["GET", "POST"])
@login_required
def entry():

    if request.method == "POST":

        name = request.form["name"].strip()
        user_id = request.form["user_id"].strip()
        entry_type = request.form["entry_type"]
        action = request.form["action"]

        con = get_db()

        con.execute(
            """
            INSERT INTO entries
            (name,user_id,entry_type,action,time)
            VALUES (?,?,?,?,?)
            """,
            (name, user_id, entry_type, action, now())
        )

        con.commit()
        con.close()

        return redirect("/")

    content = """
    <div class="card form-card">

        <h2>🪪 Campus Entry</h2>

        <p class="muted">
            Record a student, staff member or visitor entering or leaving.
        </p>

        <form method="post">

            <label>Full Name</label>
            <input
                name="name"
                placeholder="Enter full name"
                required
            >

            <label>ID / Roll Number</label>
            <input
                name="user_id"
                placeholder="Example: CS101"
                required
            >

            <label>Person Type</label>

            <select name="entry_type">
                <option>Student</option>
                <option>Staff</option>
                <option>Visitor</option>
            </select>

            <label>Action</label>

            <select name="action">
                <option>ENTRY</option>
                <option>EXIT</option>
            </select>

            <button>✓ Record Activity</button>

        </form>

    </div>
    """

    return page(content, "Campus Entry", "entry")


# ============================================================
# QR SCANNER
# ============================================================

@app.route("/scan")
@login_required
def scan():

    content = """
    <div class="card form-card">

        <h2>📷 QR Campus Entry</h2>

        <p class="muted">
            Scan a campus ID QR code. For this prototype, the QR code
            should contain a student/staff ID such as <b>student</b>.
        </p>

        <div id="reader" class="scan-box"></div>

        <p id="scan-result" class="muted">
            Camera scanner is ready when browser permission is granted.
        </p>

        <form method="post" action="/scan-entry">

            <input
                id="scanned-id"
                name="user_id"
                placeholder="Or enter scanned ID manually"
                required
            >

            <button>✓ Verify & Record Entry</button>

        </form>

    </div>

    <script>
    window.addEventListener("load", function () {

        if (typeof Html5Qrcode === "undefined") {
            document.getElementById("scan-result").innerText =
                "QR library is still loading. You can enter the ID manually.";
            return;
        }

        const scanner = new Html5Qrcode("reader");

        scanner.start(
            { facingMode: "environment" },
            { fps: 10, qrbox: 220 },

            function(decodedText) {

                document.getElementById("scanned-id").value = decodedText;

                document.getElementById("scan-result").innerText =
                    "QR detected: " + decodedText;

                scanner.stop();

            },

            function(errorMessage) {
                // Normal scanning messages are ignored.
            }
        ).catch(function(error) {

            document.getElementById("scan-result").innerText =
                "Camera unavailable. Use manual ID entry.";
        });

    });
    </script>
    """

    return page(content, "QR Scanner", "scan")


@app.route("/scan-entry", methods=["POST"])
@login_required
def scan_entry():

    user_id = request.form["user_id"].strip()

    con = get_db()

    user = con.execute(
        "SELECT * FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()

    if user:

        con.execute(
            """
            INSERT INTO entries
            (name,user_id,entry_type,action,time)
            VALUES (?,?,?,?,?)
            """,
            (
                user["name"],
                user["user_id"],
                user["role"],
                "QR ENTRY",
                now()
            )
        )

    else:

        con.execute(
            """
            INSERT INTO entries
            (name,user_id,entry_type,action,time)
            VALUES (?,?,?,?,?)
            """,
            (
                "QR User",
                user_id,
                "Student",
                "QR ENTRY",
                now()
            )
        )

    con.commit()
    con.close()

    return redirect("/")


# ============================================================
# EMERGENCY SOS
# ============================================================

@app.route("/sos", methods=["GET", "POST"])
@login_required
def sos():

    if request.method == "POST":

        location = request.form["location"].strip()
        message = request.form["message"].strip()

        con = get_db()

        con.execute(
            """
            INSERT INTO alerts
            (name,location,message,status,time)
            VALUES (?,?,?,?,?)
            """,
            (
                session["name"],
                location,
                message,
                "ACTIVE",
                now()
            )
        )

        con.commit()
        con.close()

        return redirect("/")

    content = """
    <div class="card form-card">

        <h2>🚨 Emergency SOS</h2>

        <p class="muted">
            Use this only for a genuine emergency. The alert will
            appear on the campus dashboard.
        </p>

        <form method="post">

            <label>Emergency Location</label>

            <input
                name="location"
                placeholder="Example: Block A, Room 204"
                required
            >

            <label>Emergency Details</label>

            <textarea
                name="message"
                placeholder="Describe what happened..."
                required
            ></textarea>

            <button class="danger-button big-sos">
                🚨 SEND EMERGENCY ALERT
            </button>

        </form>

    </div>
    """

    return page(content, "Emergency SOS", "sos")


# ============================================================
# COMPLAINTS
# ============================================================

@app.route("/complaint", methods=["GET", "POST"])
@login_required
def complaint():

    if request.method == "POST":

        subject = request.form["subject"].strip()
        message = request.form["message"].strip()

        con = get_db()

        con.execute(
            """
            INSERT INTO complaints
            (name,subject,message,status,time)
            VALUES (?,?,?,?,?)
            """,
            (
                session["name"],
                subject,
                message,
                "OPEN",
                now()
            )
        )

        con.commit()
        con.close()

        return redirect("/")

    content = """
    <div class="card form-card">

        <h2>📝 Report Campus Issue</h2>

        <p class="muted">
            Report broken equipment, lighting, cleanliness,
            suspicious activity or other campus issues.
        </p>

        <form method="post">

            <label>Subject</label>

            <input
                name="subject"
                placeholder="Example: Broken street light"
                required
            >

            <label>Details</label>

            <textarea
                name="message"
                placeholder="Describe the problem..."
                required
            ></textarea>

            <button>
                Submit Report
            </button>

        </form>

    </div>
    """

    return page(content, "Report Issue", "complaint")


# ============================================================
# CAMPUS MAP
# ============================================================

@app.route("/map")
@login_required
def campus_map():

    content = """
    <div class="card">

        <h2>📍 Campus Safety Map</h2>

        <p class="muted">
            Demo campus map. Replace the coordinates below with
            your actual campus coordinates.
        </p>

        <div id="map"></div>

    </div>

    <script
      src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js">
    </script>

    <script>

        // Demo coordinates.
        // Change these to your campus latitude and longitude.
        const campusLat = 28.3670;
        const campusLng = 79.4304;

        const map = L.map("map").setView(
            [campusLat, campusLng],
            16
        );

        L.tileLayer(
            "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            {
                attribution: "&copy; OpenStreetMap contributors"
            }
        ).addTo(map);

        L.marker([campusLat, campusLng])
            .addTo(map)
            .bindPopup("<b>🏫 Main Campus</b>")
            .openPopup();

        L.marker([campusLat + 0.0010, campusLng])
            .addTo(map)
            .bindPopup("🚨 Security Office");

        L.marker([campusLat, campusLng + 0.0010])
            .addTo(map)
            .bindPopup("🏥 First Aid");

        L.marker([campusLat - 0.0010, campusLng])
            .addTo(map)
            .bindPopup("🚪 Main Gate");

    </script>
    """

    return page(content, "Campus Map", "map")


# ============================================================
# ADMIN PANEL
# ============================================================

@app.route("/admin")
@login_required
@admin_required
def admin():

    con = get_db()

    alerts = con.execute(
        "SELECT * FROM alerts ORDER BY id DESC LIMIT 50"
    ).fetchall()

    complaints = con.execute(
        "SELECT * FROM complaints ORDER BY id DESC LIMIT 50"
    ).fetchall()

    users = con.execute(
        "SELECT name,user_id,role FROM users ORDER BY id"
    ).fetchall()

    con.close()

    content = render_template_string("""
    <div class="card">

        <h2>⚙️ Admin Control Center</h2>

        <p class="muted">
            Monitor emergency alerts, campus reports and registered users.
        </p>

        <h3>🚨 Emergency Alerts</h3>

        <table>

            <tr>
                <th>Name</th>
                <th>Location</th>
                <th>Message</th>
                <th>Status</th>
                <th>Time</th>
            </tr>

            {% for a in alerts %}

            <tr>
                <td>{{ a["name"] }}</td>
                <td>{{ a["location"] }}</td>
                <td>{{ a["message"] }}</td>
                <td>{{ a["status"] }}</td>
                <td>{{ a["time"] }}</td>
            </tr>

            {% else %}

            <tr>
                <td colspan="5">No alerts.</td>
            </tr>

            {% endfor %}

        </table>


        <h3 style="margin-top:35px">
            📝 Issue Reports
        </h3>

        <table>

            <tr>
                <th>Name</th>
                <th>Subject</th>
                <th>Message</th>
                <th>Status</th>
                <th>Time</th>
            </tr>

            {% for c in complaints %}

            <tr>
                <td>{{ c["name"] }}</td>
                <td>{{ c["subject"] }}</td>
                <td>{{ c["message"] }}</td>
                <td>{{ c["status"] }}</td>
                <td>{{ c["time"] }}</td>
            </tr>

            {% else %}

            <tr>
                <td colspan="5">No reports.</td>
            </tr>

            {% endfor %}

        </table>


        <h3 style="margin-top:35px">
            👥 Registered Users
        </h3>

        <table>

            <tr>
                <th>Name</th>
                <th>User ID</th>
                <th>Role</th>
            </tr>

            {% for u in users %}

            <tr>
                <td>{{ u["name"] }}</td>
                <td>{{ u["user_id"] }}</td>
                <td>{{ u["role"] }}</td>
            </tr>

            {% endfor %}

        </table>

    </div>
    """, alerts=alerts, complaints=complaints, users=users)

    return page(content, "Admin Panel", "admin")


# ============================================================
# SIMPLE JSON API FOR LIVE DASHBOARD DATA
# ============================================================

@app.route("/api/stats")
@login_required
def stats():

    con = get_db()

    today = today_prefix()

    result = {
        "today_entries": con.execute(
            "SELECT COUNT(*) c FROM entries WHERE time LIKE ?",
            (today + "%",)
        ).fetchone()["c"],

        "total_entries": con.execute(
            "SELECT COUNT(*) c FROM entries"
        ).fetchone()["c"],

        "active_alerts": con.execute(
            "SELECT COUNT(*) c FROM alerts WHERE status='ACTIVE'"
        ).fetchone()["c"],

        "open_reports": con.execute(
            "SELECT COUNT(*) c FROM complaints WHERE status='OPEN'"
        ).fetchone()["c"]
    }

    con.close()

    return jsonify(result)


# ============================================================
# START SERVER
# ============================================================

init_db()

if __name__ == "__main__":

    print()
    print("==============================================")
    print("       SMART & SECURE CAMPUS")
    print("==============================================")
    print("Dashboard : http://127.0.0.1:5000")
    print("Admin     : admin / admin123")
    print("Student   : student / student123")
    print("Database  : smart_campus.db")
    print("==============================================")
    print()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
