#!/usr/bin/env bash
# Prepare a fresh Hostinger VPS (Ubuntu 22.04/24.04) for BD Coach.
# Run as root: curl -fsSL ... | bash   OR   sudo ./scripts/install-hostinger.sh
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root (sudo ./scripts/install-hostinger.sh)"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

echo "==> System update"
apt-get update -qq
apt-get upgrade -y -qq

echo "==> Base packages"
apt-get install -y -qq ca-certificates curl git ufw fail2ban

echo "==> Docker (official)"
if ! command -v docker &>/dev/null; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  . /etc/os-release
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
    ${VERSION_CODENAME} stable" >/etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi

echo "==> Deploy user"
DEPLOY_USER="${DEPLOY_USER:-bdcoach}"
if ! id "${DEPLOY_USER}" &>/dev/null; then
  useradd -m -s /bin/bash "${DEPLOY_USER}"
  usermod -aG docker "${DEPLOY_USER}"
fi

echo "==> Firewall"
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "==> Swap (recommended on 8 GB plans)"
if [[ ! -f /swapfile ]]; then
  fallocate -l 4G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=4096
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >>/etc/fstab
fi

echo "==> App directory"
install -d -o "${DEPLOY_USER}" -g "${DEPLOY_USER}" /opt/bd-coach

cat <<EOF

Hostinger VPS is ready.

Next steps (as ${DEPLOY_USER}):
  1. Clone your bd-coach repos into /opt/bd-coach
  2. cd /opt/bd-coach/infra && cp .env.example .env
  3. Set BD_COACH_DOMAIN and generate passwords (see docs/HOSTINGER.md)
  4. Point DNS A records at this server's IP (hPanel → DNS or your registrar)
  5. Open hPanel → VPS → Firewall and allow TCP 80 + 443 if ufw alone is not enough
  6. Deploy:
       # 16 GB+ RAM:
       docker compose -f compose/docker-compose.yml -f compose/docker-compose.hostinger.yml up -d
       # 8 GB RAM (slim):
       docker compose -f compose/docker-compose.yml \\
         -f compose/docker-compose.hostinger.yml \\
         -f compose/docker-compose.slim.yml up -d
  7. ./scripts/bootstrap.sh

Server IP: $(curl -4 -s ifconfig.me || hostname -I | awk '{print $1}')
EOF
