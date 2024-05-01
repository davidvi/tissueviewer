FROM python:3.11-slim-bookworm

# Create directories if not bound
RUN mkdir -p /iv-store 

# Install required dependencies
RUN apt-get update && apt-get install -y \
    python3-opencv gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install ImmunoViewer

# Expose port (optional, adjust as needed)
ENV PORT 8080
EXPOSE 8080

# Define environment variable for number of worker processes
ENV WORKERS 1
ENV THREADS 20

ENV IV_SAVE False
ENV IV_SLIDE_DIR /iv-store

# Run the application using Gunicorn
CMD exec gunicorn --workers $WORKERS --threads $THREADS -b :$PORT -k uvicorn.workers.UvicornWorker ImmunoViewer.server:app