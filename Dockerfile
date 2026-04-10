# Stage 1: Build Frontend
FROM node:20 AS frontend-builder
WORKDIR /app/frontend
# Ensure package.json exists to install deps
COPY frontend/package*.json ./
RUN npm install
# Copy rest of frontend files and build
COPY frontend/ ./
RUN npm run build

# Stage 2: Serve Backend
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY server/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt



# Copy application code
COPY . /app/

# Copy the built frontend from stage 1 over to the backend container
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Create outputs directory
RUN mkdir -p /app/outputs/logs /app/outputs/evals

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Expose port
EXPOSE 8000

# Run server
CMD ["gunicorn", "server.app:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "120"]
