import json
import sqlite3
import threading
from contextlib import contextmanager


class SessionStore:
    """Persistent conversation history. Current turn evidence is always re-read, never inherited."""
    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(path), check_same_thread=False)
        self.lock = threading.RLock()
        self.session_locks = {}
        with self.connection:
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.connection.execute("CREATE TABLE IF NOT EXISTS turns (id INTEGER PRIMARY KEY, session TEXT, mode TEXT, payload TEXT)")

    @contextmanager
    def serial(self, session_id):
        with self.lock:
            lock = self.session_locks.setdefault(session_id, threading.RLock())
        with lock:
            yield

    def history(self, session_id, mode=None):
        with self.lock:
            if mode:
                rows = self.connection.execute("SELECT payload FROM turns WHERE session=? AND mode=? ORDER BY id DESC LIMIT 10", (session_id, mode)).fetchall()
            else:
                rows = self.connection.execute("SELECT payload FROM turns WHERE session=? ORDER BY id DESC LIMIT 10", (session_id,)).fetchall()
        return [json.loads(row[0]) for row in reversed(rows)]

    def append(self, answer):
        with self.lock, self.connection:
            self.connection.execute("INSERT INTO turns(session,mode,payload) VALUES(?,?,?)",
                                    (answer.session_id, answer.mode, answer.model_dump_json()))

    def close(self):
        self.connection.close()

