#!/bin/bash
#
# Step 6: Deploy Dash Dashboard
# Sets up the web dashboard with nginx reverse proxy
#

set -e

echo "=========================================="
echo "Deploy Dash Dashboard"
echo "=========================================="
echo ""

INSTALL_DIR="/opt/bms-analytics"

# Create systemd service for dashboard
echo "⚙️ Creating dashboard service..."
cat > /etc/systemd/system/bms-dashboard.service <<EOF
[Unit]
Description=BMS Analytics Dashboard
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$INSTALL_DIR/venv/bin/python live_timeseries_simple.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
echo "🔄 Reloading systemd..."
systemctl daemon-reload

# Enable and start service
echo "🚀 Starting dashboard service..."
systemctl enable bms-dashboard
systemctl start bms-dashboard

# Wait and check status
sleep 3

if systemctl is-active --quiet bms-dashboard; then
    echo "✅ Dashboard is running on port 8050!"
else
    echo "❌ Dashboard failed to start. Check logs:"
    echo "  journalctl -u bms-dashboard -n 50"
    exit 1
fi

# Configure nginx
echo "🌐 Configuring nginx..."
cat > /etc/nginx/sites-available/bms-analytics <<'EOF'
server {
    listen 80;
    server_name 167.172.54.56;

    location / {
        proxy_pass http://localhost:8050;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/bms-analytics /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test nginx config
echo "🧪 Testing nginx configuration..."
nginx -t

# Reload nginx
echo "🔄 Reloading nginx..."
systemctl reload nginx

echo ""
echo "✅ Dashboard deployment complete!"
echo ""
echo "🌐 Access your dashboard at:"
echo "  http://167.172.54.56"
echo ""
echo "Services running:"
systemctl status bms-dashboard --no-pager -l | head -n 3
echo ""
