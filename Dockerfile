FROM python:3.11-slim-bookworm

# Create directories
RUN mkdir -p /iv-import && \
    mkdir -p /iv-store && \
    mkdir -p /iv-completed

# Install vips and other required dependencies
RUN apt-get update && apt-get install -y \
    libvips-dev libvips libvips-tools openslide-tools python3-opencv gcc nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# Copy the application
COPY server /server
COPY client /client

# build node
WORKDIR /client
RUN npm install
RUN npm run build

# Set the working directory
WORKDIR /server

# Install the required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (optional, adjust as needed)
ENV PORT=8080
EXPOSE 8080

# Define environment variable for number of worker processes
ENV WORKERS=8
ENV THREADS=20

ENV IV_SAVE=True
ENV IV_SLIDE_DIR=/iv-store
ENV IV_IMPORT_DIR=/iv-import
ENV IV_TMP_DIR=/tmp
ENV IV_COMPLETED_DIR=/iv-completed

# Run the application using Gunicorn
CMD exec gunicorn --workers $WORKERS --threads $THREADS -b :$PORT -k uvicorn.workers.UvicornWorker server:app & python watch_folder.py