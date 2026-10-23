# syntax=docker/dockerfile:1
FROM python:3.10-slim

# Avoid interactive prompts during Debian package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV YOLO_CONFIG_DIR=/tmp/ultralytics_config

# Install system runtime dependencies for OpenCV and Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Step 1: Install CPU-only PyTorch (reduces image size from ~3.5GB to ~350MB)
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Step 2: Install application requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Step 3: Copy repository files
COPY . .

# Ensure temporary config directory exists and is writable
RUN mkdir -p /tmp/ultralytics_config && chmod -R 777 /tmp/ultralytics_config

# Render dynamically sets $PORT environment variable
ENV PORT=8000
EXPOSE 8000

# Start Uvicorn bound to 0.0.0.0 and the dynamically assigned $PORT
CMD ["sh", "-c", "uvicorn app.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
