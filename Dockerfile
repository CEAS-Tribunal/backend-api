# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create and set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user
RUN adduser --disabled-password --no-create-home django

# Copy the entrypoint script and make it executable
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && \
    chown django:django /entrypoint.sh

# Change ownership of the app directory to django user
RUN chown -R django:django /app

# Switch to non-root user
USER django

# Expose port 8000
EXPOSE 8000

# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]