# Emergency Recovery - 2 Minutes

## If you see 502 Bad Gateway:

### Option 1: One-Command Recovery (Recommended)
```bash
ssh root@167.172.54.56 "bash /opt/bms-analytics/recovery.sh"
```

### Option 2: Manual (if script not deployed)
```bash
ssh root@167.172.54.56
systemctl restart bms-dashboard
```

### Option 3: Full Reset (if still broken)
```bash
ssh root@167.172.54.56
swapon /swapfile
cd /opt/bms-analytics && docker-compose up -d
systemctl restart bms-collector
systemctl restart bms-dashboard
systemctl restart bms-filter
```

## If SSH is stuck/unresponsive:
1. Go to https://cloud.digitalocean.com
2. Click your droplet
3. Click "Power" -> "Power cycle"
4. Wait 1 minute
5. Run recovery command above

## Check Status
- Dashboard: https://cloud.birdlab.tech/
- Filter: https://cloud.birdlab.tech/filter/

## Key Files on Server
- App code: `/opt/bms-analytics/`
- Dashboard service: `systemctl status bms-dashboard`
- Collector service: `systemctl status bms-collector`
- InfluxDB: `docker ps` (should show influxdb container)
- Swap: `swapon --show` (should show 2GB)

## Alerts
UptimeRobot monitors https://cloud.birdlab.tech/ and will email you if it goes down.
