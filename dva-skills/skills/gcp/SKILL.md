---
name: gcp
description: >-
  Google Cloud Platform patterns, IAM, service accounts, gcloud CLI.
  Use this skill when working with GCP services.
---

# Google Cloud Platform

## Key Services

| Service | Purpose | CLI |
|---------|---------|-----|
| Cloud Spanner | Distributed SQL database | `gcloud spanner` |
| Cloud Storage (GCS) | Object storage | `gsutil` / `gcloud storage` |
| Cloud Run | Serverless containers | `gcloud run` |
| GKE | Kubernetes clusters | `gcloud container` |
| Pub/Sub | Messaging | `gcloud pubsub` |
| Cloud Functions | Serverless functions | `gcloud functions` |
| Secret Manager | Secrets | `gcloud secrets` |
| Vertex AI | ML/AI platform | `gcloud ai` |

## Authentication

```bash
# User auth (development)
gcloud auth login
gcloud auth application-default login

# Service account
gcloud auth activate-service-account --key-file=key.json
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json

# Check current auth
gcloud auth list
gcloud config get-value project
```

## Common Commands

```bash
gcloud config set project MY_PROJECT
gcloud config set compute/region us-central1

gcloud run deploy my-service --source . --region us-central1
gcloud builds submit --tag gcr.io/MY_PROJECT/my-service

gcloud secrets versions access latest --secret=MY_SECRET
```

## IAM Patterns

```bash
# Grant role
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:SA@PROJECT.iam.gserviceaccount.com" \
  --role="roles/spanner.databaseUser"

# Create service account
gcloud iam service-accounts create my-sa --display-name="My SA"
```

## Guidelines

- Use Workload Identity Federation over service account keys
- Use Secret Manager for secrets (not env vars in deployment config)
- Set up Cloud Audit Logging for compliance
- Use VPC Service Controls for sensitive data
- Prefer managed services (Cloud Run, Cloud Functions) over GCE/GKE when possible
- Use `gcloud config configurations` for multiple project contexts
