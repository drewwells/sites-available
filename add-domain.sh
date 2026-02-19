#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Usage: $0 <domain> <port>"
    echo "  Example: $0 schedule.jayloves.us 7073"
    exit 1
}

[[ $# -ne 2 ]] && usage

DOMAIN="$1"
PORT="$2"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONF="$SCRIPT_DIR/${DOMAIN}.conf"
ENABLED="/etc/nginx/sites-enabled/${DOMAIN}.conf"
REGEN="$SCRIPT_DIR/regen-certs.sh"

# Validate port is a number
if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
    echo "Error: port must be a number, got '$PORT'"
    exit 1
fi

# Check for duplicate server_name in existing nginx config
if sudo nginx -T 2>/dev/null | grep -q "server_name ${DOMAIN};"; then
    echo "Error: server_name '${DOMAIN}' already exists in nginx config."
    echo "Run: sudo nginx -T 2>/dev/null | grep -B5 'server_name ${DOMAIN}' | grep 'configuration file'"
    exit 1
fi

# Create vhost config
cat > "$CONF" <<EOF
server {
    server_name ${DOMAIN};

    location / {
        include sites-available/snippets/upstreams/common.conf;
        set \$upstream http://\$upstream_host:${PORT};
        include sites-available/snippets/jayloves-proxy.conf;
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/chat.jayloves.us/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/chat.jayloves.us/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot
}
server {
    if (\$host = ${DOMAIN}) {
        return 301 https://\$host\$request_uri;
    } # managed by Certbot

    listen 80;
    server_name ${DOMAIN};
}
EOF
echo "Created $CONF"

# Add domain to regen-certs.sh if not already present
if ! grep -q "${DOMAIN}" "$REGEN"; then
    sed -i "s/^)/  ${DOMAIN}\n)/" "$REGEN"
    echo "Added ${DOMAIN} to regen-certs.sh"
else
    echo "${DOMAIN} already in regen-certs.sh"
fi

# Symlink to sites-enabled
if [[ ! -L "$ENABLED" ]]; then
    sudo ln -s "$CONF" "$ENABLED"
    echo "Symlinked to $ENABLED"
else
    echo "Symlink already exists at $ENABLED"
fi

# Test and reload nginx
sudo nginx -t
sudo systemctl reload nginx
echo "nginx reloaded"

# Expand the cert
echo ""
echo "Expanding TLS cert to include ${DOMAIN}..."
bash "$REGEN"

echo ""
echo "Done. ${DOMAIN} is now live."
