#!/bin/bash
#
# Step 3: InfluxDB Setup
# Deploys InfluxDB 2.x via Docker
#

set -e

echo "=========================================="
echo "InfluxDB 2.x Setup"
echo "=========================================="
echo ""

# Create directory for InfluxDB data
echo "📁 Creating InfluxDB data directory..."
mkdir -p /opt/influxdb/data
mkdir -p /opt/influxdb/config

# Create docker-compose.yml
echo "📝 Creating InfluxDB Docker configuration..."
cat > /opt/influxdb/docker-compose.yml <<'EOF'
version: '3.8'

services:
  influxdb:
    image: influxdb:2.7
    container_name: influxdb
    restart: always
    ports:
      - "8086:8086"
    volumes:
      - ./data:/var/lib/influxdb2
      - ./config:/etc/influxdb2
    environment:
      - DOCKER_INFLUXDB_INIT_MODE=setup
      - DOCKER_INFLUXDB_INIT_USERNAME=admin
      - DOCKER_INFLUXDB_INIT_PASSWORD=bms-analytics-2026
      - DOCKER_INFLUXDB_INIT_ORG=birdlab
      - DOCKER_INFLUXDB_INIT_BUCKET=bms_data
      - DOCKER_INFLUXDB_INIT_RETENTION=0  # Keep data forever
      - DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=bms-super-secret-token-change-in-production
EOF

# Start InfluxDB
echo "🚀 Starting InfluxDB..."
cd /opt/influxdb
docker-compose up -d

# Wait for InfluxDB to be ready
echo "⏳ Waiting for InfluxDB to start..."
sleep 10

# Check if running
if docker ps | grep -q influxdb; then
    echo ""
    echo "✅ InfluxDB is running!"
    echo ""
    echo "📊 InfluxDB Details:"
    echo "  URL: http://localhost:8086"
    echo "  Username: admin"
    echo "  Password: bms-analytics-2026"
    echo "  Organization: birdlab"
    echo "  Bucket: bms_data"
    echo "  Token: bms-super-secret-token-change-in-production"
    echo ""
    echo "⚠️ SECURITY NOTE:"
    echo "  These are default credentials for initial setup."
    echo "  You should change them via the InfluxDB UI after setup."
    echo ""
    echo "To access InfluxDB UI:"
    echo "  ssh -L 8086:localhost:8086 root@167.172.54.56"
    echo "  Then visit: http://localhost:8086"
else
    echo ""
    echo "❌ InfluxDB failed to start. Check logs:"
    echo "  docker logs influxdb"
fi

echo ""
