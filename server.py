"""HabitFlow local server with a small SQLite database.

Run from the project folder with: python server.py
Then open: http://127.0.0.1:8000
"""

from __future__ import annotations

import json
import os
import sqlite3
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT
DATABASE = ROOT / "habitflow.db"
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")


def connection() -> sqlite3.Connection:
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def initialize_database() -> None:
    with connection() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS habits (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS journal_entries (
                entry_date TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


class HabitFlowHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND), **kwargs)

    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            return self.send_json({"ok": True, "database": str(DATABASE.name)})
        if path == "/api/config":
            return self.send_json({"googleClientId": GOOGLE_CLIENT_ID})
        if path == "/api/habits":
            with connection() as db:
                rows = db.execute("SELECT data FROM habits ORDER BY updated_at").fetchall()
            return self.send_json([json.loads(row["data"]) for row in rows])
        if path.startswith("/api/journal/"):
            entry_date = path.rsplit("/", 1)[-1]
            with connection() as db:
                row = db.execute("SELECT data FROM journal_entries WHERE entry_date = ?", (entry_date,)).fetchone()
            return self.send_json(json.loads(row["data"]) if row else {})
        if path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            payload = self.read_json()
        except (ValueError, json.JSONDecodeError):
            return self.send_json({"error": "Invalid JSON"}, 400)

        if path == "/api/habits":
            habits = payload.get("habits")
            if not isinstance(habits, list):
                return self.send_json({"error": "habits must be a list"}, 400)
            with connection() as db:
                db.execute("DELETE FROM habits")
                db.executemany(
                    "INSERT INTO habits (id, data) VALUES (?, ?)",
                    [(str(habit.get("id")), json.dumps(habit)) for habit in habits if habit.get("id")],
                )
            return self.send_json({"ok": True, "count": len(habits)})

        if path.startswith("/api/journal/"):
            entry_date = path.rsplit("/", 1)[-1]
            with connection() as db:
                db.execute(
                    "INSERT INTO journal_entries (entry_date, data, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
                    "ON CONFLICT(entry_date) DO UPDATE SET data=excluded.data, updated_at=CURRENT_TIMESTAMP",
                    (entry_date, json.dumps(payload)),
                )
            return self.send_json({"ok": True, "date": entry_date})

        return self.send_json({"error": "Not found"}, 404)


if __name__ == "__main__":
    initialize_database()
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), HabitFlowHandler)
    print(f"HabitFlow running at http://{host}:{port}")
    print(f"SQLite database: {DATABASE}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nHabitFlow stopped.")
    finally:
        server.server_close()
