import sqlite3


conn = sqlite3.connect("database.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS opportunities (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, date TEXT NOT NULL, link TEXT NOT NULL, description TEXT)")
cursor.execute("INSERT INTO opportunities (title, date, link, description) VALUES (?, ?, ?, ?)", ("Testing Opportunity", "Oct 25", "https://google.com", "This is a test opportunity."))
conn.commit()
conn.close()
