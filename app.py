import sqlite3
from flask import Flask, render_template, request, redirect, session
from datetime import date
app = Flask(__name__)
app.secret_key = "jhs_volunteering_secret_key"

@app.route("/")
def home():
   conn = sqlite3.connect("database.db")
   conn.row_factory = sqlite3.Row
   conn.execute("DELETE FROM opportunities WHERE date < date('now')")
   conn.commit()
   opportunities = conn.execute("SELECT * FROM opportunities").fetchall()
   conn.close()
   return render_template("index.html", opportunities=opportunities)

@app.route("/admin")
def admin():
  if not session.get("is_admin"):
    return redirect("/?error=auth")
  conn = sqlite3.connect("database.db")
  conn.row_factory = sqlite3.Row
  opportunities = conn.execute("SELECT * FROM opportunities").fetchall()
  conn.close()
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
   conn = sqlite3.connect("database.db")
   conn.execute(
      "INSERT INTO opportunities (title, date, link, description) VALUES (?, ?, ?, ?)",
      (title, date_val, link, description)
   )
   conn.commit()
   conn.close()
   return redirect("/admin")

@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
  if not session.get("is_admin"):
    return redirect("/?error=auth")
  conn = sqlite3.connect("database.db")
  conn.execute("DELETE FROM opportunities WHERE id = ?", (id,))
  conn.commit()
  conn.close()
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
  conn = sqlite3.connect("database.db")
  conn.execute(
      "UPDATE opportunities SET title = ?, date = ?, link = ?, description = ? WHERE id = ?",
      (title, date_val, link, description, id)
  )
  conn.commit()
  conn.close()
  return redirect("/admin")