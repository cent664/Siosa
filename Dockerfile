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

# Pre-download rerank model so first conference Ask is faster (adds ~100MB to image).
RUN python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

COPY docs ./docs

COPY --from=web-build /web/dist ./web/dist



ENV POE_PROVIDER_MODE=claude
ENV POE_API_HOST=0.0.0.0
ENV POE_API_PORT=8000
ENV POE_DATA_DIR=/app/data

EXPOSE 8000

COPY scripts/start_api.sh /app/scripts/start_api.sh
RUN chmod +x /app/scripts/start_api.sh

CMD ["/app/scripts/start_api.sh"]

