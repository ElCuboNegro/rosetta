# Rosetta Dictionary - Dockerfile
# Multi-stage build for efficient image size

FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    bzip2 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml ./
COPY src/ ./src/
COPY conf/ ./conf/

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Create data directories
RUN mkdir -p data/01_raw data/02_intermediate data/03_primary data/08_reporting

# Expose Kedro Viz port
EXPOSE 4141

# Default command
CMD ["kedro", "run"]
