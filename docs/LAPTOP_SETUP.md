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
| `checklist.md` | Personal Already / Planned / Bonus roadmap (local only) |
| `transfer/` | Laptop handoff with secrets + transcripts |
| `data/*.sqlite` | Rate-limit, analytics, and session-memory DBs |
| `data/chroma/`, live cache | Runtime indexes/caches |
| `.venv/`, `web/node_modules/`, `web/dist/` | Local install / build output |

Before every push: `git status` — if `.env` or a SQLite file appears, stop.

**Operator analytics page:** set a long random `OPERATOR_DASHBOARD_KEY` in `.env` (and the same in Railway Variables for production). Bookmark:

- Local: `http://127.0.0.1:8000/operator/analytics?key=YOUR_KEY`
- Production: `https://www.poesiosa.net/operator/analytics?key=YOUR_KEY`

Empty key = page disabled. Local and production each keep their own SQLite file (no sync). On Railway, attach a volume at `/app/data` so data survives redeploys. Do not put these links on public visitor docs.

## 3. Transfer bundle (optional but recommended)

On your **main PC**, regenerate the handoff folder:

```powershell
.\scripts\export_transfer.ps1
```

Copy the whole `transfer/` folder to the laptop (USB, OneDrive, etc.). It is **gitignored** — not on GitHub.

On the laptop, place `transfer/` inside the cloned repo and read in order:

1. **`transfer/CONTINUATION.md`** — pick-up brief (next steps, vLLM status, recent ship list)
2. **`transfer/checklist.md`** — copy to repo-root `checklist.md` (still gitignored)
3. **`transfer/HANDOFF.md`** — paths and quick start
4. **`transfer/PROJECT_OVERVIEW.txt`** — deeper technical overview if needed

## 4. Run locally

```powershell
.\start.bat
```

- App: http://127.0.0.1:8000/
- Docs: http://127.0.0.1:8000/docs/

Optional wiki index: `poe-ingest` (not required if `RETRIEVAL_MODE=live` in `.env`).

## 5. Cursor on the laptop

1. Open the `Siosa` folder in Cursor.
2. Start a **new** chat (old chats are not synced automatically; transcripts are under `transfer/cursor/agent-transcripts/` for reference).
3. Prompt example: *Read `transfer/CONTINUATION.md`, `transfer/checklist.md`, and `docs/ARCHITECTURE.md`; continue with the tool registry and Cargo/PoEDB.*
4. Paste **User rules** from `transfer/cursor/user-rules.md` into Cursor **Settings → Rules** if you filled them in on the main PC.
5. Ensure git author for this repo is `cent664` / `cent664@users.noreply.github.com` (not the unrelated `niv@users.noreply.github.com` noreply).

## 6. Production (unchanged)

Railway Variables and https://www.poesiosa.net/ are configured in the Railway dashboard, not on the laptop.

## Regenerate transfer bundle

```powershell
.\scripts\export_transfer.ps1
```
