#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/demo_web"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

sudo mkdir -p "$APP_DIR"
sudo cp -R "$SCRIPT_DIR/.."/* "$APP_DIR/"
sudo python3 -m venv "$APP_DIR/.venv"
sudo "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/backend/requirements.txt"

if [ ! -f "$APP_DIR/backend/.env" ]; then
  sudo cp "$APP_DIR/backend/.env.example" "$APP_DIR/backend/.env"
fi

sudo cp "$APP_DIR/backend/demo-web.service" /etc/systemd/system/demo-web.service
sudo systemctl daemon-reload
sudo systemctl enable demo-web.service
sudo systemctl restart demo-web.service
sudo systemctl --no-pager status demo-web.service
