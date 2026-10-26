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
        cur.execute("CREATE TABLE IF NOT EXISTS opportunities (id SERIAL PRIMARY KEY, title TEXT NOT NULL, date TEXT NOT NULL, link TEXT NOT NULL, description TEXT, image TEXT)")
        conn.commit()
        try:
            cur.execute("ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS image TEXT")
            conn.commit()
        except Exception:
            conn.rollback()
    else:
        cur.execute("CREATE TABLE IF NOT EXISTS opportunities (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, date TEXT NOT NULL, link TEXT NOT NULL, description TEXT, image TEXT)")
        conn.commit()
        try:
            cur.execute("ALTER TABLE opportunities ADD COLUMN image TEXT")
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
    opportunities = execute_db("SELECT * FROM opportunities ORDER BY date ASC", fetch=True)
    return render_template("index.html", opportunities=opportunities)

@app.route("/admin")
def admin():
    if not session.get("is_admin"):
        return redirect("/?error=auth")
    opportunities = execute_db("SELECT * FROM opportunities ORDER BY date ASC", fetch=True)
    return render_template("admin.html", opportunities=opportunities, today=date.today())

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
    return redirect("/")

@app.route("/add", methods=["POST"])
def add(): 
    if not session.get("is_admin"):
        return redirect("/?error=auth")
    title = request.form["title"]
    date_val = request.form["date"]
    link = request.form["link"]
    description = request.form["description"]
    image_data = process_image(request)
    execute_db(
        "INSERT INTO opportunities (title, date, link, description, image) VALUES (?, ?, ?, ?, ?)",
        (title, date_val, link, description, image_data)
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
    
    existing = execute_db("SELECT image FROM opportunities WHERE id = ?", (id,), fetch=True)
    current_image = existing[0]["image"] if existing and existing[0]["image"] else ""

    if request.form.get("remove_image") == "1":
        image_data = ""
    else:
        file = request.files.get("image_file")
        if file and file.filename:
            image_data = process_image(request)
        else:
            image_data = current_image

    execute_db(
        "UPDATE opportunities SET title = ?, date = ?, link = ?, description = ?, image = ? WHERE id = ?",
        (title, date_val, link, description, image_data, id)
    )
    return redirect("/admin")
