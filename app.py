import io
import base64
import os
import sqlite3
from datetime import date
from flask import Flask, render_template, request, redirect, session, send_from_directory

app = Flask(__name__)
app.secret_key = "jhs_volunteering_secret_key"

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def get_db():
    if DATABASE_URL:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    if DATABASE_URL:
        cur.execute("CREATE TABLE IF NOT EXISTS spaces (id SERIAL PRIMARY KEY, name TEXT NOT NULL, code TEXT NOT NULL UNIQUE)")
        conn.commit()
        cur.execute("CREATE TABLE IF NOT EXISTS opportunities (id SERIAL PRIMARY KEY, title TEXT NOT NULL, date TEXT NOT NULL, link TEXT NOT NULL, description TEXT, image TEXT, space_id INTEGER)")
        conn.commit()
        try:
            cur.execute("ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS image TEXT")
            conn.commit()
        except Exception:
            conn.rollback()
        try:
            cur.execute("ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS space_id INTEGER")
            conn.commit()
        except Exception:
            conn.rollback()
    else:
        cur.execute("CREATE TABLE IF NOT EXISTS spaces (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, code TEXT NOT NULL UNIQUE)")
        conn.commit()
        cur.execute("CREATE TABLE IF NOT EXISTS opportunities (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, date TEXT NOT NULL, link TEXT NOT NULL, description TEXT, image TEXT, space_id INTEGER)")
        conn.commit()
        try:
            cur.execute("ALTER TABLE opportunities ADD COLUMN image TEXT")
            conn.commit()
        except Exception:
            pass
        try:
            cur.execute("ALTER TABLE opportunities ADD COLUMN space_id INTEGER")
            conn.commit()
        except Exception:
            pass
    cur.close()
    conn.close()

init_db()

def format_date_str(val):
    try:
        d = date.fromisoformat(str(val))
        day = d.day
        if 11 <= day <= 13:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return f"{d.strftime('%B')} {day}{suffix}, {d.year}"
    except Exception:
        return val

@app.template_filter("format_date")
def format_date_filter(val):
    return format_date_str(val)

def process_image(req):
    file = req.files.get("image_file")
    if file and file.filename:
        try:
            try:
                from PIL import Image
                img = Image.open(file.stream)
                img.thumbnail((800, 800))
                buf = io.BytesIO()
                if img.mode in ("RGBA", "P"):
                    img.save(buf, format="PNG", optimize=True)
                    mime = "image/png"
                else:
                    img = img.convert("RGB")
                    img.save(buf, format="JPEG", quality=85, optimize=True)
                    mime = "image/jpeg"
                b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                return f"data:{mime};base64,{b64}"
            except Exception:
                file.stream.seek(0)
                data = file.read()
                if data:
                    mime = file.content_type or "image/jpeg"
                    b64 = base64.b64encode(data).decode("utf-8")
                    return f"data:{mime};base64,{b64}"
        except Exception:
            pass
    return ""

def execute_db(query, params=(), fetch=False):
    conn = get_db()
    if DATABASE_URL:
        query = query.replace("?", "%s")
    cur = conn.cursor()
    cur.execute(query, params)
    result = None
    if fetch:
        result = cur.fetchall()
    else:
        conn.commit()
    cur.close()
    conn.close()
    return result

@app.route("/favicon.ico")
def favicon():
    return send_from_directory(os.path.join(app.root_path, "static"), "favicon.ico", mimetype="image/vnd.microsoft.icon")

@app.route("/manifest.json")
def manifest():
    return send_from_directory(os.path.join(app.root_path, "static"), "manifest.json", mimetype="application/manifest+json")

@app.route("/")
def home():
    execute_db("DELETE FROM opportunities WHERE date < ?", (str(date.today()),))
    space_id = session.get("space_id")
    current_space = None
    if space_id:
        rows = execute_db("SELECT * FROM spaces WHERE id = ?", (space_id,), fetch=True)
        if rows:
            current_space = rows[0]
        else:
            session.pop("space_id", None)
    if current_space:
        opportunities = execute_db(
            "SELECT * FROM opportunities WHERE space_id = ? ORDER BY date ASC",
            (current_space["id"],),
            fetch=True
        )
    else:
        opportunities = []
    return render_template("index.html", opportunities=opportunities, current_space=current_space)

@app.route("/join-space", methods=["POST"])
def join_space():
    code = request.form.get("code", "").strip().upper()
    if not code:
        return redirect("/?space_error=1")
    rows = execute_db("SELECT * FROM spaces WHERE UPPER(code) = ?", (code,), fetch=True)
    if rows:
        session["space_id"] = rows[0]["id"]
        return redirect("/")
    return redirect("/?space_error=1")

@app.route("/leave-space", methods=["GET", "POST"])
def leave_space():
    session.pop("space_id", None)
    return redirect("/")

@app.route("/admin")
def admin():
    if not session.get("is_admin"):
        return redirect("/?error=auth")
    execute_db("DELETE FROM opportunities WHERE date < ?", (str(date.today()),))
    admin_space_id = session.get("admin_space_id")
    admin_space = None
    if admin_space_id:
        rows = execute_db("SELECT * FROM spaces WHERE id = ?", (admin_space_id,), fetch=True)
        if rows:
            admin_space = rows[0]
        else:
            session.pop("admin_space_id", None)
    if admin_space:
        opportunities = execute_db(
            "SELECT * FROM opportunities WHERE space_id = ? ORDER BY date ASC",
            (admin_space["id"],),
            fetch=True
        )
    else:
        opportunities = []
    return render_template(
        "admin.html",
        admin_space=admin_space,
        opportunities=opportunities,
        today=date.today()
    )

