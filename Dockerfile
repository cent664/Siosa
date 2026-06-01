# Build React UI

FROM node:22-alpine AS web-build

WORKDIR /web

COPY web/package.json ./

RUN npm install

COPY web/ ./

RUN npm run build



# Python API + static UI

FROM python:3.11-slim



WORKDIR /app



RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*



COPY pyproject.toml README.md ./

COPY src ./src



RUN pip install --no-cache-dir -e .



COPY docs ./docs

COPY --from=web-build /web/dist ./web/dist



ENV POE_PROVIDER_MODE=stub

ENV POE_API_HOST=0.0.0.0

ENV POE_API_PORT=8000



EXPOSE 8000



CMD ["uvicorn", "poe_agent.harness.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

