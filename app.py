import sqlite3
from flask import Flask, render_template, request, redirect
app = Flask(__name__)

@app.route("/")
def home():
   conn: sqlite3.Connection = sqlite3.connect("database.db")
   conn.row_factory = sqlite3.Row
   opportunities = conn.execute("SELECT * FROM opportunities").fetchall()
   conn.close()
   return render_template("index.html", opportunities=opportunities)

@app.route("/admin")
def admin():
  conn = sqlite3.connect("database.db")
  conn.row_factory = sqlite3.Row
  opportunities = conn.execute("SELECT * FROM opportunities").fetchall()
  conn.close()
  return render_template("admin.html", opportunities=opportunities)
@app.route("/add", methods=["POST"])
def add(): 
   title, date, link = (
      request.form["title"],
      request.form["date"],
      request.form["link"]
   )
   conn = sqlite3.connect("database.db")
   conn.execute(
      "INSERT INTO opportunities (title, date, link) VALUES (?, ?, ?)",
      (title, date, link)
   )
   conn.commit()
   conn.close()
   return redirect("/admin")
@app.route("/login", methods=["POST"])
def login():
   if request.form.get("password") == "admin123":
      return redirect("/admin")
   else:
      return "Incorrect password"
@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
  conn = sqlite3.connect("database.db")
  conn.execute("DELETE FROM opportunities WHERE id = ?", (id,))
  conn.commit()
  conn.close()
  return redirect("/admin")