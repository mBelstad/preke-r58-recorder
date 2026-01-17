#!/bin/bash
# Clear server-side caches (best-effort)
set -e

echo "[Cache] Clearing server-side caches..."

# Clear nginx cache if present
if [ -d "/var/cache/nginx" ]; then
  echo "[Cache] Clearing /var/cache/nginx"
  rm -rf /var/cache/nginx/* || true
fi

# Clear temporary files
echo "[Cache] Clearing /tmp/preke-*"
rm -rf /tmp/preke-* || true

# Clear Python bytecode caches
echo "[Cache] Clearing __pycache__ folders"
find /opt/preke-r58-recorder -type d -name "__pycache__" -prune -exec rm -rf {} + || true

echo "[Cache] Done"
