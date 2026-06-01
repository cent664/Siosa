# PoE Wiki Agent



Path of Exile **1** wiki-grounded Q&A for portfolio and learning. Ask mechanics questions; get answers with citations from [poewiki.net](https://www.poewiki.net/wiki/Path_of_Exile_Wiki).



**Browser docs** (with API running): [Architecture](http://127.0.0.1:8000/docs/architecture.html) · [Changelog](http://127.0.0.1:8000/docs/changelog.html)



## Quick start



```powershell

cd Project

python -m venv .venv

.venv\Scripts\activate

pip install -e ".[dev,speech]"



copy .env.example .env

```



**Preferred — one click:** double-click `start.bat` (or run `.\start.ps1`). Builds the React UI if needed, then starts the API.



- App: http://127.0.0.1:8000/

- API: http://127.0.0.1:8000

- Docs: http://127.0.0.1:8000/docs/



**UI development (hot reload):**



```powershell

# Terminal 1

uvicorn poe_agent.harness.api.app:app --reload --host 127.0.0.1 --port 8000



# Terminal 2

cd web

npm install

npm run dev

```



Vite runs on http://localhost:5173 and proxies API routes to port 8000.



## Index wiki content (once)



```powershell

poe-ingest

```



Fetches **18 curated** PoE 1 pages → `data/chunks/` + `data/chroma/`. Restart API if it was running during ingest.



## Answer mode



Use the **sidebar** to switch **stub**, **ollama**, **claude**, or **gpt4**. Claude/GPT-4 need API keys in `.env`. Each answer shows quality scores and an expandable LLM trace.



## Regenerate docs



After editing `docs/ARCHITECTURE.md` or `docs/CHANGELOG.md`:



```powershell

python scripts/sync_docs.py

```



---

