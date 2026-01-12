#!/bin/bash
#
# Step 1: System Setup & Dependencies
# Installs Docker, nginx, Python, and system tools
#

set -e  # Exit on any error

echo "=========================================="
echo "BMS Analytics Platform - System Setup"
echo "=========================================="
echo ""

# Update system
echo "📦 Updating system packages..."
apt update && apt upgrade -y

# Install essential tools
echo "🔧 Installing essential tools..."
apt install -y \
    git \
    curl \
    wget \
    nano \
    vim \
    htop \
    ufw \
    certbot \
    python3-certbot-nginx

# Install Docker
echo "🐳 Installing Docker..."
apt install -y docker.io docker-compose
systemctl enable docker
systemctl start docker

# Install Python
echo "🐍 Installing Python 3 and pip..."
apt install -y python3 python3-pip python3-venv

# Install nginx
echo "🌐 Installing nginx..."
apt install -y nginx
systemctl enable nginx
systemctl start nginx

# Configure firewall
echo "🔥 Configuring firewall..."
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

echo ""
echo "✅ System setup complete!"
echo ""
echo "Installed:"
echo "  - Docker: $(docker --version)"
echo "  - Docker Compose: $(docker-compose --version)"
echo "  - Python: $(python3 --version)"
echo "  - nginx: $(nginx -v 2>&1)"
echo ""
