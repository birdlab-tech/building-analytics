#!/bin/bash
#
# Step 5: Deploy Background Data Collector
# Sets up systemd service to continuously collect BMS data
#
# IMPORTANT: Edit BMS credentials before running!
#

set -e

echo "=========================================="
echo "Deploy Background Data Collector"
echo "=========================================="
echo ""

INSTALL_DIR="/opt/bms-analytics"

# Create configuration file
echo "📝 Creating collector configuration..."
cat > $INSTALL_DIR/.env <<'EOF'
# BMS API Configuration
BMS_URL=https://192.168.11.128/rest
BMS_TOKEN=6r1lkFI2qDKrghg0YaeHMZF1Pbtbloji

# InfluxDB Configuration
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=bms-super-secret-token-change-in-production
INFLUXDB_ORG=birdlab
INFLUXDB_BUCKET=bms_data

# Collector Settings
BUILDING_ID=sackville
TENANT_ID=sackville
POLL_INTERVAL_SECONDS=300
EOF

# Create systemd service
echo "⚙️ Creating systemd service..."
cat > /etc/systemd/system/bms-collector.service <<EOF
[Unit]
Description=BMS Data Collector for Sackville
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$INSTALL_DIR/venv/bin/python live_ingestion.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
echo "🔄 Reloading systemd..."
systemctl daemon-reload

# Enable and start service
echo "🚀 Starting collector service..."
systemctl enable bms-collector
systemctl start bms-collector

# Wait and check status
sleep 3

echo ""
if systemctl is-active --quiet bms-collector; then
    echo "✅ BMS Collector is running!"
    echo ""
    echo "Service status:"
    systemctl status bms-collector --no-pager -l
    echo ""
    echo "To view live logs:"
    echo "  journalctl -u bms-collector -f"
else
    echo "❌ Collector failed to start. Check logs:"
    echo "  journalctl -u bms-collector -n 50"
fi

echo ""
