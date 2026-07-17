# Laptop setup (second machine)

Use this after cloning [https://github.com/cent664/Siosa](https://github.com/cent664/Siosa). GitHub has code and docs; **secrets and Cursor chat context** do not.

## Prerequisites

- **Python 3.11+** and **Node.js LTS** (22+; matches CI/Docker). Install Node if `npm -v` fails:

```powershell
winget install OpenJS.NodeJS.LTS
```

Then close and reopen your terminal. Verify: `node -v` and `npm -v`.

## 1. Clone and install

```powershell
git clone https://github.com/cent664/Siosa.git
cd Siosa
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev,speech]"
cd web
npm install
cd ..
```

## 2. Environment file

**Option A — you copied `transfer/` from your other PC:**

```powershell
copy transfer\env\.env.local.backup .env
```

**Option B — fresh keys:**

```powershell
copy .env.example .env
# Edit .env: ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.
```

Never commit `.env`.

### Secrets & local-only data

Keep these **off GitHub** (already gitignored):

| Path / env | Why |
|------------|-----|
| `.env` | Real API keys and `OPERATOR_DASHBOARD_KEY` |
| `transfer/` | Laptop handoff with secrets |
| `data/*.sqlite` | Rate-limit and operator-analytics DBs (hashed IPs, not full addresses) |
| `data/chroma/`, live cache | Runtime indexes/caches |
| `.venv/`, `web/node_modules/`, `web/dist/` | Local install / build output |

Before every push: `git status` — if `.env` or a SQLite file appears, stop.

**Operator analytics page (local only):** set a long random `OPERATOR_DASHBOARD_KEY` in `.env`, run the app, then bookmark:

`http://127.0.0.1:8000/operator/analytics?key=YOUR_KEY`

Empty key = page disabled. Production profile forces analytics off (page 404s). Do not put this link on public docs.

## 3. Transfer bundle (optional but recommended)

On your **main PC**, regenerate the handoff folder:

```powershell
.\scripts\export_transfer.ps1
```

Copy the whole `transfer/` folder to the laptop (USB, OneDrive, etc.). It is **gitignored** — not on GitHub.

On the laptop, place `transfer/` inside the cloned repo and read **`transfer/PROJECT_OVERVIEW.txt`** first (full technical overview and transfer steps), then `transfer/HANDOFF.md`.

## 4. Run locally

```powershell
.\start.bat
```

- App: http://127.0.0.1:8000/
- Docs: http://127.0.0.1:8000/docs/

Optional wiki index: `poe-ingest` (not required if `RETRIEVAL_MODE=live` in `.env`).

## 5. Cursor on the laptop

1. Open the `Siosa` folder in Cursor.
2. Start a **new** chat (old chats are not synced automatically).
3. Prompt example: *Read `transfer/HANDOFF.md` and `docs/ARCHITECTURE.md`; continue work on the PoE wiki agent.*
4. Paste **User rules** from `transfer/cursor/user-rules.md` into Cursor **Settings → Rules** if you filled them in on the main PC.

## 6. Production (unchanged)

Railway Variables and https://www.poesiosa.net/ are configured in the Railway dashboard, not on the laptop.

## Regenerate transfer bundle

```powershell
.\scripts\export_transfer.ps1
```
