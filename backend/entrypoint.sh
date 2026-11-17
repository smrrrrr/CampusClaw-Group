#!/bin/sh
# 以 root 启动仅用于修正挂载目录属主，随后立即降权到 appuser 运行应用。
# 这样既保留非 root 运行，又能在新目录/新机器上容忍 Compose 自动创建的 root 属主目录。
set -e
if [ "$(id -u)" = "0" ]; then
  mkdir -p /app/data /app/uploads
  chown -R appuser:appuser /app/data /app/uploads 2>/dev/null || true
  exec setpriv --reuid=appuser --regid=appuser --init-groups "$@"
fi
exec "$@"
