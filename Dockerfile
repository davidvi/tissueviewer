FROM python:3.11-slim-bookworm

# Create directories
RUN mkdir -p /iv-import && \
    mkdir -p /iv-store && \
    chmod +rx /iv-import && \
    chmod +rx /iv-store

# Install vips and other required dependencies
RUN apt-get update && apt-get install -y \
    libvips-dev libvips libvips-tools openslide-tools python3-opencv \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /requirements.txt

RUN pip install --no-cache-dir -r /requirements.txt

# Copy the application
COPY src /src

# Set the working directory
WORKDIR /src/ImmunoViewer

# Expose port (optional, adjust as needed)
EXPOSE 8000

# Define environment variable for number of worker processes
ENV WORKER_PROCESSES=8

# Run the application using Gunicorn
CMD exec gunicorn -w $WORKER_PROCESSES -b 0.0.0.0:8000 server:app & python watch_folder_docker.py