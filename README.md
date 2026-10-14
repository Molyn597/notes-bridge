# ⚡ Notes Bridge

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()
[![LLM Cost](https://img.shields.io/badge/LLM%20Cost-0%20CZK%20%2F%20Zero--Waste-brightgreen.svg)]()
[![UI Design](https://img.shields.io/badge/Design-Kognita%20Systems%20Minimalism-black.svg)]()

> **Ultra-lightweight, zero-token note & task bridge from iPhone (via Telegram) to Windows PC, rendered in a high-craft Kognita Systems Swiss minimalist UI and mirrored to Obsidian.**

---

## 💡 Overview

**Notes Bridge** is a low-latency, privacy-first ingestion bridge designed to eliminate friction when capturing thoughts on mobile and acting on them on desktop:
- Capture notes or dictate voice tasks on iPhone via **Action Button** / **Apple Shortcuts** / **Telegram Forum Topics**.
- Sync instantly to your PC over the Telegram Bot API without cloud subscriptions or paid LLM inference.
- Render in a clean standalone desktop app featuring the **Kognita Systems** design language (Space Grotesk, Inter, Fira Code, 40px grid).
- Automatically break down numbered/bulleted lists into individual interactive checklist items.
- Live-mirror checklist tasks directly into your **Obsidian AI Brain** vault (`notes.md`).

---

## 🚀 Capabilities

| Capability | Description |
| :--- | :--- |
| **📱 Mobile-to-Desktop Ingestion** | Instant capture via Telegram Bot API with forum topic/thread routing. Zero third-party cloud apps. |
| **0️⃣ Zero-Waste / Zero-Token** | Runs 100% on standard Python libraries without invoking expensive LLM loops for simple text capture. |
| **🎨 Kognita Systems UI** | Swiss typographic minimalism, 40px structural grid, Space Grotesk headings, Fira Code metadata. |
| **☑️ Smart List Parser** | Automatically parses multi-item lists (`1.`, `2.`, `-`, `*`) into distinct, checkable task items. |
| **🧠 Obsidian Vault Mirror** | Real-time bi-directional sync with Obsidian Markdown checkboxes (`- [ ]`). |
| **🤖 Hermes Orchestration** | Dedicated **"Předat Orchestrátorovi"** button to hand off unresolved tasks directly to AI agents. |

---

## 🏗️ System Architecture

```text
  [ iPhone (iOS Shortcuts / Siri / Action Button) ]
                          │
                          ▼ (HTTPS POST / Telegram Bot API)
  [ Telegram Supergroup Topic: #Notes-Bridge ]
                          │
                          ▼ (Long-poll / 0 tokens)
  [ notes_bridge / server.py (127.0.0.1:7892) ]
          │                               │
          ▼ (JSON State)                  ▼ (Markdown Checklist)
  [ Kognita Desktop Widget ]     [ Obsidian AI_Brain Vault ]
     (widget.html / App Mode)       (Inbox/notes.md)
```

---

## ⚡ Quick Start

### 1. Clone & Configure
```bash
git clone https://github.com/Molyn597/notes-bridge.git
cd notes-bridge
cp .env.example .env
```

### 2. Configure Environment Variables
Set credentials via OS environment variables or `.env`:
```env
NOTES_TELEGRAM_BOT_TOKEN="your_bot_token"
TELEGRAM_CHAT_ID="-100xxxxxxxxxx"
NOTES_TELEGRAM_THREAD_ID="19"
```

### 3. Launch the Application
```bash
# Launch server and frameless standalone window
python start_app.py
```

Or run headless in daemon mode:
```bash
python bridge.py --daemon
```

---

## 📋 CLI Reference (`bridge.py`)

| Flag | Description |
| :--- | :--- |
| `--once` | Run a single poll cycle to fetch pending updates and exit. |
| `--daemon` | Continuous long-polling loop with automatic reconnection. |
| `--discover` | Inspect the latest incoming chat IDs and topic thread IDs. |
| `--dry-run` | Process messages in memory without modifying `notes.json` or Obsidian. |

---

## 🔒 Privacy & Security

- **Zero Plaintext Credentials:** Secrets load strictly from OS environment variables or Windows `HKCU\Environment` registry.
- **Local State:** All notes reside exclusively on your machine in `notes.json` and your local Obsidian vault.
- **No Telemetry / No Tracking:** Zero analytics, cookies, or external calls outside the official Telegram Bot API.

---

## 📄 License

MIT © [Molyn597](https://github.com/Molyn597)
