gcloud builds submit --tag gcr.io/studio-2517797099-c9afe_cloudbuild/shorts-gpu-worker
gcloud run deploy create-shorts-job \
  --image gcr.io/studio-2517797099-c9afe_cloudbuild/shorts-gpu-worker \
  --region us-central1 \
  --memory 16Gi \
  --cpu 4 \
  --timeout 3600 \
  --gpu 1 \
  --gpu-type nvidia-l4 \
  --no-cpu-throttling \
  --no-allow-unauthenticated