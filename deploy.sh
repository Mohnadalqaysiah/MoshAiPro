#!/bin/bash
# ================================================
# Mosh AI Pro v5 - Production Deployment Script
# ================================================
# Run this on your VPS after copying the project

set -e

echo "=== Mosh AI Pro v5 - Deployment ==="

# 1. Install Docker if not installed
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "Docker installed. Please logout and login again, then re-run this script."
    exit 0
fi

# 2. Install Docker Compose plugin if not installed
if ! docker compose version &> /dev/null; then
    echo "Installing Docker Compose..."
    sudo apt-get update
    sudo apt-get install -y docker-compose-plugin
fi

# 3. Check .env.prod exists
if [ ! -f "./backend/.env.prod" ]; then
    echo "ERROR: backend/.env.prod not found!"
    echo "Copy backend/.env.prod and fill in your values."
    exit 1
fi

# 4. Build and start
echo "Building images..."
docker compose -f docker-compose.prod.yml build --no-cache

echo "Starting services..."
docker compose -f docker-compose.prod.yml up -d

echo ""
echo "=== Deployment Complete ==="
echo "Your app is running at: http://$(curl -s ifconfig.me)"
echo ""
echo "Check logs with:"
echo "  docker compose -f docker-compose.prod.yml logs -f"
