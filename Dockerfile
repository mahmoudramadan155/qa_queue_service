FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 celeryuser && \
    chown -R celeryuser:celeryuser /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package installer)
RUN pip install uv 
# --no-cache-dir

# Install Python dependencies
COPY requirements.txt .

RUN uv pip install --system -r requirements.txt 
# --no-cache-dir

# Copy project
COPY . .

# # Create necessary directories
# RUN mkdir -p /app/chroma_db /app/logs ./chroma_db ./data

# Create necessary directories and set permissions
RUN mkdir -p /app/chroma_db /app/logs ./chroma_db ./data && \
    chown -R celeryuser:celeryuser /app/chroma_db /app/logs ./chroma_db ./data

# Copy and make the start script executable
# COPY start.sh .
# RUN chmod +x start.sh

# Switch to non-root user
USER celeryuser

# Expose port
EXPOSE 8009

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8009"]

# Use the start script as the entrypoint
# CMD ["./start.sh"]
