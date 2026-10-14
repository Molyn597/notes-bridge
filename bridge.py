"""notes_bridge: Telegram -> local notes bridge.

Polls Telegram Bot API getUpdates, stores notes in notes.json and mirrors
them as a markdown checklist in AI_Brain/Inbox/notes.md.

Credentials are loaded from OS env (preferred) or Windows registry
HKCU\\Environment (fallback). Nothing is hardcoded.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_DIR = Path(__file__).resolve().parent
NOTES_JSON = PROJECT_DIR / "notes.json"
INBOX_MD = Path(os.environ.get("OBSIDIAN_INBOX_PATH", str(Path.home() / "AI_Workspace" / "AI_Brain" / "Inbox" / "notes.md")))
POLL_TIMEOUT = 25          # Telegram long-poll seconds
POLL_INTERVAL = 1          # delay between polls in --daemon mode
STATE_FILE = PROJECT_DIR / ".state.json"


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------
def _load_from_registry(name: str) -> Optional[str]:
    """Read a value from HKCU\\Environment. Returns None if not on Windows
    or if the value is missing."""
    try:
        import winreg  # type: ignore
    except ImportError:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as k:
            value, _ = winreg.QueryValueEx(k, name)
            if value:
                return str(value)
    except (OSError, FileNotFoundError):
        return None
    return None


def get_credential(name: str, aliases: tuple[str, ...] = ()) -> Optional[str]:
    """Env first, then registry. Supports aliases."""
    for key in (name, *aliases):
        val = os.environ.get(key)
        if val and val.strip():
            return val.strip()
        reg_val = _load_from_registry(key)
        if reg_val and reg_val.strip():
            return reg_val.strip()
    return None


# ---------------------------------------------------------------------------
# Telegram API
# ---------------------------------------------------------------------------
def api_call(token: str, method: str, params: Optional[Dict[str, Any]] = None,
             timeout: int = 35) -> Dict[str, Any]:
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(params or {}, doseq=True).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        return {"ok": False, "error": str(exc)}


def get_updates(token: str, offset: Optional[int], timeout: int) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {"timeout": timeout, "allowed_updates": ["message"]}
    if offset is not None:
        params["offset"] = offset
    result = api_call(token, "getUpdates", params, timeout=timeout + 10)
    if not result.get("ok"):
        return []
    return result.get("result") or []


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def load_notes() -> List[Dict[str, Any]]:
    if NOTES_JSON.exists():
        try:
            with NOTES_JSON.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except (json.JSONDecodeError, OSError):
            pass
    return []


def save_notes(notes: List[Dict[str, Any]]) -> None:
    PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = NOTES_JSON.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)
    tmp.replace(NOTES_JSON)


def load_state() -> Dict[str, Any]:
    if STATE_FILE.exists():
        try:
            with STATE_FILE.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"offset": None}


def save_state(state: Dict[str, Any]) -> None:
    PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    tmp.replace(STATE_FILE)


def mirror_markdown(notes: List[Dict[str, Any]]) -> None:
    INBOX_MD.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = [
        "# Notes Inbox",
        "",
        "_Auto-mirrored from `notes_bridge/bridge.py`._",
        "",
    ]
    if not notes:
        lines.append("- _Žádné poznámky._")
    else:
        for n in notes:
            box = "x" if n.get("done") else " "
            ts = n.get("created_at", "")
            text = (n.get("text") or "").replace("\n", " ")
            src = n.get("source", "")
            suffix = f"  _(via {src}, {ts})_" if src else f"  _({ts})_"
            lines.append(f"- [{box}] {text}{suffix}")
    INBOX_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Core & Parser
# ---------------------------------------------------------------------------
import re

def parse_items_from_text(raw_text: str) -> List[str]:
    """If text contains numbered or bulleted list items (e.g. 1. foo\n2. bar),
    split into individual items. Otherwise return [raw_text]."""
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if not lines:
        return []

    list_pattern = re.compile(r"^\s*(?:\d+[\.\)]|[-*•–])\s+(.+)$")
    matches = [list_pattern.match(l) for l in lines]
    matched_count = sum(1 for m in matches if m is not None)

    if matched_count >= 2:
        items: List[str] = []
        for line, m in zip(lines, matches):
            if m:
                items.append(m.group(1).strip())
            elif items:
                items[-1] += " " + line
            else:
                items.append(line)
        return items

    return [raw_text]


def extract_notes(update: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Pull usable text payloads out of an update. If the message contains
    a numbered list (1., 2., ...) or bullet points, splits into individual tasks."""
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return []
    chat = msg.get("chat") or {}
    expected_chat = get_credential("TELEGRAM_CHAT_ID")
    if expected_chat and str(chat.get("id")) != str(expected_chat):
        return []

    expected_thread = get_credential("NOTES_TELEGRAM_THREAD_ID", ("TELEGRAM_THREAD_ID",))
    msg_thread = msg.get("message_thread_id")
    if expected_thread and msg_thread is not None and str(msg_thread) != str(expected_thread):
        return []

    raw_text = msg.get("text") or msg.get("caption")
    if not raw_text:
        return []
    raw_text = str(raw_text).strip()
    if not raw_text:
        return []

    msg_id = msg.get("message_id")
    sender = (msg.get("from") or {}).get("username") or (msg.get("from") or {}).get("first_name") or "telegram"
    created_at = datetime.fromtimestamp(
        msg.get("date", int(time.time())), tz=timezone.utc
    ).isoformat(timespec="seconds")

    items = parse_items_from_text(raw_text)
    entries: List[Dict[str, Any]] = []
    for idx, item in enumerate(items, 1):
        note_id = f"tg_{msg_id}_{idx}" if len(items) > 1 else f"tg_{msg_id}"
        entries.append({
            "id": note_id,
            "update_id": update["update_id"],
            "message_id": msg_id,
            "item_index": idx,
            "thread_id": msg_thread,
            "from": sender,
            "text": item,
            "created_at": created_at,
            "done": False,
            "source": "telegram",
        })
    return entries


