# BMS Analytics Platform - Deployment Scripts

Automated deployment scripts for DigitalOcean droplet.

## Prerequisites

- DigitalOcean droplet created (Ubuntu 24.04)
- SSH access as root
- ZeroTier network ID

## Deployment Steps

Run these scripts **in order** on your droplet:

### 1. System Setup (5 minutes)
```bash
bash 01_system_setup.sh
```
Installs: Docker, nginx, Python, firewall

### 2. ZeroTier VPN (2 minutes)
```bash
# FIRST: Edit script and add your ZeroTier network ID
nano 02_zerotier_setup.sh

# Then run:
bash 02_zerotier_setup.sh
```
**After running:** Go to my.zerotier.com and authorize the device!

### 3. InfluxDB Database (3 minutes)
```bash
bash 03_influxdb_setup.sh
```
Starts InfluxDB on port 8086

### 4. Clone GitHub Repo (2 minutes)
```bash
bash 04_clone_repo.sh
```
Downloads your code from GitHub

### 5. Background Collector (2 minutes)
```bash
bash 05_deploy_collector.sh
```
Starts collecting data every 5 minutes

### 6. Dashboard (2 minutes)
```bash
bash 06_deploy_dashboard.sh
```
Deploys dashboard with nginx

## Total Time: ~15-20 minutes

## After Deployment

**Access dashboard:**
- http://167.172.54.56

**Check services:**
```bash
systemctl status bms-collector
systemctl status bms-dashboard
docker ps
```

**View logs:**
```bash
journalctl -u bms-collector -f
journalctl -u bms-dashboard -f
docker logs influxdb
```

## Troubleshooting

**Collector not working:**
```bash
# Check ZeroTier is connected
zerotier-cli status

# Test BMS access
curl -k https://192.168.11.128/rest
```

**Dashboard not loading:**
```bash
# Check if running
systemctl status bms-dashboard

# Check nginx
nginx -t
systemctl status nginx
```

**Database issues:**
```bash
docker logs influxdb
docker restart influxdb
```

## Next Steps

1. Configure domain (birdlab.tech)
2. Set up SSL certificates
3. Add authentication
4. Configure label filtering UI
