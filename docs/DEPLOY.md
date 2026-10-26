# Deploying Aakalan on an Ubuntu server (no Docker)

One Ubuntu server (AWS EC2, Ubuntu 24.04 recommended) runs everything as plain services:

| Service | What | Listens on |
|---|---|---|
| `aakalan-api` | FastAPI (uvicorn) | 127.0.0.1:8000 |
| `aakalan-worker` | Huey background jobs | — |
| `aakalan-web` | Next.js standalone build | 127.0.0.1:3000 |
| Caddy | front door: `/api/*` → API, the rest → website; HTTPS once a domain is set | :80, :443 |

All data stays in `data/` in the checkout (SQLite database, uploads, reports). Settings are in
`.env` at the repo root, read by the app itself. The files are in `deploy/`; the paths in the
service files assume the checkout is `/home/ubuntu/Aakalan` and the user is `ubuntu`.

Open ports 22, 80 and 443 in the EC2 security group. With 1 GB of memory, add swap first (the
website build needs it):

```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## First install

```bash
# 1. Tools: git, Node 22, uv (Python), Caddy
sudo apt-get update && sudo apt-get install -y git curl debian-keyring debian-archive-keyring apt-transport-https
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt-get install -y nodejs
curl -LsSf https://astral.sh/uv/install.sh | sh && source ~/.local/bin/env
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt-get update && sudo apt-get install -y caddy

# 2. The code (a private repo asks for a GitHub username and a personal access token)
cd ~ && git clone -b phase2/accuracy https://github.com/0607rj/Aakalan.git && cd Aakalan

# 3. Settings
cp .env.example .env
sed -i "s/^ENVIRONMENT=.*/ENVIRONMENT=production/" .env
sed -i "s/^JWT_SECRET=.*/JWT_SECRET=$(openssl rand -hex 32)/" .env
sed -i 's|^CORS_ORIGINS=.*|CORS_ORIGINS=["http://SERVER_IP"]|' .env
sed -i 's|^NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=http://SERVER_IP/api|' .env
nano .env   # SEED_USER_PASSWORD (admin@gmail.com's password), ANTHROPIC_API_KEY, SMTP_*

# 4. Services and Caddy
sudo cp deploy/aakalan-*.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable aakalan-api aakalan-worker aakalan-web
sudo cp deploy/Caddyfile /etc/caddy/Caddyfile && sudo systemctl reload caddy

# 5. Build and start (also the command for every later update)
bash deploy/update.sh
```

Replace `SERVER_IP` with the server's public IP. Then open `http://SERVER_IP` and log in as
`admin@gmail.com` with `SEED_USER_PASSWORD`. In production, sign-up codes need the SMTP settings.

## Updating

```bash
cd ~/Aakalan && bash deploy/update.sh
```

It pulls the code, installs, migrates, loads new seed versions, rebuilds the website and restarts
the services.

## Adding the domain (HTTPS)

1. In the DNS for panscience.ai, add an A record: `akalan` → the server's IP.
2. On the server:

```bash
cd ~/Aakalan
sudo sed -i 's|^:80 {|akalan.panscience.ai {|' /etc/caddy/Caddyfile && sudo systemctl reload caddy
sed -i 's|^NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=https://akalan.panscience.ai/api|' .env
sed -i 's|^CORS_ORIGINS=.*|CORS_ORIGINS=["https://akalan.panscience.ai"]|' .env
bash deploy/update.sh
```

## When something fails

- Logs: `journalctl -u aakalan-api -n 100` (or `aakalan-worker`, `aakalan-web`, `caddy`).
- The API stops at start with an SQLite extension error: this Python cannot load sqlite-vec. Set
  `SQLITE_VEC_ENABLED=false` in `.env` and `sudo systemctl restart aakalan-api aakalan-worker`.
- The website build is killed: not enough memory, add the swap above.
