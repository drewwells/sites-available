#!/usr/bin/env bash
set -euo pipefail

# Standalone cert for swingelo.com — kept separate from *.jayloves.us certs.
# Update this list when adding/removing swingelo domains.
DOMAINS=(
  swingelo.com
  www.swingelo.com
)

args=()
for d in "${DOMAINS[@]}"; do
  args+=("-d" "$d")
done

CERT_DIR="/etc/letsencrypt/live/swingelo.com"

if [[ ! -d "$CERT_DIR" ]]; then
  echo "No existing cert found at $CERT_DIR — bootstrapping with standalone mode."
  echo "Stopping nginx temporarily to free port 80..."
  sudo systemctl stop nginx
  sudo certbot certonly --standalone "${args[@]}"
  echo "Restarting nginx..."
  sudo systemctl start nginx
  echo "Bootstrap complete. You may now symlink swingelo.com.conf and reload nginx."
else
  echo "Cert exists — renewing/expanding with nginx plugin..."
  sudo certbot --nginx "${args[@]}"
fi
