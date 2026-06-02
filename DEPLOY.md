# Deploy to Railway (conference demo)

Public URL for QR codes; your laptop can stay off during the event.

## What you do in Railway (one time, ~15 min)

1. Sign in at [railway.app](https://railway.app) with GitHub.
2. **Upgrade to Hobby** ($5/mo) and add a **payment method** (required for always-on; no sleep).
3. **New Project** → **Deploy from GitHub repo** → choose **`cent664/Siosa`** → branch **`main`**.
4. Railway detects [`Dockerfile`](Dockerfile) and [`railway.toml`](railway.toml) automatically.
5. Open the service → **Settings**:
   - **Resources:** set **4 GB RAM** and **~2 vCPU** before the first deploy (default RAM often OOMs during startup; healthcheck will fail).
   - **Networking:** click **Generate domain** → you get `https://something.up.railway.app`.
6. **Variables** tab — paste the [production variables](#required-variables) below (secrets from your local `.env`, never commit them).
7. Wait for **Deploy** to finish (first build ~5–15 min).
8. Open `https://YOUR-DOMAIN.up.railway.app/health` — should return `"status":"ok"`. Railway probes `/health/live` during deploy (see [`railway.toml`](railway.toml)).
9. Open the root URL, run one **Ask**, then create your **QR code** pointing to `https://YOUR-DOMAIN.up.railway.app/`.

## Required variables

Copy into Railway **Variables** (replace secrets with your real keys).

**Judges are not a Railway product** — `JUDGE_PROVIDER` chooses which **your** LLM API runs optional quality scores on each Ask (only when `INLINE_EVAL=true`). For the booth, use `INLINE_EVAL=false` and still set `JUDGE_PROVIDER=claude` so `/health` is not misleading.

**Do not use Ollama on Railway:** delete or override any `JUDGE_PROVIDER=ollama`, `POE_PROVIDER_MODE=ollama`, or `OLLAMA_*` variables (local dev defaults from `.env.example`).

**Do not set** a custom `PORT` — Railway injects it; the container uses it via [`scripts/start_api.sh`](scripts/start_api.sh).

### Claude + GPT-4 in the UI (recommended)

Both keys let attendees switch providers in the web UI. Initial startup default is Claude; switching to GPT-4 in the UI updates the runtime judge automatically.

```env
POE_PROVIDER_MODE=claude
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
JUDGE_PROVIDER=claude
INLINE_EVAL=false
RETRIEVAL_MODE=live
POE_DATA_DIR=/app/data
```

### Claude only

```env
POE_PROVIDER_MODE=claude
JUDGE_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6
RETRIEVAL_MODE=live
INLINE_EVAL=false
POE_DATA_DIR=/app/data
```

Optional tuning (defaults are fine):

```env
LIVE_WIKI_MAX_PAGES=5
LIVE_WIKI_MAX_SEARCH_QUERIES=4
RERANK_TOP_N=5
PLANNER_MAX_RETRIEVE_SUBTASKS=4
RETRIEVAL_REFINE_ENABLED=false
LOG_LEVEL=INFO
```

Use **`INLINE_EVAL=false`** at the booth for faster, cheaper responses. Set back to `true` when testing quality locally.

Do **not** set `OLLAMA_*` on Railway (no Ollama on the server).

## Redeploy checklist

After changing RAM or variables, or pushing code to `main`:

1. **Variables** — Use a block above; remove `ollama` / `OLLAMA_*` / custom `PORT`.
2. **Resources** — **4 GB RAM** and **~2 vCPU** is enough after a successful deploy (8 GB is safe but costs more).
3. **Push** — `git push origin main` triggers a rebuild (includes `/health/live` in [`railway.toml`](railway.toml)).
4. **Verify** — Deploy logs show `Uvicorn running on http://0.0.0.0:...`; then:
   - `https://YOUR-DOMAIN.up.railway.app/health/live` → `{"status":"ok"}`
   - `/health` → `"status":"ok"`, `judge_provider` is `claude` (not `ollama`)
   - Root URL → one **Ask** returns a real answer (not stub text)
   - Or run: `.\scripts\verify_railway_deploy.ps1 -BaseUrl "https://YOUR-DOMAIN.up.railway.app"`

## Pushing updates (2 Jun – 7 Jun)

1. Edit code locally.
2. `git push origin main`
3. Railway rebuilds automatically (watch **Deployments**).
4. After deploy, run one test Ask on the public URL (warms the app).

QR code URL **does not change** if you keep the same Railway domain.

## Billing (rough)

- **Railway:** $5/mo Hobby + RAM/CPU while the service runs (~$12–25 for a busy week at 4 GB).
- **Anthropic/OpenAI:** per Ask, separate from Railway — see usage dashboards.

Delete the Railway service after the conference if you want to stop hosting charges.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Deploy fails: healthcheck / network process | Set **4 GB RAM** (default often OOMs). Check deploy logs for `OOMKilled` or exit **137**. Do not set a custom `PORT` variable. |
| Deploy log: `python-multipart` / Form data requires | Fixed in `pyproject.toml` — rebuild after pulling latest `main`. |
| Build fails on memory | Increase build resources in Railway or retry |
| Service crashes on Ask | Raise RAM to 4 GB |
| 502 / timeout on first Ask | Normal once — model load + wiki fetch; try again |
| Works locally, fails on Railway | Check `ANTHROPIC_API_KEY` in Variables, not only in local `.env` |
| Health OK but stub answers | Set `POE_PROVIDER_MODE=claude` and API key in Variables |
| `/health` shows `judge_provider: ollama` | Set `JUDGE_PROVIDER=claude` (or `gpt4`); remove `ollama` from Variables |

## What the agent cannot do for you

- Create your Railway account or enter card details — **you** must do that in the browser.
- Paste API keys into Railway — copy from your local `.env` into **Variables**.

After you have a public URL, share it if you want help verifying health and a test query.
