#!/bin/bash

# ========================================
# Production Deployment Script
# Telegram Repair Bot
# ========================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    log_error "Please do not run as root"
    exit 1
fi

log_info "==================================="
log_info "Telegram Repair Bot - Production Deployment"
log_info "==================================="

# Step 1: Check Docker
log_info "Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

log_info "✓ Docker is installed: $(docker --version)"
log_info "✓ Docker Compose is installed: $(docker-compose --version)"

# Step 2: Check .env file
log_info "Checking .env file..."
if [ ! -f ".env" ]; then
    log_warn ".env file not found. Creating from env.example..."
    cp env.example .env
    log_error "Please edit .env file with your configuration and run this script again."
    exit 1
fi

# Step 3: Validate .env
log_info "Validating .env configuration..."
source .env

if [ -z "$BOT_TOKEN" ] || [ "$BOT_TOKEN" == "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-EXAMPLE" ]; then
    log_error "BOT_TOKEN is not set or using example value. Please set real token in .env"
    exit 1
fi

if [ -z "$ADMIN_IDS" ]; then
    log_error "ADMIN_IDS is not set. Please set in .env"
    exit 1
fi

if [ -z "$GROUP_CHAT_ID" ] || [ "$GROUP_CHAT_ID" == "-1001234567890" ]; then
    log_warn "GROUP_CHAT_ID is not set or using example value."
    read -p "Continue without GROUP_CHAT_ID? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

if [ "$DEV_MODE" != "false" ]; then
    log_warn "DEV_MODE is not set to 'false'. This is PRODUCTION deployment!"
    read -p "Continue with DEV_MODE=${DEV_MODE}? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

log_info "✓ Configuration validated"

# Step 4: Backup existing database
if [ -f "bot_database.db" ]; then
    log_info "Creating database backup..."
    backup_dir="data/backups"
    mkdir -p "$backup_dir"
    backup_file="$backup_dir/bot_database_$(date +%Y%m%d_%H%M%S).db"
    cp bot_database.db "$backup_file"
    log_info "✓ Backup created: $backup_file"
fi

# Step 5: Pull latest changes (if in git repo)
if [ -d ".git" ]; then
    log_info "Pulling latest changes from git..."
    git pull origin main || log_warn "Git pull failed or not configured"
fi

# Step 6: Build Docker image
log_info "Building Docker image..."
cd docker
docker-compose -f docker-compose.prod.yml build --no-cache

# Step 7: Apply database migrations
log_info "Applying database migrations..."
docker-compose -f docker-compose.prod.yml run --rm bot alembic upgrade head

# Step 8: Start services
log_info "Starting services..."
docker-compose -f docker-compose.prod.yml up -d

# Step 9: Wait for services to be healthy
log_info "Waiting for services to be healthy..."
sleep 10

# Step 10: Check status
log_info "Checking service status..."
docker-compose -f docker-compose.prod.yml ps

# Step 11: Show logs
log_info "==================================="
log_info "Deployment completed successfully!"
log_info "==================================="
log_info ""
log_info "Useful commands:"
log_info "  View logs:    docker-compose -f docker/docker-compose.prod.yml logs -f bot"
log_info "  Stop:         docker-compose -f docker/docker-compose.prod.yml stop"
log_info "  Restart:      docker-compose -f docker/docker-compose.prod.yml restart"
log_info "  Status:       docker-compose -f docker/docker-compose.prod.yml ps"
log_info ""
log_info "Showing last 50 log lines..."
docker-compose -f docker-compose.prod.yml logs --tail=50 bot

log_info ""
log_info "✓ All done! Bot should be running now."
log_info "Test it by sending /start to your bot in Telegram"

