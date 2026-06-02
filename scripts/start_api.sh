#!/bin/sh
# Railway and other hosts set PORT; default 8000 for local Docker.
PORT="${PORT:-8000}"
exec uvicorn poe_agent.harness.api.app:app --host 0.0.0.0 --port "$PORT"
