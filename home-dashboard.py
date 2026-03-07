#!/usr/bin/env python3
"""Home dashboard HTTP server — dynamically discovers services on this host.

Socket-activated by systemd (home-dashboard.socket) or run standalone
for testing (falls back to binding :8888).
"""

import os
import re
import socket
import subprocess
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path


NGINX_DIRS = [
    "/etc/nginx/sites-enabled",
    "/etc/nginx/sites-available",
]

# Ports to skip — system noise, not interesting services
SKIP_PORTS = {22, 25, 53, 80, 443, 8888, 10000}
SKIP_PORT_BELOW = 1000


def get_docker_port_map():
    """Return {host_port: {"name": container_name, "image": image}} via docker ps."""
    try:
        out = subprocess.check_output(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Image}}\t{{.Ports}}"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return {}

    port_map = {}
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        name, image, ports_str = parts[0], parts[1], parts[2]
        # ports_str: "0.0.0.0:8080->80/tcp, :::8080->80/tcp, 0.0.0.0:9000->9000/tcp"
        for m in re.finditer(r"(?:[\d.]+|:::):(\d+)->", ports_str):
            host_port = int(m.group(1))
            if host_port not in port_map:
                port_map[host_port] = {"name": name, "image": image}
    return port_map


def proc_cmdline_name(pid):
    """Try to derive a friendly name from /proc/<pid>/cmdline."""
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        args = raw.split(b"\x00")
        # args[0] is the binary; strip path
        binary = os.path.basename(args[0].decode(errors="replace"))
        # For interpreters (python*, node, ruby, java), show the script/jar arg
        if binary.startswith(("python", "node", "ruby", "java", "perl")):
            for arg in args[1:]:
                a = arg.decode(errors="replace")
                if a and not a.startswith("-"):
                    return os.path.basename(a).removesuffix(".py").removesuffix(".js")
        return binary
    except OSError:
        return ""


def discover_listeners():
    """Return list of dicts: {port, process, pid} for all listening TCP ports."""
    try:
        out = subprocess.check_output(
            ["ss", "-tlnp"], text=True, stderr=subprocess.DEVNULL
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []

    docker_map = get_docker_port_map()

    services = []
    seen_ports = set()
    for line in out.splitlines()[1:]:  # skip header
        parts = line.split()
        if len(parts) < 4:
            continue
        addr = parts[3]
        m = re.search(r":(\d+)$", addr)
        if not m:
            continue
        port = int(m.group(1))
        if port in SKIP_PORTS or port < SKIP_PORT_BELOW or port in seen_ports:
            continue
        seen_ports.add(port)

        process = ""
        pid = ""
        proc_m = re.search(r'\("([^"]+)",pid=(\d+)', line)
        if proc_m:
            process = proc_m.group(1)
            pid = proc_m.group(2)

        # Skip rpc.* services and anything with no process info at all
        if process.startswith("rpc.") or (not process and not pid):
            continue

        # Resolve a friendly name
        if port in docker_map:
            info = docker_map[port]
            friendly = info["name"]
            detail = info["image"]
        elif process == "docker-proxy":
            # docker-proxy port not matched above — shouldn't happen, but fall back
            friendly = "docker"
            detail = f"port {port}"
        elif pid:
            friendly = proc_cmdline_name(pid) or process
            detail = process
        else:
            friendly = process
            detail = ""

        # Drop anything that still has no meaningful name
        if not friendly or friendly.startswith("pid:"):
            continue

        services.append({
            "port": port,
            "process": process,
            "pid": pid,
            "friendly": friendly,
            "detail": detail,
            "domain": "",
        })

    return sorted(services, key=lambda s: s["port"])


def load_nginx_port_map():
    """Parse nginx configs and return {port: domain} from proxy_pass lines."""
    port_map = {}
    for d in NGINX_DIRS:
        p = Path(d)
        if not p.is_dir():
            continue
        for f in p.glob("*.conf"):
            try:
                text = f.read_text()
            except OSError:
                continue
            domain_m = re.search(r"server_name\s+([^\s;]+)", text)
            if not domain_m:
                continue
            domain = domain_m.group(1)
            # match port-based upstream: set $upstream http://...:PORT;
            for port_m in re.finditer(r":(\d+)\s*(?:/[^\s;]*)?\s*;", text):
                port = int(port_m.group(1))
                if port not in (80, 443):
                    port_map[port] = domain
    return port_map


def get_services():
    listeners = discover_listeners()
    port_map = load_nginx_port_map()
    for svc in listeners:
        svc["domain"] = port_map.get(svc["port"], "")
    return listeners


CARD_TEMPLATE = """
  <a class="card" href="{href}">
    <p class="name">{name}</p>
    <p class="host">{host}</p>
    <span class="port">:{port}</span>
  </a>"""

PAGE_TEMPLATE = """\
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>jayloves.us — services</title>
<style>
* {{ box-sizing: border-box; }}
body {{
    margin: 0;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    background: #0f172a;
    color: #e2e8f0;
    min-height: 100vh;
    padding: 48px 24px;
}}
h1 {{ font-size: 28px; margin: 0 0 8px 0; color: #f8fafc; }}
p.sub {{ margin: 0 0 40px 0; color: #64748b; font-size: 14px; }}
.grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 16px;
    max-width: 960px;
}}
a.card {{
    display: block;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 24px;
    text-decoration: none;
    color: inherit;
    transition: border-color .15s, background .15s;
}}
a.card:hover {{ border-color: #60a5fa; background: #1e3a5f; }}
.name {{ font-size: 18px; font-weight: 600; color: #f1f5f9; margin: 0 0 6px 0; }}
.host {{ font-size: 12px; color: #64748b; margin: 0 0 12px 0; }}
.port {{
    display: inline-block;
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 12px;
    color: #94a3b8;
}}
.empty {{ color: #475569; font-size: 14px; }}
</style>
</head>
<body>
<h1>jayloves.us</h1>
<p class="sub">Services discovered on this host</p>
<div class="grid">
{cards}
</div>
</body>
</html>"""


def render_page(services, server_host):
    if not services:
        cards = '  <p class="empty">No services found.</p>'
    else:
        parts = []
        for svc in services:
            domain = svc["domain"]
            friendly = svc.get("friendly") or svc["process"] or f"pid:{svc['pid']}"
            detail = svc.get("detail", "")
            if domain:
                href = f"https://{domain}"
                name = domain.split(".")[0].title()
                host = domain
            else:
                href = f"http://{server_host}:{svc['port']}"
                name = friendly
                host = detail if detail and detail != friendly else ""
            parts.append(CARD_TEMPLATE.format(
                href=href, name=name, host=host, port=svc["port"]
            ))
        cards = "\n".join(parts)
    return PAGE_TEMPLATE.format(cards=cards).encode()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Use the Host header so links work from any client, not just localhost
        server_host = self.headers.get("Host", "localhost").split(":")[0]
        body = render_page(get_services(), server_host)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(fmt % args, file=sys.stderr, flush=True)


def main():
    listen_fds = int(os.environ.get("LISTEN_FDS", 0))
    if listen_fds >= 1:
        sock = socket.fromfd(3, socket.AF_INET6, socket.SOCK_STREAM)
    else:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", 8888))
        sock.listen(5)
        print("Listening on http://localhost:8888")

    server = HTTPServer(("", 0), Handler)
    server.socket = sock
    server.serve_forever()


if __name__ == "__main__":
    main()
