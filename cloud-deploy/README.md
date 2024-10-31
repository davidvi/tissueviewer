# Deploying ImmunoViewer on Google Cloud Platform

This guide describes how to deploy the ImmunoViewer application to Google Cloud Platform (GCP) using Google Cloud Run and Artifact Registry.

## Prerequisites

- Ensure you have the Google Cloud SDK installed and initialized.
- You should have Docker installed and running on your local machine.
- Make sure you have access to the Google Cloud project where you intend to deploy the application.

## Steps

### 1. Configure GCP Project

Verify that you are operating in the correct GCP project. Replace `{YOUR-GCP-PROJECT-NAME}` with your actual project ID.

```bash
gcloud config set project {YOUR-GCP-PROJECT-NAME}
```

And make sure you are working in the main github folder.  

```bash
git clone https://github.com/davidvi/tissueviewer.git
cd tissueviewer
```

### 2. Check for Existing Artifact Repository

Check if the required Docker repository exists in your project:

```bash
gcloud artifacts repositories list --location=us-central1
```

### 3. Create Artifact Repository

If the repository does not exist, create a new one:

```bash
gcloud artifacts repositories create tv --repository-format=docker --location=us-central1
```

### 4. Configure Docker Authentication

Authenticate Docker with GCP to allow pushing and pulling images:

```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
```

### 5. Build and Tag Docker Image

Build your Docker image locally and tag it for upload:

```bash
docker build -t tv-cloud -f cloud-deploy/Dockerfile .
docker tag tv-cloud us-central1-docker.pkg.dev/{YOUR-GCP-PROJECT-NAME}/tv/tv-cloud:latest
```

### 6. Push Docker Image

Push the Docker image to Google Artifact Registry:

```bash
docker push us-central1-docker.pkg.dev/{YOUR-GCP-PROJECT-NAME}/tv/tv-cloud
```

### 7. Deploy to Cloud Run

Deploy the image to Google Cloud Run:

```bash
gcloud run deploy iv --image us-central1-docker.pkg.dev/{YOUR-GCP-PROJECT-NAME}/tv/tv-cloud --platform managed --allow-unauthenticated --execution-environment gen2
```

### 8. Attach Storage Bucket

Visit the Google Cloud documentation on [mounting Cloud Storage volumes](https://cloud.google.com/run/docs/configuring/services/cloud-storage-volume-mounts) for step-by-step instructions.

## Accessing Your Application

Once deployed, your application will be accessible via a URL provided by Google Cloud Run. This URL will be displayed in the output of the deploy command.
