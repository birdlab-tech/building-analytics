#!/bin/bash
# BMS Analytics Recovery Script
# Run this if the dashboard is down: sudo bash /opt/bms-analytics/recovery.sh

echo "=== BMS Analytics Recovery ==="

# Check and enable swap if not active
if ! swapon --show | grep -q swapfile; then
    echo "Enabling swap..."
    swapon /swapfile 2>/dev/null || {
        fallocate -l 2G /swapfile
        chmod 600 /swapfile
        mkswap /swapfile
        swapon /swapfile
        grep -q swapfile /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
    }
fi
echo "Swap: OK"

# Start InfluxDB if not running
if ! docker ps | grep -q influxdb; then
    echo "Starting InfluxDB..."
    cd /opt/bms-analytics && docker-compose up -d
    sleep 5
fi
echo "InfluxDB: OK"

# Restart all services
echo "Restarting services..."
systemctl restart bms-collector
systemctl restart bms-dashboard
systemctl restart bms-filter 2>/dev/null

# Wait and check
sleep 3

echo ""
echo "=== Status ==="
systemctl is-active bms-collector && echo "Collector: RUNNING" || echo "Collector: FAILED"
systemctl is-active bms-dashboard && echo "Dashboard: RUNNING" || echo "Dashboard: FAILED"
systemctl is-active bms-filter 2>/dev/null && echo "Filter: RUNNING" || echo "Filter: not configured"

echo ""
echo "Recovery complete. Check https://cloud.birdlab.tech/"
