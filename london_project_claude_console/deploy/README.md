# 런던프로젝트클로드 — 배포 가이드 (VPS)

이 문서는 `london_project_claude_console/`를 기존 Hostinger VPS에 별도 서비스로 올리는 절차입니다.
**`managed_roots`(.github, automation_hub, control_center, scripts, config, deploy, tests, tools,
multilang_quiz)와 완전히 분리된 새 systemd 서비스**로 운영하며, `deploy-to-vps.yml`의 기존
reconciliation 로직(`sync_main.py`)을 건드리지 않습니다. 즉 이 서비스는 **수동으로 별도 배포**해야
하고, `main` 브랜치에 코드가 push된다고 자동으로 뜨지 않습니다 (의도적 — 검증 전 실서비스에 잘못
얹히는 사고 방지).

## 1. 왜 화면이 있는 Chrome이 필요한가

`naverPublisher.js`/`tistoryPublisher.js`는 데스크톱 콘솔과 동일하게 **playwright-core로 실제
Chrome 창을 `headless: false`로 띄우는 방식**을 그대로 씁니다 (코드 변경 없음 — 검증된 로그인/
캡챠/세션-복구 로직을 그대로 신뢰). 데스크톱에서는 사용자 화면에 그 창이 바로 보이지만, 헤드리스
리눅스 VPS에는 화면 자체가 없습니다.

해결책: VPS에 **가상 디스플레이(Xvfb) + VNC 서버(x11vnc) + 웹 브라우저에서 보이는 noVNC**를 올려서,
Chrome은 그 가상 디스플레이에 뜨고, 오너/베트남 직원은 아무 기기의 브라우저로 noVNC 페이지를 열어
그 화면을 보고 마우스/키보드로 로그인·캡챠를 직접 완료합니다. Playwright 실행 코드는 전혀 손대지
않고, "화면을 어디서 보여줄 것인가"만 바꾸는 것이라 가장 안전합니다.

## 2. VPS 패키지 설치 (1회)

```bash
sudo apt-get update
sudo apt-get install -y xvfb x11vnc novnc websockify google-chrome-stable \
  fonts-noto-cjk  # 한글 폰트 - 없으면 네이버 에디터가 깨져 보일 수 있음
```

## 3. systemd 유닛 3개

`/etc/systemd/system/lpc-xvfb.service`
```ini
[Unit]
Description=London Project Claude - virtual display
After=network.target

[Service]
ExecStart=/usr/bin/Xvfb :77 -screen 0 1366x900x24
Restart=always

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/lpc-x11vnc.service`
```ini
[Unit]
Description=London Project Claude - VNC on virtual display
After=lpc-xvfb.service
Requires=lpc-xvfb.service

[Service]
Environment=DISPLAY=:77
# -passwd here (or -rfbauth with a generated file) - never leave VNC open with no password.
ExecStart=/usr/bin/x11vnc -display :77 -forever -shared -rfbport 5977 -passwd CHANGE_ME_VNC_PASSWORD
Restart=always

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/lpc-novnc.service`
```ini
[Unit]
Description=London Project Claude - noVNC websocket bridge
After=lpc-x11vnc.service
Requires=lpc-x11vnc.service

[Service]
ExecStart=/usr/bin/websockify --web=/usr/share/novnc 6077 localhost:5977
Restart=always

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/lpc-console.service` (the Node app itself)
```ini
[Unit]
Description=London Project Claude - web console (Node/Express)
After=network.target lpc-xvfb.service

[Service]
WorkingDirectory=/opt/london-project-claude-console
Environment=DISPLAY=:77
Environment=PORT=8787
Environment=LPC_USER=admin
Environment=LPC_PASS=CHANGE_ME_STRONG_PASSWORD
Environment=BLOGAUTO_RUNTIME_ROOT=/opt/london-project-claude-console/runtime
ExecStart=/usr/bin/node server/server.js
Restart=always
User=lpcconsole

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now lpc-xvfb lpc-x11vnc lpc-novnc lpc-console
```

Naver 로그인/캡챠가 필요한 순간에는, 앱에서 "브라우저 화면 열기" 안내와 함께
`https://<vps-host>:6077/vnc.html?autoconnect=true&resize=scale`
링크를 보여주면 됩니다 (PC/모바일 브라우저 모두 동작). 이 링크는 반드시 nginx에서
TLS + 별도 인증 뒤로 감싸서 노출하세요 (아래 4번).

## 4. nginx reverse proxy (TLS 종단 + 두 서비스 프록시)

```nginx
server {
  listen 443 ssl;
  server_name console.example.com;   # 실제 서브도메인으로 교체

  ssl_certificate     /etc/letsencrypt/live/console.example.com/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/console.example.com/privkey.pem;

  location / {
    proxy_pass http://127.0.0.1:8787;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;   # WebSocket (/ws) 업그레이드 필수
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
  }

  location /vnc/ {
    proxy_pass http://127.0.0.1:6077/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    # noVNC 페이지 자체는 로그인 세션 쿠키를 안 보므로, 반드시 basic auth나
    # IP allowlist 등 별도 보호를 추가할 것 - 아래 참고.
    auth_basic "restricted";
    auth_basic_user_file /etc/nginx/lpc-vnc.htpasswd;
  }
}
```

## 5. 최초 배포 절차

```bash
sudo useradd -r -m -s /usr/sbin/nologin lpcconsole || true
sudo mkdir -p /opt/london-project-claude-console
sudo rsync -a london_project_claude_console/ /opt/london-project-claude-console/ --exclude runtime --exclude node_modules
cd /opt/london-project-claude-console
sudo -u lpcconsole npm install --omit=dev
sudo -u lpcconsole PLAYWRIGHT_BROWSERS_PATH=0 npx --yes playwright install chrome  # 시스템 Chrome 채널 사용 확인
sudo systemctl restart lpc-console
```

## 6. 아직 검증되지 않은 것 (다음 세션에서 확인 필요)

- 실제 VPS에서 Xvfb 위에 뜬 Chrome + noVNC 화면 크기/DPI가 네이버 에디터 좌표 기반 클릭 로직과
  잘 맞는지 (naverPublisher.js는 `viewport: 1366x900` 고정 — Xvfb 해상도와 일치시킴, 실기 테스트 필요).
- 여러 계정을 "동시에" 발행할 때 Xvfb 화면 하나에 Chrome 창이 여러 개 뜨는 상황 처리 (현재 구조는
  데스크톱 콘솔과 동일하게 순차 처리(activeJob 단일 슬롯)를 그대로 유지 — 동시 실행 큐잉은 미구현).
- systemd 유닛의 실제 파일 배치/활성화는 **VPS SSH 접근 권한이 없어 이 세션에서 직접 실행하지
  못했음** — Chairman 또는 GitHub Actions workflow_dispatch를 통한 별도 배포 스텝이 필요.
- LPC_PASS/VNC 비밀번호는 systemd 유닛에 평문으로 넣지 말고 `EnvironmentFile=` + 별도 secrets
  파일(0600, root 소유)로 분리 권장 — 위 예시는 최소 동작 확인용.
