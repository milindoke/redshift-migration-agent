FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -e .
RUN pip install --no-cache-dir -r requirements-agent.txt
RUN pip install --no-cache-dir fastapi uvicorn

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV AWS_REGION=us-east-2

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run the API server
CMD ["python", "api_server.py"]
