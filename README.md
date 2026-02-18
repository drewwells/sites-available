# Nginx Sites (jayloves.us)

This folder holds nginx vhost configs for jayloves.us and friends.

## Reverse proxy include

Common proxy settings live in `snippets/jayloves-proxy.conf`.

Usage pattern in each vhost:

```nginx
location / {
    include snippets/upstreams/common.conf;
    set $upstream http://$upstream_host:PORT;
    include snippets/jayloves-proxy.conf;
}
```

The upstream is defined in a separate include so the internal hostnames do not live in git.

## Upstream definitions (not in git)

Use a single upstream include shared by all sites:

- `snippets/upstreams/common.conf`

This file is intentionally gitignored. Create it on the server by copying the `.example` file and filling in the internal hostname:

```bash
cp snippets/upstreams/common.conf.example snippets/upstreams/common.conf
```

The file should contain a single line like:

```nginx
set $upstream_host INTERNAL_HOST;
```

If you deploy this repo to `/etc/nginx`, the include path `snippets/upstreams/*.conf` resolves to `/etc/nginx/snippets/upstreams/*.conf`.

## Certbot: adding a new site

When you add a new vhost file and want it covered by the shared SAN cert, run:

```bash
sudo certbot --nginx -d dance.jayloves.us -d chat.jayloves.us -d speedtest.jayloves.us -d gym.jayloves.us
```

This will expand the existing certificate (or create it if it does not exist).

Use the helper script below to keep the list in one place.

## Certbot helper script

Edit `regen-certs.sh` to add/remove domains, then run it:

```bash
./regen-certs.sh
```

If you want to keep certbot from touching the `default` vhost, make sure `default` does not contain real `server_name` entries for your domains, and avoid enabling it in `sites-enabled` for those names.
