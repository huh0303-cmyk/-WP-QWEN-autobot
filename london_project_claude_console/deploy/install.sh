#!/usr/bin/env bash
# 런던프로젝트클로드 웹 콘솔 - VPS 최초 설치/업데이트 스크립트 (idempotent).
# Runs on the VPS itself, invoked by .github/workflows/deploy-london-project-claude-console.yml
# via the same SSH secrets deploy-to-vps.yml already uses (VPS_HOST/VPS_USER/VPS_SSH_PRIVATE_KEY).
#
# Does NOT touch managed_roots or /opt/korea365's guarded reconciliation - this app runs as its
# own systemd services, entirely separate from the korea365-* services.
#
# Required env vars when invoked: APP_DIR, LPC_USER, LPC_PASS, VNC_PASSWORD
set -euo pipefail

APP_DIR="${APP_DIR:?APP_DIR is required}"
LPC_USER="${LPC_USER:?LPC_USER is required}"
LPC_PASS="${LPC_PASS:?LPC_PASS is required}"
VNC_PASSWORD="${VNC_PASSWORD:?VNC_PASSWORD is required}"
DISPLAY_NUM="${DISPLAY_NUM:-:77}"
VNC_PORT="${VNC_PORT:-5977}"
NOVNC_PORT="${NOVNC_PORT:-6077}"
APP_PORT="${APP_PORT:-8787}"
RUN_USER="${RUN_USER:-lpcconsole}"

echo "=== [1/6] apt packages ==="
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y xvfb x11vnc novnc websockify fonts-noto-cjk curl gnupg ca-certificates

if ! command -v google-chrome-stable >/dev/null 2>&1; then
  curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg
  echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
    > /etc/apt/sources.list.d/google-chrome.list
  apt-get update -y
  apt-get install -y google-chrome-stable
fi

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "npm still missing after nodesource install - falling back to distro package"
  apt-get install -y npm
fi
command -v node && node --version
command -v npm && npm --version

echo "=== [2/6] service user ==="
id -u "$RUN_USER" >/dev/null 2>&1 || useradd -r -m -s /usr/sbin/nologin "$RUN_USER"

echo "=== [3/6] app dependencies ==="
cd "$APP_DIR"
sudo -u "$RUN_USER" npm ci --omit=dev
mkdir -p "$APP_DIR/runtime"
chown -R "$RUN_USER":"$RUN_USER" "$APP_DIR/runtime"

echo "=== [4/6] EnvironmentFile (credentials live only here, root-readable only) ==="
install -d -m 700 /etc/london-project-claude-console
cat > /etc/london-project-claude-console/env <<EOF
PORT=$APP_PORT
DISPLAY=$DISPLAY_NUM
LPC_USER=$LPC_USER
LPC_PASS=$LPC_PASS
BLOGAUTO_RUNTIME_ROOT=$APP_DIR/runtime
EOF
chmod 600 /etc/london-project-claude-console/env
chown root:root /etc/london-project-claude-console/env

echo "=== [5/6] systemd units ==="
cat > /etc/systemd/system/lpc-xvfb.service <<EOF
[Unit]
Description=London Project Claude - virtual display
After=network.target

[Service]
ExecStart=/usr/bin/Xvfb $DISPLAY_NUM -screen 0 1366x900x24
Restart=always

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/lpc-x11vnc.service <<EOF
[Unit]
Description=London Project Claude - VNC on virtual display
After=lpc-xvfb.service
Requires=lpc-xvfb.service

[Service]
Environment=DISPLAY=$DISPLAY_NUM
ExecStart=/usr/bin/x11vnc -display $DISPLAY_NUM -forever -shared -rfbport $VNC_PORT -passwd $VNC_PASSWORD
Restart=always

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/lpc-novnc.service <<EOF
[Unit]
Description=London Project Claude - noVNC websocket bridge
After=lpc-x11vnc.service
Requires=lpc-x11vnc.service

[Service]
ExecStart=/usr/bin/websockify --web=/usr/share/novnc $NOVNC_PORT localhost:$VNC_PORT
Restart=always

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/lpc-console.service <<EOF
[Unit]
Description=London Project Claude - web console (Node/Express)
After=network.target lpc-xvfb.service

[Service]
WorkingDirectory=$APP_DIR
EnvironmentFile=/etc/london-project-claude-console/env
ExecStart=/usr/bin/node server/server.js
Restart=always
User=$RUN_USER

[Install]
WantedBy=multi-user.target
EOF

echo "=== [6/6] enable + (re)start ==="
systemctl daemon-reload
systemctl enable lpc-xvfb lpc-x11vnc lpc-novnc lpc-console >/dev/null
systemctl restart lpc-xvfb
sleep 1
systemctl restart lpc-x11vnc lpc-novnc lpc-console

sleep 2
systemctl is-active lpc-xvfb lpc-x11vnc lpc-novnc lpc-console
echo "=== deploy OK ==="
