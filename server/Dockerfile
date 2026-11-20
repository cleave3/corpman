FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for asyncpg and cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Expose port (Render automatically sets $PORT)
ENV PORT=8000
EXPOSE 8000

# Run with Uvicorn; single worker to keep memory well within Render's 512MB limit
CMD ["sh", "-c", "uvicorn src:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --timeout-graceful-shutdown 15"]