def discover(token: str, chat_id: Optional[str]) -> Dict[str, Any]:
    """One-shot: fetch latest updates and print thread/message IDs so the
    user can populate TELEGRAM_THREAD_ID / TELEGRAM_CHAT_ID."""
    updates = get_updates(token, offset=None, timeout=0)
    if not updates:
        print("[discover] No updates found. Send a message to the bot first.")
        return {"updates": []}

    summary: List[Dict[str, Any]] = []
    for u in updates[-10:]:
        msg = u.get("message") or {}
        chat = msg.get("chat") or {}
        summary.append({
            "update_id": u.get("update_id"),
            "chat_id": chat.get("id"),
            "chat_title": chat.get("title") or chat.get("username"),
            "message_id": msg.get("message_id"),
            "thread_id": msg.get("message_thread_id"),
            "is_topic": msg.get("is_topic_message"),
            "text_preview": (msg.get("text") or msg.get("caption") or "")[:80],
        })

    print("[discover] latest updates:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if chat_id is None and summary:
        first_chat = summary[-1]["chat_id"]
        if first_chat is not None:
            print(f"\n[discover] suggested TELEGRAM_CHAT_ID={first_chat}")
    threads = {s["thread_id"] for s in summary if s["thread_id"] is not None}
    if threads:
        print(f"[discover] observed thread IDs: {sorted(threads)}")
    return {"updates": summary}


def poll_once(token: str, dry_run: bool = False,
               verbose: bool = True) -> List[Dict[str, Any]]:
    state = load_state()
    offset = state.get("offset")
    updates = get_updates(token, offset=offset, timeout=POLL_TIMEOUT)
    if not updates:
        if verbose:
            print("[poll] no updates")
        return []

    notes = load_notes()
    next_offset = offset
    new_entries: List[Dict[str, Any]] = []

    for u in updates:
        next_offset = max(next_offset or 0, u["update_id"] + 1)
        entries = extract_notes(u)
        for entry in entries:
            # dedupe by note id
            if any(n.get("id") == entry["id"] for n in notes):
                continue
            notes.append(entry)
            new_entries.append(entry)
            if verbose:
                print(f"[poll] + [{entry['id']}] {entry['text'][:80]}")

    state["offset"] = next_offset
    if not dry_run:
        save_notes(notes)
        save_state(state)
        if new_entries:
            mirror_markdown(notes)
    else:
        if verbose:
            print(f"[dry-run] would store {len(new_entries)} new, "
                  f"offset -> {next_offset}")
    return new_entries


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="notes_bridge: Telegram -> local notes")
    grp = p.add_mutually_exclusive_group()
    grp.add_argument("--once", action="store_true",
                     help="poll once and exit")
    grp.add_argument("--daemon", action="store_true",
                     help="poll forever")
    grp.add_argument("--discover", action="store_true",
                     help="inspect latest updates (chat/thread IDs) and exit")
    p.add_argument("--dry-run", action="store_true",
                   help="do not write notes.json / .state.json / notes.md")
    args = p.parse_args(argv)

    token = get_credential("NOTES_TELEGRAM_BOT_TOKEN", ("TELEGRAM_BOT_TOKEN", "JOBS_TELEGRAM_BOT_TOKEN"))
    chat_id = get_credential("TELEGRAM_CHAT_ID")
    thread_id = get_credential("NOTES_TELEGRAM_THREAD_ID", ("TELEGRAM_THREAD_ID",))

    if not token:
        print("[bridge] ERROR: TELEGRAM_BOT_TOKEN not found in env or "
              "HKCU\\Environment.", file=sys.stderr)
        return 2

    if verbose := True:
        print(f"[bridge] chat_id={chat_id} thread_id={thread_id} "
              f"dry_run={args.dry_run}")

    if args.discover:
        discover(token, chat_id)
        return 0

    if args.daemon:
        print("[bridge] daemon mode (Ctrl-C to stop)")
        while True:
            try:
                poll_once(token, dry_run=args.dry_run)
            except KeyboardInterrupt:
                print("\n[bridge] stopped")
                return 0
            except Exception as exc:  # pragma: no cover
                print(f"[bridge] error: {exc}", file=sys.stderr)
            time.sleep(POLL_INTERVAL)

    # default = --once
    poll_once(token, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())