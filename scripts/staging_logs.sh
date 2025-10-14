#!/bin/bash
# ========================================
# Показать логи STAGING
# ========================================

SSH_SERVER="${SSH_SERVER:-root@YOUR_SERVER_IP}"
STAGING_DIR="${STAGING_DIR:-~/telegram_repair_bot_staging}"

echo "📋 Получение логов STAGING..."
echo ""

ssh "$SSH_SERVER" "cd $STAGING_DIR/docker && docker compose -f docker-compose.staging.yml logs -f bot"

