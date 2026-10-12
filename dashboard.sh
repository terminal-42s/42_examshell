#!/bin/bash
# ==============================================================================
# 42 Examshell - Dashboard Startup Script
# ==============================================================================

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT=5000

echo "🚀 Iniciando 42 Examshell Dashboard & Tutor IA..."
echo "📡 Servidor: http://localhost:${PORT}/"

# Check if server is already running on the port
if curl -s -o /dev/null -w "%{http_code}" "http://localhost:${PORT}/api/latest" 2>/dev/null | grep -q "200"; then
    echo "ℹ️  O Dashboard já está em execução em http://localhost:${PORT}/"
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "http://localhost:${PORT}/" >/dev/null 2>&1 &
    elif command -v open >/dev/null 2>&1; then
        open "http://localhost:${PORT}/" >/dev/null 2>&1 &
    fi
    exit 0
fi

# Open browser in the background after a slight delay
(
    sleep 1.2
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "http://localhost:${PORT}/" >/dev/null 2>&1
    elif command -v open >/dev/null 2>&1; then
        open "http://localhost:${PORT}/" >/dev/null 2>&1
    fi
) &

cd "$BASE_DIR" || exit 1
python3 server.py "$PORT"
