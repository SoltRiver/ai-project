
# Python 3.11 Slim
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# libpq-dev is needed for psycopg2 (if used) or just general db tools
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Set environment path
ENV PYTHONPATH=/app

# Default command (can be overridden by compose)
CMD ["python", "app.py"]
