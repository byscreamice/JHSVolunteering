import os
import sqlite3
from datetime import date
from flask import Flask, render_template, request, redirect, session

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
        cur.execute("CREATE TABLE IF NOT EXISTS opportunities (id SERIAL PRIMARY KEY, title TEXT NOT NULL, date TEXT NOT NULL, link TEXT NOT NULL, description TEXT)")
    else:
        cur.execute("CREATE TABLE IF NOT EXISTS opportunities (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, date TEXT NOT NULL, link TEXT NOT NULL, description TEXT)")
    conn.commit()
    cur.close()
    conn.close()

init_db()

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
    title, date_val, link, description = (
        request.form["title"],
        request.form["date"],
        request.form["link"],
        request.form["description"]
    )
    execute_db(
        "INSERT INTO opportunities (title, date, link, description) VALUES (?, ?, ?, ?)",
        (title, date_val, link, description)
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
    title, date_val, link, description = (
        request.form["title"],
        request.form["date"],
        request.form["link"],
        request.form["description"]
    )
    execute_db(
        "UPDATE opportunities SET title = ?, date = ?, link = ?, description = ? WHERE id = ?",
        (title, date_val, link, description, id)
    )
    return redirect("/admin")