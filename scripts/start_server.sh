#!/usr/bin/env bash
set -e

cd /home/google/symon-image-server
source venv/bin/activate

export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8090
