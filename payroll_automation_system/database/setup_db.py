"""
Database Setup Script
Creates the SQLite database and all tables from schema.sql
"""
import os
import sys
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "database", "payroll.db")
SQL_PATH = os.path.join(BASE_DIR, "database", "schema.sql")

sys.path.insert(0, BASE_DIR)


def setup_database():
    print("=" * 60)
    print("  PAYROLL AUTOMATION SYSTEM - DATABASE SETUP")
    print("=" * 60)

    # Remove old DB if exists
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"[✓] Removed existing database")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    with open(SQL_PATH, "r") as f:
        sql_script = f.read()

    conn.executescript(sql_script)
    conn.commit()
    conn.close()

    print(f"[✓] Database created at: {DB_PATH}")
    print(f"[✓] All tables, views, indexes & triggers created")

    # Verify
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    cur.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table','view','index','trigger') ORDER BY type, name")
    objects = cur.fetchall()

    tables   = [o[0] for o in objects if o[1] == 'table']
    views    = [o[0] for o in objects if o[1] == 'view']
    indexes  = [o[0] for o in objects if o[1] == 'index']
    triggers = [o[0] for o in objects if o[1] == 'trigger']

    print(f"\n  Tables   ({len(tables)}): {', '.join(tables)}")
    print(f"  Views    ({len(views)}): {', '.join(views)}")
    print(f"  Indexes  ({len(indexes)}): {', '.join(indexes)}")
    print(f"  Triggers ({len(triggers)}): {', '.join(triggers)}")

    conn.close()
    print("\n[✓] Database setup complete!\n")


if __name__ == "__main__":
    setup_database()
