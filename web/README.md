# PoE Wiki Agent — Web UI

React + Vite frontend. Production build is served by FastAPI at `http://127.0.0.1:8000/`.

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

Output: `dist/` (gitignored). `start.bat` runs this automatically if `dist/index.html` is missing.
