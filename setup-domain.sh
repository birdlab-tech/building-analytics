#!/bin/bash
# Setup script for cloud.birdlab.tech domain
# Run this on the DigitalOcean droplet

set -e  # Exit on error

echo "=========================================="
echo "Domain Setup: cloud.birdlab.tech"
echo "=========================================="

# Check DNS first
echo ""
echo "Step 1: Checking DNS..."
EXPECTED_IP="167.172.54.56"
CURRENT_IP=$(dig +short cloud.birdlab.tech | head -n 1)

if [ "$CURRENT_IP" != "$EXPECTED_IP" ]; then
    echo "⚠️  WARNING: DNS not pointing to this server yet!"
    echo "   Current: $CURRENT_IP"
    echo "   Expected: $EXPECTED_IP"
    echo ""
    echo "Please update DNS first:"
    echo "  Type: A Record"
    echo "  Host: cloud.birdlab.tech"
    echo "  Value: $EXPECTED_IP"
    echo "  TTL: 3600"
    echo ""
    read -p "Press Enter after DNS is updated, or Ctrl+C to cancel..."

    # Wait for DNS to propagate
    echo "Waiting for DNS propagation..."
    sleep 5
fi

echo "✅ DNS is correctly pointing to $EXPECTED_IP"

# Install certbot if not already installed
echo ""
echo "Step 2: Checking certbot..."
if ! command -v certbot &> /dev/null; then
    echo "Installing certbot..."
    sudo apt update
    sudo apt install -y certbot python3-certbot-nginx
else
    echo "✅ certbot already installed"
fi

# Copy nginx config
echo ""
echo "Step 3: Installing nginx configuration..."
sudo cp /opt/bms-analytics/nginx-cloud-birdlab.conf /etc/nginx/sites-available/cloud-birdlab
sudo ln -sf /etc/nginx/sites-available/cloud-birdlab /etc/nginx/sites-enabled/

# Test nginx config (before SSL)
echo "Testing nginx configuration..."
sudo nginx -t || {
    echo "❌ Nginx configuration test failed!"
    exit 1
}

# Get SSL certificate
echo ""
echo "Step 4: Getting SSL certificate..."
if [ ! -d "/etc/letsencrypt/live/cloud.birdlab.tech" ]; then
    # First, temporarily disable SSL in nginx to get cert
    sudo sed -i 's/listen 443 ssl/listen 443/' /etc/nginx/sites-available/cloud-birdlab
    sudo sed -i 's/ssl_certificate/#ssl_certificate/g' /etc/nginx/sites-available/cloud-birdlab
    sudo systemctl reload nginx

    # Get certificate
    sudo certbot --nginx -d cloud.birdlab.tech --non-interactive --agree-tos --email noreply@birdlab.tech

    # Restore SSL config
    sudo cp /opt/bms-analytics/nginx-cloud-birdlab.conf /etc/nginx/sites-available/cloud-birdlab
    sudo nginx -t && sudo systemctl reload nginx
else
    echo "✅ SSL certificate already exists"
fi

# Dash apps don't need updates - nginx handles path routing
echo ""
echo "Step 5: Applications are ready..."
echo "✅ Dashboard running on port 8050"
echo "✅ Filter running on port 8051"
echo "✅ Nginx will handle path routing"

# Restart services
echo ""
echo "Step 6: Restarting services..."
sudo systemctl restart bms-dashboard
sudo systemctl restart bms-filter
sudo systemctl reload nginx

echo ""
echo "=========================================="
echo "✅ Setup complete!"
echo "=========================================="
echo ""
echo "Your BMS Analytics platform is now available at:"
echo "  Dashboard: https://cloud.birdlab.tech/"
echo "  Filter:    https://cloud.birdlab.tech/filter/"
echo ""
echo "HTTP will automatically redirect to HTTPS"
echo ""
