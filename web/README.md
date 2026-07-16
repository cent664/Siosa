# PoE Wiki Agent — Web UI

React + Vite frontend. Production build is served by FastAPI at `http://127.0.0.1:8000/`.

**Prerequisite:** Node.js LTS (22+). Install from [nodejs.org](https://nodejs.org/) or `winget install OpenJS.NodeJS.LTS` if `npm` is not on PATH.

## Setup

```bash
npm install
```

## Development

With the API on port 8000:

```bash
npm run dev
```

Open http://localhost:5173 (API calls are proxied to :8000).

## Production build

```bash
npm run build
```

Output: `dist/` (gitignored). `start.bat` / `start.ps1` always run `npm install` and `npm run build` before starting the API.
