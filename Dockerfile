FROM python:3.11-slim-bookworm

# Create directories
RUN mkdir -p /iv-import && \
    mkdir -p /iv-store

# Install vips and other required dependencies
RUN apt-get update && apt-get install -y \
    libvips-dev libvips libvips-tools openslide-tools python3-opencv gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install ImmunoViewer

# Copy the application
COPY src /src

# Set the working directory
WORKDIR /src/ImmunoViewer

# Expose port (optional, adjust as needed)
ENV PORT=8080
EXPOSE 8080

# Define environment variable for number of worker processes
ENV WORKERS=8
ENV THREADS=20

ENV IV_SAVE=True
ENV IV_SLIDE_DIR=/iv-store

# Run the application using Gunicorn
CMD exec gunicorn --workers $WORKERS --threads $THREADS -b :$PORT -k uvicorn.workers.UvicornWorker server:app & python watch_folder_docker.py