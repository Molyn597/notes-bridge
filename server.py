"""notes_bridge: Standalone Desktop Server & Telegram Sync Daemon.

Serves the Kognita-style widget locally on port 7892, provides real-time REST API,
and runs a background Telegram polling thread for 0-token live sync.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict

from bridge import (
    NOTES_JSON,
    POLL_INTERVAL,
    get_credential,
    load_notes,
    mirror_markdown,
    poll_once,
    save_notes,
)

PORT = 7892
PROJECT_DIR = Path(__file__).resolve().parent


class NotesHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROJECT_DIR), **kwargs)

    def do_GET(self):
        if self.path == "/api/notes":
            notes = load_notes()
            data = json.dumps(notes, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache, no-store")
            self.end_headers()
            self.wfile.write(data)
            return

        if self.path == "/" or self.path == "":
            self.path = "/widget.html"
        return super().do_GET()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            payload = json.loads(body)
        except Exception:
            payload = {}

        if self.path == "/api/toggle":
            note_id = payload.get("id")
            done = payload.get("done")
            notes = load_notes()
            modified = False
            for n in notes:
                if n.get("id") == note_id:
                    n["done"] = bool(done)
                    modified = True
                    break
            if modified:
                save_notes(notes)
                mirror_markdown(notes)
            data = json.dumps({"ok": True, "modified": modified}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(data)
            return

        if self.path == "/api/add":
            text = (payload.get("text") or "").strip()
            if text:
                notes = load_notes()
                new_note = {
                    "id": f"pc_{int(time.time()*1000)}",
                    "text": text,
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "done": False,
                    "source": "pc",
                }
                notes.insert(0, new_note)
                save_notes(notes)
                mirror_markdown(notes)
                data = json.dumps({"ok": True, "note": new_note}).encode("utf-8")
            else:
                data = json.dumps({"ok": False, "error": "empty"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(data)
            return

        self.send_error(404, "Endpoint not found")

    def log_message(self, format, *args):
        # Silence routine request logging
        pass


def run_telegram_worker():
    """Background polling thread for Telegram updates."""
    token = get_credential("NOTES_TELEGRAM_BOT_TOKEN", ("TELEGRAM_BOT_TOKEN", "JOBS_TELEGRAM_BOT_TOKEN"))
    if not token:
        print("[daemon] NOTES_TELEGRAM_BOT_TOKEN not found; skipping TG sync.")
        return

    print("[daemon] Telegram sync thread active.")
    while True:
        try:
            poll_once(token, dry_run=False, verbose=False)
        except Exception as exc:
            print(f"[daemon] poll error: {exc}", file=sys.stderr)
        time.sleep(POLL_INTERVAL)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    t = threading.Thread(target=run_telegram_worker, daemon=True)
    t.start()

    server = HTTPServer(("127.0.0.1", port), NotesHandler)
    print(f"[server] Notes Bridge Desktop server running at http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[server] Shutting down.")


if __name__ == "__main__":
    main()
