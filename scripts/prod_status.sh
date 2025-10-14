#!/bin/bash
# ========================================
# Проверить статус PRODUCTION
# ========================================

SSH_SERVER="${SSH_SERVER:-root@YOUR_SERVER_IP}"
PROD_DIR="${PROD_DIR:-~/telegram_repair_bot}"

echo "🔍 Проверка статуса PRODUCTION..."
echo ""

ssh "$SSH_SERVER" bash -s << 'ENDSSH'
PROD_DIR="${PROD_DIR:-~/telegram_repair_bot}"

cd "$PROD_DIR/docker"

echo "📦 Статус контейнеров:"
docker compose -f docker-compose.prod.yml ps

echo ""
echo "📊 Использование ресурсов:"
docker stats --no-stream $(docker compose -f docker-compose.prod.yml ps -q)

echo ""
echo "🔍 Последние логи (20 строк):"
docker compose -f docker-compose.prod.yml logs --tail=20 bot
ENDSSH

