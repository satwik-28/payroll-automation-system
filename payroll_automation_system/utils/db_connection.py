"""
Database connection utility for Payroll Automation System
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "payroll.db")


def get_connection():
    """Return a database connection with row_factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def execute_query(query: str, params: tuple = (), fetchone: bool = False):
    """Execute a SELECT query and return results."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        return cur.fetchone() if fetchone else cur.fetchall()


def execute_write(query: str, params: tuple = ()):
    """Execute INSERT/UPDATE/DELETE and return last row id."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        return cur.lastrowid


def execute_many(query: str, params_list: list):
    """Execute bulk INSERT/UPDATE."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.executemany(query, params_list)
        conn.commit()
        return cur.rowcount


def execute_script(sql_script: str):
    """Execute a multi-statement SQL script."""
    with get_connection() as conn:
        conn.executescript(sql_script)
        conn.commit()