@app.route("/admin/access-space", methods=["POST"])
def admin_access_space():
    if not session.get("is_admin"):
        return redirect("/?error=auth")
    code = request.form.get("code", "").strip().upper()
    if not code:
        return redirect("/admin?access_err=1")
    rows = execute_db("SELECT * FROM spaces WHERE UPPER(code) = ?", (code,), fetch=True)
    if rows:
        session["admin_space_id"] = rows[0]["id"]
        return redirect("/admin")
    return redirect("/admin?access_err=1")

@app.route("/admin/lock-space")
def admin_lock_space():
    session.pop("admin_space_id", None)
    return redirect("/admin")

@app.route("/spaces/add", methods=["POST"])
def add_space():
    if not session.get("is_admin"):
        return redirect("/?error=auth")
    name = request.form.get("name", "").strip()
    code = request.form.get("code", "").strip().upper()
    if name and code:
        existing = execute_db("SELECT id FROM spaces WHERE UPPER(code) = ?", (code,), fetch=True)
        if existing:
            return redirect("/admin?space_err=exists")
        execute_db("INSERT INTO spaces (name, code) VALUES (?, ?)", (name, code))
        new_row = execute_db("SELECT id FROM spaces WHERE UPPER(code) = ?", (code,), fetch=True)
        if new_row:
            session["admin_space_id"] = new_row[0]["id"]
    return redirect("/admin")

@app.route("/spaces/edit/<int:id>", methods=["POST"])
def edit_space(id):
    if not session.get("is_admin"):
        return redirect("/?error=auth")
    name = request.form.get("name", "").strip()
    code = request.form.get("code", "").strip().upper()
    if name and code:
        existing = execute_db("SELECT id FROM spaces WHERE UPPER(code) = ? AND id != ?", (code, id), fetch=True)
        if existing:
            return redirect("/admin?space_err=exists")
        execute_db("UPDATE spaces SET name = ?, code = ? WHERE id = ?", (name, code, id))
        session["admin_space_id"] = id
    return redirect("/admin")

@app.route("/spaces/delete/<int:id>", methods=["POST"])
def delete_space(id):
    if not session.get("is_admin"):
        return redirect("/?error=auth")
    execute_db("DELETE FROM opportunities WHERE space_id = ?", (id,))
    execute_db("DELETE FROM spaces WHERE id = ?", (id,))
    if session.get("admin_space_id") == id:
        session.pop("admin_space_id", None)
    if session.get("space_id") == id:
        session.pop("space_id", None)
    return redirect("/admin")

@app.route("/login", methods=["POST"])
def login():
    if request.form.get("password") == "admin123":
        session["is_admin"] = True
        return redirect("/admin")
    else:
        return redirect("/?error=1")

@app.route("/logout")
def logout():
    session.pop("is_admin", None)
    session.pop("admin_space_id", None)
    return redirect("/")

@app.route("/add", methods=["POST"])
def add(): 
    if not session.get("is_admin"):
        return redirect("/?error=auth")
    title = request.form["title"]
    date_val = request.form["date"]
    link = request.form["link"]
    description = request.form["description"]
    space_id_raw = request.form.get("space_id", "").strip()
    space_id = int(space_id_raw) if space_id_raw.isdigit() else session.get("admin_space_id")
    image_data = process_image(request)
    execute_db(
        "INSERT INTO opportunities (title, date, link, description, image, space_id) VALUES (?, ?, ?, ?, ?, ?)",
        (title, date_val, link, description, image_data, space_id)
    )
    return redirect("/admin")

@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    if not session.get("is_admin"):
        return redirect("/?error=auth")
    execute_db("DELETE FROM opportunities WHERE id = ?", (id,))
    return redirect("/admin")

@app.route("/edit/<int:id>", methods=["POST"])
def edit(id):
    if not session.get("is_admin"):
        return redirect("/?error=auth")
    title = request.form["title"]
    date_val = request.form["date"]
    link = request.form["link"]
    description = request.form["description"]
    space_id_raw = request.form.get("space_id", "").strip()
    if space_id_raw.isdigit():
        space_id = int(space_id_raw)
    else:
        space_id = session.get("admin_space_id")
    
    existing = execute_db("SELECT image, space_id FROM opportunities WHERE id = ?", (id,), fetch=True)
    current_image = existing[0]["image"] if existing and existing[0]["image"] else ""
    if space_id is None and existing and existing[0]["space_id"]:
        space_id = existing[0]["space_id"]

    if request.form.get("remove_image") == "1":
        image_data = ""
    else:
        file = request.files.get("image_file")
        if file and file.filename:
            image_data = process_image(request)
        else:
            image_data = current_image

    execute_db(
        "UPDATE opportunities SET title = ?, date = ?, link = ?, description = ?, image = ?, space_id = ? WHERE id = ?",
        (title, date_val, link, description, image_data, space_id, id)
    )
    return redirect("/admin")
