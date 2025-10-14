#!/bin/bash
# ========================================
# Показать логи PRODUCTION
# ========================================

SSH_SERVER="${SSH_SERVER:-root@YOUR_SERVER_IP}"
PROD_DIR="${PROD_DIR:-~/telegram_repair_bot}"

echo "📋 Получение логов PRODUCTION..."
echo ""

ssh "$SSH_SERVER" "cd $PROD_DIR/docker && docker compose -f docker-compose.prod.yml logs -f bot"

