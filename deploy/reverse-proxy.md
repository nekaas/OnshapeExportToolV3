# Reverse Proxy & Remote Access

The Onshape Export Manager listens on `http://0.0.0.0:8080` in Server Mode. Put a
reverse proxy in front of it to add HTTPS and a clean hostname, or use Tailscale
/ Cloudflare Tunnel for zero-config remote access. The dashboard's **System**
page auto-detects whichever of these is installed and shows the access URLs.

---

## Tailscale (recommended — easiest)

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Once connected, the **System** page shows the appliance's tailnet address, e.g.
`http://100.x.y.z:8080` and the MagicDNS name `http://onshape-pi.tailnet.ts.net:8080`.
No ports need to be opened on your router.

---

## Cloudflare Tunnel

```bash
# Install cloudflared, then authenticate and create a named tunnel:
cloudflared tunnel login
cloudflared tunnel create onshape
cloudflared tunnel route dns onshape onshape.example.com
```

`~/.cloudflared/config.yml`:

```yaml
tunnel: onshape
credentials-file: /home/pi/.cloudflared/<TUNNEL-ID>.json
ingress:
  - hostname: onshape.example.com
    service: http://localhost:8080
  - service: http_status:404
```

```bash
sudo cloudflared service install
sudo systemctl enable --now cloudflared
```

The **System** page detects the running `cloudflared` service and reports tunnel
status (Connected / Disconnected) and the configured tunnel name.

---

## NGINX

```nginx
server {
    listen 80;
    server_name onshape.example.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Server-Sent Events (live dashboard) need buffering off:
        proxy_buffering off;
        proxy_read_timeout 3600s;
    }
}
```

Add HTTPS with Let's Encrypt: `sudo certbot --nginx -d onshape.example.com`.

---

## Caddy (automatic HTTPS)

`/etc/caddy/Caddyfile`:

```
onshape.example.com {
    reverse_proxy 127.0.0.1:8080 {
        flush_interval -1   # stream Server-Sent Events
    }
}
```

Caddy obtains and renews Let's Encrypt certificates automatically.

---

## Traefik (Docker labels)

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.onshape.rule=Host(`onshape.example.com`)"
  - "traefik.http.routers.onshape.entrypoints=websecure"
  - "traefik.http.routers.onshape.tls.certresolver=letsencrypt"
  - "traefik.http.services.onshape.loadbalancer.server.port=8080"
```

---

## HTTPS notes

- Behind a proxy, set `server.behind_proxy = true` in `config.json` (or the
  Settings page) so generated links use the external scheme.
- Let's Encrypt certificates under `/etc/letsencrypt/live/<domain>` are
  auto-detected and shown on the **System** page.
- For a quick self-signed certificate on a LAN-only box:
  `openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 365`.
