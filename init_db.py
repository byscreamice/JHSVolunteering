import os
import sqlite3

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL:
    import psycopg2
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS opportunities (id SERIAL PRIMARY KEY, title TEXT NOT NULL, date TEXT NOT NULL, link TEXT NOT NULL, description TEXT)")
    conn.commit()
    cur.close()
    conn.close()
else:
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS opportunities (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, date TEXT NOT NULL, link TEXT NOT NULL, description TEXT)")
    conn.commit()
    cur.close()
    conn.close()
