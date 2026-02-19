# AGENTS.md — Context for AI assistants

This repo manages nginx vhost configs for `jayloves.us` subdomains.
It is deployed to `/etc/nginx` on a single server.

## Repo layout

```
add-domain.sh                        # Script to onboard a new domain (see below)
regen-certs.sh                       # Expands the shared SAN cert via certbot
<domain>.conf                        # One nginx vhost config per domain
snippets/
  jayloves-proxy.conf                # Shared proxy_pass settings (headers, timeouts, WebSocket)
  upstreams/
    common.conf.example              # Template for the gitignored upstream host variable
    common.conf                      # NOT in git — set on the server manually
```

## How vhosts work

Each `.conf` file has two server blocks:
- Port 443 (SSL): proxies requests to an internal backend via `$upstream`
- Port 80: redirects to HTTPS

The proxy settings (headers, timeouts, WebSocket) are shared via `snippets/jayloves-proxy.conf`.

The internal backend hostname is set in `snippets/upstreams/common.conf` (gitignored) as:
```nginx
set $upstream_host INTERNAL_HOST;
```

Each vhost sets the port and constructs the full upstream URL:
```nginx
set $upstream http://$upstream_host:PORT;
```

SSL is managed by certbot. All domains share one SAN cert. The cert block in each vhost is added/managed by certbot and should not be edited manually.

## Onboarding a new domain

Always use `add-domain.sh` — do not create `.conf` files by hand:

```bash
./add-domain.sh <domain> <port>
# Example: ./add-domain.sh schedule.jayloves.us 7073
```

The script handles: conflict detection, config creation, symlinking to `sites-enabled`, nginx reload, and cert expansion.

## Common failure modes

- **Conflicting server_name warning**: The domain is already defined in another config (e.g. certbot injected it). Find the duplicate with:
  ```bash
  sudo nginx -T 2>/dev/null | grep -B5 "server_name <domain>" | grep "configuration file"
  ```

- **502 Bad Gateway**: Backend not running or `common.conf` has wrong hostname.

- **Nothing in error log**: Nginx isn't matching the vhost — config not symlinked to `sites-enabled` or nginx not reloaded.

- **504 Gateway Timeout**: Backend running but not responding within timeout.

## What NOT to do

- Do not edit the SSL cert block in `.conf` files — certbot manages it.
- Do not commit `snippets/upstreams/common.conf` — it contains internal hostnames.
- Do not run `certbot` directly — use `regen-certs.sh` to keep the domain list consistent.
- Do not create vhost configs manually — use `add-domain.sh` to avoid missing steps.
