# Deploy to Railway (conference demo)

Public URL for QR codes; your laptop can stay off during the event. Live site: **https://www.poesiosa.net/**

## What you do in Railway (one time, ~15 min)

1. Sign in at [railway.app](https://railway.app) with GitHub.
2. **Upgrade to Hobby** ($5/mo) and add a **payment method** (required for always-on; no sleep).
3. **New Project** → **Deploy from GitHub repo** → choose **`cent664/Siosa`** → branch **`main`**.
4. Railway detects [`Dockerfile`](Dockerfile) and [`railway.toml`](railway.toml) automatically.
5. Open the service → **Settings**:
   - **Resources:** set **4 GB RAM** and **~2 vCPU** before the first deploy (default RAM often OOMs during startup; healthcheck will fail).
   - **Networking:** click **Generate domain** → you get `https://something.up.railway.app`.
6. **Variables** tab — paste the [production variables](#required-variables) below, or copy from [`railway.variables.example`](railway.variables.example) (secrets from your local `.env`, never commit them).
7. Wait for **Deploy** to finish (first build ~5–15 min).
8. Open `https://YOUR-DOMAIN.up.railway.app/health` — should return `"status":"ok"`. Railway probes `/health/live` during deploy (see [`railway.toml`](railway.toml)).
9. Open the root URL, run one **Ask**, then create your **QR code** pointing to `https://YOUR-DOMAIN.up.railway.app/`.

## Required variables

Copy into Railway **Variables** (replace secrets with your real keys).

**Fastest fix for booth UI:** set `DEPLOYMENT_PROFILE=production` — this applies booth defaults (`INLINE_EVAL=false`, `POE_ENABLE_OLLAMA=false`, `JUDGE_PROVIDER=claude`) even if you forget the individual flags.

**Judges are not a Railway product** — `JUDGE_PROVIDER` chooses which **your** LLM API runs optional quality scores on each Ask (only when `INLINE_EVAL=true`). For the booth, use `INLINE_EVAL=false` or `DEPLOYMENT_PROFILE=production`.

**Do not use Ollama on Railway:** set `POE_ENABLE_OLLAMA=false`, delete or override any `JUDGE_PROVIDER=ollama`, `POE_PROVIDER_MODE=ollama`, or `OLLAMA_*` variables (local dev defaults from `.env.example`).

**Booth UI:** When `INLINE_EVAL=false`, the web UI shows **Answer + Sources only** (no quality scores, trace, or timing). `/health` returns `"inline_eval": false` and `"enable_ollama": false`.

**Do not set** a custom `PORT` — Railway injects it; the container uses it via [`scripts/start_api.sh`](scripts/start_api.sh).

### Claude + GPT-4 in the UI (recommended)

Both keys let attendees switch providers in the web UI. Initial startup default is Claude; switching to GPT-4 in the UI updates the runtime judge automatically.

```env
DEPLOYMENT_PROFILE=production
POE_PROVIDER_MODE=claude
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
JUDGE_PROVIDER=claude
INLINE_EVAL=false
POE_ENABLE_OLLAMA=false
RETRIEVAL_MODE=live
POE_DATA_DIR=/app/data
```

### Claude only

```env
DEPLOYMENT_PROFILE=production
POE_PROVIDER_MODE=claude
JUDGE_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6
RETRIEVAL_MODE=live
INLINE_EVAL=false
POE_ENABLE_OLLAMA=false
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

1. **Variables** — Use a block above; set `POE_ENABLE_OLLAMA=false`; remove `ollama` / `OLLAMA_*` / custom `PORT`.
2. **Resources** — **4 GB RAM** and **~2 vCPU** is enough after a successful deploy (8 GB is safe but costs more).
3. **Push** — `git push origin main` triggers a rebuild (includes `/health/live` in [`railway.toml`](railway.toml)).
4. **Verify** — Deploy logs show `Uvicorn running on http://0.0.0.0:...`; then:
   - `https://www.poesiosa.net/health/live` → `{"status":"ok"}`
   - `/health` → `"status":"ok"`, `"inline_eval": false`, `"enable_ollama": false`, `"deployment_profile": "production"`
   - Root URL → one **Ask** with Claude returns a real answer (not stub text)
   - Or run: `.\scripts\verify_railway_deploy.ps1 -BaseUrl "https://www.poesiosa.net"`

## Pushing updates (2 Jun – 7 Jun)

1. Edit code locally.
2. `git push origin main`
3. Railway rebuilds automatically (watch **Deployments**).
4. After deploy, run one test Ask on the public URL (warms the app).

QR code URL **does not change** if you keep the same Railway `*.up.railway.app` hostname. If you add a [custom domain](#custom-domain), point the QR at the new `https://...` URL instead.

## Local vs production

| | **Local** (your PC) | **Production** (Railway) |
|--|---------------------|---------------------------|
| Config | [`.env`](.env.example) | Railway **Variables** ([`railway.variables.example`](railway.variables.example)) |
| Run API | `poe-api` or `docker compose` | Auto-deploy on `git push origin main` |
| Run UI | `cd web && npm run dev` | Served from same container as API |
| Ollama | `POE_ENABLE_OLLAMA=true` (optional `ollama serve`) | `POE_ENABLE_OLLAMA=false` — hidden from dropdown |
| Judges | `INLINE_EVAL=true` for experiments | `INLINE_EVAL=false` at the booth |
| UI | Full: scores, trace, timing, Ollama | Booth: Answer + Sources only |

Production-only tweaks (no code): set Variables as in [Required variables](#required-variables). Code changes (background, UX, retrieval, hiding Ollama in the dropdown) require a git push.

## Custom domain

Railway does not sell domains. Register elsewhere, then attach the hostname in Railway. **No app code changes** are required.

### 1. Register a domain

Buy a name at any registrar, for example:

- [Cloudflare Registrar](https://www.cloudflare.com/products/registrar/)
- [Namecheap](https://www.namecheap.com), [Porkbun](https://porkbun.com)

A **subdomain** (e.g. `app.yourdomain.com`) is the simplest DNS setup for a demo.

### 2. Add the domain in Railway

1. [railway.app](https://railway.app) → your project → service (e.g. Siosa).
2. **Settings** → **Networking** → **Custom Domain** → **Add custom domain**.
3. Enter the full hostname (e.g. `app.yourdomain.com`).
4. Copy the **CNAME target** Railway shows (often something like `xxxx.up.railway.app`).

Your existing `https://siosa-production.up.railway.app` URL keeps working; both hostnames can point at the same service.

### 3. DNS at your registrar

Create a record in the DNS panel for that domain:

| Type | Host / Name | Value / Target |
|------|-------------|----------------|
| CNAME | `app` (for `app.yourdomain.com`) | Paste Railway’s CNAME target exactly |

For the **apex** (`yourdomain.com` with no subdomain), use Railway’s on-screen instructions (ALIAS/ANAME or CNAME flattening); subdomain CNAME is easier.

Save and wait for DNS to propagate (minutes to a few hours).

### 4. SSL

Railway provisions HTTPS automatically when DNS resolves. In Networking, the custom domain should show **Active**.

### 5. Verify and update QR

```powershell
curl https://app.yourdomain.com/health/live
.\scripts\verify_railway_deploy.ps1 -BaseUrl "https://app.yourdomain.com"
```

Reprint or regenerate your QR code with the new `https://` URL.

| Custom domain issue | Fix |
|---------------------|-----|
| Certificate pending | Wait for DNS; confirm CNAME matches Railway exactly |
| 502 on custom URL only | Check Networking target port; do not set a custom `PORT` variable |
| Old Railway URL still works | Expected — both hostnames can serve the same deploy |

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
| Health OK but stub answers | Set `POE_PROVIDER_MODE=claude` and `ANTHROPIC_API_KEY` in Variables |
| Claude/GPT greyed out in UI | Add `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` to Railway Variables |
| `/health` shows `judge_provider: ollama` | Set `JUDGE_PROVIDER=claude` (or `gpt4`); remove `ollama` from Variables |
| Homepage unchanged after git push | Code deployed; set `DEPLOYMENT_PROFILE=production` (or `INLINE_EVAL=false` + `POE_ENABLE_OLLAMA=false`) in Railway Variables |
| `/health` shows `inline_eval: true` | Add `DEPLOYMENT_PROFILE=production` or `INLINE_EVAL=false` in Railway Variables and redeploy |

## What the agent cannot do for you

- Create your Railway account or enter card details — **you** must do that in the browser.
- Paste API keys into Railway — copy from your local `.env` into **Variables**.
- Register a domain or edit DNS — use [Custom domain](#custom-domain) above at your registrar.

After you have a public URL, share it if you want help verifying health and a test query.
