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
# APP_DIR is a git checkout owned by whatever user/permissions the main
# deploy pipeline uses (root) - install node_modules as the current
# (root) user rather than sudo -u "$RUN_USER", which would need write
# access to APP_DIR itself just to create node_modules. The systemd
# service only needs read+execute on node_modules, which default perms
# already give it; only runtime/ needs to be writable by RUN_USER.
npm ci --omit=dev
mkdir -p "$APP_DIR/runtime"

# 최초 1회만: 계정 스토어가 비어있으면(파일이 없거나, jobRunner가 서버 기동 시
# 자동 생성한 빈 기본값 그대로면) 확인된 네이버 3계정을 미리 등록해서 Chairman이
# "계정 관리"에서 Blog ID를 손으로 다시 입력할 필요가 없게 한다. 파일에 "accounts": []
# 가 아닌 실제 내용이 있으면(=UI에서 계정을 추가/수정한 적 있으면) 절대 덮어쓰지 않음.
ACCOUNT_STORE="$APP_DIR/runtime/account-categories.json"
if [ ! -f "$ACCOUNT_STORE" ] || grep -q '"accounts": \[\]' "$ACCOUNT_STORE"; then
  echo "=== seeding initial Naver account store (first run only) ==="
  cat > "$ACCOUNT_STORE" <<'ACCTEOF'
{
  "selectedAccountId": "acct_huh0303",
  "accounts": [
    {
      "id": "acct_huh0303",
      "label": "생활의정석",
      "naverId": "",
      "blogId": "huh0303",
      "checked": true,
      "categories": []
    },
    {
      "id": "acct_k_insight_vietnam",
      "label": "부의정석",
      "naverId": "",
      "blogId": "k-insight-vietnam",
      "checked": true,
      "categories": []
    },
    {
      "id": "acct_k_healthcare",
      "label": "헬스의정석 (Blog ID 확인 필요)",
      "naverId": "",
      "blogId": "k-healthcare",
      "checked": true,
      "categories": []
    }
  ]
}
ACCTEOF
fi

chown -R "$RUN_USER":"$RUN_USER" "$APP_DIR/runtime"
chmod -R a+rX "$APP_DIR/node_modules" "$APP_DIR/server" "$APP_DIR/lib" "$APP_DIR/public"

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
