#!/usr/bin/env bash

set -euo pipefail
docker run \
  --rm \
  --name rick_vfs-minio \
  -p 9010:9000 \
  -p 9011:9001 \
  -e "MINIO_ROOT_USER=SomeTestUser" \
  -e "MINIO_ROOT_PASSWORD=SomeTestPassword" \
  quay.io/minio/minio server /data --console-address ":9001"

