# Nginx Sites (jayloves.us)

This folder holds nginx vhost configs for jayloves.us and friends.
It is deployed to `/etc/nginx` on the server.

## Adding a new domain

Use `add-domain.sh`:

```bash
./add-domain.sh <domain> <port>
```

Example:

```bash
./add-domain.sh schedule.jayloves.us 7073
```

This script will:
1. Check for duplicate `server_name` conflicts in the existing nginx config
2. Create the vhost `.conf` file from the standard template
3. Add the domain to `regen-certs.sh`
4. Symlink the config into `/etc/nginx/sites-enabled/`
5. Test and reload nginx
6. Run `regen-certs.sh` to expand the shared TLS cert

## Upstream definitions (not in git)

All vhosts share a single upstream host variable defined in:

- `sites-available/snippets/upstreams/common.conf`

This file is intentionally gitignored. Create it on the server by copying the example:

```bash
cp sites-available/snippets/upstreams/common.conf.example sites-available/snippets/upstreams/common.conf
```

Set it to the internal Tailscale (or LAN) hostname that backs your services:

```nginx
set $upstream_host INTERNAL_HOST;
```

Each vhost then sets the port:

```nginx
set $upstream http://$upstream_host:PORT;
```

If you deploy this repo to `/etc/nginx`, the include path `sites-available/snippets/upstreams/*.conf` resolves to `/etc/nginx/sites-available/snippets/upstreams/*.conf`.

## TLS certificates

All domains share a single SAN cert managed by certbot. The domain list lives in `regen-certs.sh`. To manually regenerate/expand the cert:

```bash
./regen-certs.sh
```

`add-domain.sh` calls this automatically when onboarding a new domain.

## Proxy settings

Common reverse proxy settings (timeouts, headers, WebSocket support) live in:

- `sites-available/snippets/jayloves-proxy.conf`

This is included by every vhost and should not need to be edited for new domains.
