#!/usr/bin/env bash
set -euo pipefail

# Update this list when you add or remove a domain.
DOMAINS=(
  chat.jayloves.us
  dance.jayloves.us
  gym.jayloves.us
  schedule.jayloves.us
  speedtest.jayloves.us
  steven.jayloves.us
  stats.dance.jayloves.us
)

args=()
for d in "${DOMAINS[@]}"; do
  args+=("-d" "$d")
done

sudo certbot --nginx "${args[@]}"
