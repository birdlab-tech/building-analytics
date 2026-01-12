#!/bin/bash
#
# Step 2: ZeroTier VPN Setup
# Installs ZeroTier and joins your network
#
# IMPORTANT: Edit ZEROTIER_NETWORK_ID before running!
#

set -e

echo "=========================================="
echo "ZeroTier VPN Setup"
echo "=========================================="
echo ""

# ⚠️ EDIT THIS - Add your ZeroTier network ID
ZEROTIER_NETWORK_ID="YOUR_NETWORK_ID_HERE"

if [ "$ZEROTIER_NETWORK_ID" = "YOUR_NETWORK_ID_HERE" ]; then
    echo "❌ ERROR: You must edit this script and set your ZeroTier network ID!"
    echo ""
    echo "Steps:"
    echo "1. Get your ZeroTier network ID from https://my.zerotier.com"
    echo "2. Edit this script: nano $(readlink -f $0)"
    echo "3. Replace YOUR_NETWORK_ID_HERE with your actual network ID"
    echo "4. Run this script again"
    exit 1
fi

# Install ZeroTier
echo "📡 Installing ZeroTier..."
curl -s https://install.zerotier.com | bash

# Wait for service to start
sleep 3

# Join network
echo "🔗 Joining ZeroTier network: $ZEROTIER_NETWORK_ID"
zerotier-cli join $ZEROTIER_NETWORK_ID

# Show status
echo ""
echo "✅ ZeroTier installation complete!"
echo ""
echo "Your ZeroTier address:"
zerotier-cli info

echo ""
echo "⚠️ IMPORTANT NEXT STEPS:"
echo "1. Go to https://my.zerotier.com"
echo "2. Find your network"
echo "3. Authorize this device (it will show as pending)"
echo "4. Once authorized, you'll be able to access the BMS at 192.168.11.128"
echo ""
