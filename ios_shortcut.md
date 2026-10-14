# notes_bridge · iOS Shortcut

Posílání hlasových i textových poznámek z iPhonu (Action Button / Siri / Share Sheet) přímo do Telegram bota, který pak ukládá vše do `notes.json` a zrcadlí do `AI_Workspace/AI_Brain/Inbox/notes.md`.

> **Bezpečnost:** token bota nikdy neukládejte do Shortcutu v plaintextu. Postup níže ho drží v Telegramu samotném (pošle ho první zprávou přes Deep Link / BotFather `/setprivacy`), nebo použijte proměnnou prostředí uloženou v **Settings → Shortcuts → Advanced → Allow Running Scripts** a načtenou přes `Get Dictionary Value`.

---

## 1. Co musíte mít připravené

| Položka | Kde ji získat |
|---|---|
| `TELEGRAM_BOT_TOKEN` | `@BotFather` → `/newbot` |
| `TELEGRAM_CHAT_ID` | odešlete botovi zprávu, otevřete `https://api.telegram.org/bot<TOKEN>/getUpdates` → `chat.id` |
| `TELEGRAM_THREAD_ID` (jen u skupin s fóry) | stejný `getUpdates` → `message_thread_id` (volitelné) |

Hodnoty si poznamenejte; v Shortcutu se odkazují jako **proměnné** nebo **Dictionary** (viz krok 5).

---

## 2. Vytvoření hlavního Shortcutu

1. Otevřete **Shortcuts** (Zkratky) na iPhonu.
2. `+` → **Create Shortcut** → pojmenujte `Poslat Poznámku`.
4. Přidejte akce v tomto pořadí (viz krok 3–6).

---

## 3. Vstup: text nebo hlas

### Varianta A — textová poznámka
- Akce: **Ask for Input**
  - Prompt: `Co chceš zapsat?`
  - Input type: `Text`
  - Variable: `note`

### Varianta B — hlasová poznámka
- Akce: **Dictate Text**
  - Wait until: `Stopped`
  - Variable: `note`

### Varianta C — share sheet (cokoli z jiné appky)
- V nastavení Shortcutu zapněte: **Show in Share Sheet** + **Accepts: Text, URLs**.
- Sdílený text přichází jako `Shortcut Input` → přidejte **Get Dictionary Value** / `Set Variable` `note` = `Shortcut Input`.

---

## 4. Volitelně: chat ID a thread ID

Pokud ukládáte konfiguraci do **Dictionary** (doporučeno):

1. Akce: **Dictionary**
   - Přidejte 3 klíče:
     - `token`   → `<TELEGRAM_BOT_TOKEN>`
     - `chat_id` → `<TELEGRAM_CHAT_ID>`
     - `thread_id` → `<TELEGRAM_THREAD_ID>` nebo prázdné
2. Akce: **Get Dictionary Value** pro každý klíč → proměnné `token`, `chat_id`, `thread_id`.

> Tip: místo Dictionary můžete použít **Text** akci s JSON a **Get Dictionary from JSON** — viz `Get Contents of URL` akce níže.

---

## 5. Sestavení URL pro Telegram Bot API

1. Akce: **Text**
   - Content:
     ```
     https://api.telegram.org/bot%token%/sendMessage
     ```
   - Variable: `url`
2. Akce: **Dictionary** s klíči pro POST tělo:
   - `chat_id` → proměnná `chat_id`
   - `text`    → proměnná `note`
   - `message_thread_id` → proměnná `thread_id` (jen pokud není prázdná)

---

## 6. Odeslání

1. Akce: **Get Contents of URL**
   - URL: proměnná `url`
   - Method: `POST`
   - Request Body: `JSON` → vyberte Dictionary z kroku 5
   - Headers: `Content-Type: application/json` (přidá se automaticky)
   - Allow Untrusted Hosts: **OFF** (odesíláte na telegram.org)
2. Akce: **Show Notification**:
   - Text: ✅ `Poznámka odeslána`

---

## 7. Přiřazení na Action Button

1. **Settings → Action Button**.
2. Swipe na **Shortcut** → vyberte `Poslat Poznámku`.
3. (Volitelně) **Double Press / Triple Press** pro různé varianty (text / hlas / share).

Pro **Siri**: **Settings → Siri & Search → Poslat Poznámku** → přiřaďte frázi, např. `„Hej Siri, poznamenej si to"`.

---

## 8. Kontrola

Po prvním spuštění ověřte, že bridge poznámku přijal:

```bash
python bridge.py --once
```

nebo pro trvalý provoz:

```bash
python bridge.py --daemon
```

Výsledek najdete v:
- `notes.json`
- `AI_Brain/Inbox/notes.md` (ve vašem Obsidian vaultu)
- a widgetu `widget.html`.

Pokud se nic neukládá, spusťte `--discover` — vypíše nejnovější `chat_id` a `thread_id`, které porovnejte s hodnotami ve Shortcutu.