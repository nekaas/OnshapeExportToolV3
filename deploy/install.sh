#!/usr/bin/env bash
#
# Onshape Export Manager — Linux / Raspberry Pi installer.
#
# Creates a Python virtual environment, installs dependencies, and installs a
# systemd service that boots into the terminal appliance experience (the web
# server runs in the background).
#
# Usage:
#   sudo ./deploy/install.sh
#   sudo OEM_PORT=8080 OEM_USER=pi OEM_MODE=console ./deploy/install.sh
#
# OEM_MODE:  console (default)  |  server (web-only, no terminal UI)
#
set -euo pipefail

SERVICE_NAME="onshape-export-manager"
PORT="${OEM_PORT:-8080}"
MODE="${OEM_MODE:-console}"

# Resolve the repository root (parent of this script's directory).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${APP_DIR}/.venv"
RUN_USER="${OEM_USER:-${SUDO_USER:-$(id -un)}}"

echo "==> Onshape Export Manager installer"
echo "    App directory : ${APP_DIR}"
echo "    Run as user   : ${RUN_USER}"
echo "    Port          : ${PORT}"
echo "    Mode          : ${MODE}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "This installer must be run as root (use sudo)." >&2
  exit 1
fi

# --- Python & dependencies --------------------------------------------------
PYTHON_BIN="$(command -v python3 || true)"
if [[ -z "${PYTHON_BIN}" ]]; then
  echo "python3 is required but was not found." >&2
  exit 1
fi

echo "==> Creating virtual environment"
"${PYTHON_BIN}" -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/pip" install --upgrade pip
"${VENV_DIR}/bin/pip" install -r "${APP_DIR}/requirements.txt"

# --- systemd unit -----------------------------------------------------------
UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
echo "==> Writing ${UNIT_PATH}"
cat > "${UNIT_PATH}" <<UNIT
[Unit]
Description=Onshape Export Manager Appliance
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${APP_DIR}
Environment=OEM_MODE=${MODE}
Environment=OEM_PORT=${PORT}
# The terminal appliance experience — web server runs in background.
# Set OEM_MODE=server to run as a headless web-only service.
ExecStart=${VENV_DIR}/bin/python ${APP_DIR}/app.py
StandardInput=tty
StandardOutput=journal
TTYPath=/dev/tty1
TTYReset=yes
TTYVHangup=yes
Restart=on-failure
RestartSec=5
# Low-power friendly limits
Nice=5
MemoryMax=512M

[Install]
WantedBy=multi-user.target
UNIT

echo "==> Enabling and starting service"
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service"
systemctl restart "${SERVICE_NAME}.service"

echo
echo "==> Installed. Service status:"
systemctl --no-pager --full status "${SERVICE_NAME}.service" || true

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo
echo "Onshape Export Manager is running."
echo "  Local : http://localhost:${PORT}"
[[ -n "${IP}" ]] && echo "  LAN   : http://${IP}:${PORT}"
echo
echo "Manage with: sudo ${APP_DIR}/deploy/manage.sh {start|stop|restart|status|enable|disable|logs}"
