# ---- Build frontend ----
FROM node:22-alpine AS frontend-build
WORKDIR /app/web
COPY web/package.json web/package-lock.json* ./
RUN npm ci
COPY web/ ./
RUN npm run build

# ---- Python backend ----
FROM python:3.13-slim
WORKDIR /app

# Install dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[web]"

# Copy backend source
COPY agent_company/ ./agent_company/
COPY prompts/ ./prompts/
COPY .env.example ./.env.example

# Copy built frontend
COPY --from=frontend-build /app/web/dist ./web/dist

# Serve static frontend from FastAPI
# We need to add static file serving to the backend

EXPOSE 8000
ENV LOG_LEVEL=INFO

CMD ["python", "-m", "agent_company.cli.app", "serve"]
