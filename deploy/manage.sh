#!/usr/bin/env bash
#
# Onshape Export Manager — systemd service management wrapper.
#
# Usage:
#   sudo ./deploy/manage.sh start
#   sudo ./deploy/manage.sh stop
#   sudo ./deploy/manage.sh restart
#   sudo ./deploy/manage.sh status
#   sudo ./deploy/manage.sh enable
#   sudo ./deploy/manage.sh disable
#   sudo ./deploy/manage.sh logs
#
set -euo pipefail

SERVICE_NAME="onshape-export-manager"
COMMAND="${1:-status}"

case "${COMMAND}" in
  start)   systemctl start   "${SERVICE_NAME}" ;;
  stop)    systemctl stop    "${SERVICE_NAME}" ;;
  restart) systemctl restart "${SERVICE_NAME}" ;;
  status)  systemctl --no-pager --full status "${SERVICE_NAME}" ;;
  enable)  systemctl enable  "${SERVICE_NAME}" ;;
  disable) systemctl disable "${SERVICE_NAME}" ;;
  logs)    journalctl -u "${SERVICE_NAME}" -f --no-pager ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|enable|disable|logs}" >&2
    exit 2
    ;;
esac
