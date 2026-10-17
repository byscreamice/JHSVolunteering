from flask import Flask, render_template
app = Flask(__name__)

@app.route("/")
def home():
    opportunities = [
        {"title": "Test volunteer event", "date": "Oct 25", "link": "https://google.com"}
    ]
    return render_template("index.html", opportunities=opportunities)
