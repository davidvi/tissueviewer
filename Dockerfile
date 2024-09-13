FROM python:3.11-slim-bookworm
# FROM continuumio/miniconda3:24.7.1-0

# Create directories
RUN mkdir -p /tv-import && \
    mkdir -p /tv-store

# Install vips and other required dependencies
RUN apt-get update && apt-get install -y \
    python3-opencv npm nodejs \
    openjdk-17-jdk wget unzip \ 
    && rm -rf /var/lib/apt/lists/*

# Copy the application
COPY server /server
COPY client /client

# install bioformats
WORKDIR /
RUN wget https://github.com/glencoesoftware/bioformats2raw/releases/download/v0.9.4/bioformats2raw-0.9.4.zip
RUN unzip bioformats2raw-0.9.4.zip

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

ENV TV_SAVE=True
ENV TV_SLIDE_DIR=/tv-store
ENV TV_IMPORT_DIR=/tv-import
ENV TV_TMP_DIR=/tmp

# Run the application using Gunicorn
CMD exec gunicorn --workers $WORKERS --threads $THREADS -b :$PORT -k uvicorn.workers.UvicornWorker server:app & python watch_folder.py
