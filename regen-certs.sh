#!/usr/bin/env bash
set -euo pipefail

# Update this list when you add or remove a domain.
DOMAINS=(
  dance.jayloves.us
  chat.jayloves.us
  speedtest.jayloves.us
  gym.jayloves.us
)

args=()
for d in "${DOMAINS[@]}"; do
  args+=("-d" "$d")
done

sudo certbot --nginx "${args[@]}"
