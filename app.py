import sqlite3
from flask import Flask, render_template
app = Flask(__name__)

@app.route("/")
def home():
   conn: sqlite3.Connection = sqlite3.connect("database.db")
   conn.row_factory = sqlite3.Row
   opportunities = conn.execute("SELECT * FROM opportunities").fetchall()
   conn.close()
   return render_template("index.html", opportunities=opportunities)
