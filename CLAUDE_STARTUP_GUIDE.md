# Claude Startup Guide - BMS Analytics Platform

**Purpose**: This document is for Claude (AI assistant) to read at the start of any session involving the BMS Analytics platform. It contains critical context, known issues, and solutions learned from painful debugging sessions.

**Last Updated**: 14 January 2026

---

## System Overview

- **Platform**: DigitalOcean droplet (1GB RAM, $6/month)
- **IP**: 167.172.54.56
- **Domain**: https://cloud.birdlab.tech/
- **Filter UI**: https://cloud.birdlab.tech/filter/
- **GitHub**: https://github.com/birdlab-tech/building-analytics

### Services Running on Server
| Service | Port | Systemd Unit | Purpose |
|---------|------|--------------|---------|
| Dashboard | 8050 | bms-dashboard | Main Plotly/Dash visualization |
| Filter | 8051 | bms-filter | Point filtering interface |
| Collector | N/A | bms-collector | Background BMS data polling (every 5 mins) |
| InfluxDB | 8086 | Docker container | Time-series database |
| Nginx | 443 | nginx | Reverse proxy with SSL |

---

## Pre-Session Checklist

Before doing ANY work, verify the system is healthy:

### 1. Check if site loads
```
https://cloud.birdlab.tech/
```
- Should see "LIVE BMS Time-Series" header with graph
- If 502 Bad Gateway → See CRASH_RECOVERY.md
- If blank graph but header visible → Data/InfluxDB issue

### 2. Quick server health check (if SSH needed)
```bash
ssh root@167.172.54.56 "free -h && swapon --show && systemctl is-active bms-dashboard bms-collector && docker ps | grep influx"
```

Expected output should show:
- Memory usage (should have ~400MB+ free with swap)
- Swap: 2GB /swapfile
- bms-dashboard: active
- bms-collector: active
- influxdb container running

---

## CRITICAL LESSONS LEARNED (Do Not Repeat These Mistakes)

### 1. Debug Mode = Memory Death
**Problem**: `debug=True` in Dash apps doubles memory usage by spawning reloader process.
**Solution**: ALWAYS ensure production has `debug=False`
**Files affected**:
- `live_timeseries_simple.py` line 522
- `filter_points.py` line 781

If you EVER see debug=True in production, fix it immediately:
```bash
ssh root@167.172.54.56 "sed -i 's/debug=True/debug=False/g' /opt/bms-analytics/*.py && systemctl restart bms-dashboard bms-filter"
```

### 2. Swap is Essential on 1GB Droplet
**Problem**: Without swap, OOM killer terminates services randomly.
**Solution**: 2GB swap file is configured and MUST be permanent.

Verify swap exists:
```bash
ssh root@167.172.54.56 "swapon --show"
```

If missing, recreate:
```bash
ssh root@167.172.54.56 "fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile && grep -q swapfile /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab"
```

### 3. InfluxDB Runs in Docker, NOT Systemd
**Problem**: `systemctl status influxdb` returns "not found" - this is NORMAL.
**Solution**: Check Docker instead:
```bash
ssh root@167.172.54.56 "docker ps | grep influx"
```

Start if missing:
```bash
ssh root@167.172.54.56 "cd /opt/bms-analytics && docker-compose up -d"
```

### 4. JSON Config Files Were in .gitignore
**Problem**: Filter configs weren't deploying because they were gitignored.
**Solution**: `label_filter_configs.json` is now force-added to git. If other config files are missing, check .gitignore and use `git add -f` if needed.

### 5. DigitalOcean Web Console is Terrible for Pasting
**Problem**: The web console intercepts Ctrl+C/V, splits multi-line commands, injects garbage characters.
**Solutions**:
- Use SSH from terminal instead when possible
- For web console: right-click to paste, keep commands on ONE LINE
- If command splits across lines, it may still work - just press Enter
- Press 'q' to exit pagers (like journalctl output)

### 6. Server Can Become Unresponsive When Memory-Starved
**Problem**: If OOM killer is active, SSH and web console may freeze.
**Solution**: Use DigitalOcean dashboard to power cycle:
1. https://cloud.digitalocean.com
2. Click droplet
3. Power → Turn off (wait for it to complete, can take several minutes)
4. Power → Turn on
5. Then run recovery script

---

## SSH Access

### From Windows PowerShell:
```bash
ssh root@167.172.54.56
```

### If SSH hangs or freezes:
- Close the terminal window entirely (this kills the connection)
- Open new terminal and try again
- If server unresponsive, power cycle via DigitalOcean dashboard

### SSH troubleshooting:
- Stuck in pager (journalctl, less, etc)? Press `q`
- Stuck at password prompt? There is no password, uses key auth
- Connection refused? Server may be down, check DigitalOcean dashboard

---

## Deploying Code Changes

### Standard deployment:
```bash
# 1. Commit and push locally (Windows)
cd "C:\Users\ahami\OneDrive\Documents\KCL PhD\ResearchProposal\Independent Building Analytics"
git add -A && git commit -m "Description" && git push

# 2. Pull and restart on server
ssh root@167.172.54.56 "cd /opt/bms-analytics && git pull && systemctl restart bms-dashboard bms-filter bms-collector"
```

### If git pull fails with "local changes would be overwritten":
```bash
ssh root@167.172.54.56 "cd /opt/bms-analytics && git checkout -- . && git pull"
```

---

## Key File Locations

### On Server (/opt/bms-analytics/):
- `live_timeseries_simple.py` - Main dashboard
- `filter_points.py` - Filter interface
- `live_ingestion.py` - Background data collector
- `live_api_client.py` - BMS API wrapper
- `.env` - Credentials (BMS token, InfluxDB config)
- `docker-compose.yml` - InfluxDB container config
- `recovery.sh` - One-command recovery script
- `label_filter_configs.json` - Filter presets

### Systemd service files:
- `/etc/systemd/system/bms-dashboard.service`
- `/etc/systemd/system/bms-filter.service`
- `/etc/systemd/system/bms-collector.service`

### Nginx config:
- `/etc/nginx/sites-available/cloud-birdlab`

---

## InfluxDB Credentials

From `/opt/bms-analytics/.env`:
```
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=bms-super-secret-token-change-in-production
INFLUXDB_ORG=birdlab
INFLUXDB_BUCKET=bms_data
```

Query example:
```bash
docker exec influxdb influx query 'from(bucket:"bms_data") |> range(start: -1h) |> count()' --org birdlab --token bms-super-secret-token-change-in-production
```

---

## Data Retention

- Dashboard default view: 24 hours (configurable via TIME_WINDOW)
- InfluxDB retention: Unlimited (stored on disk)
- Collector polls every 5 minutes (POLL_INTERVAL_SECONDS=300)
- Data survives service restarts
- Data survives server reboots (stored in Docker volume)
- Data MAY be lost if Docker volume is deleted or corrupted

---

## Monitoring (Manual)

**No automated alerting is configured** (UptimeRobot free tier is a scam - don't waste time on it).

Manual checks:
- Bookmark: https://cloud.birdlab.tech/
- If user reports it's down, go straight to CRASH_RECOVERY.md

---

## Common User Requests and How to Handle

### "The dashboard is down / 502 error"
→ See CRASH_RECOVERY.md, run recovery script

### "The graph is blank but page loads"
→ Check InfluxDB is running, check collector is running, may need to wait 5 mins for data

### "I lost my filter settings"
→ Filter configs are in label_filter_configs.json - ensure it's deployed

### "Can we add another building?"
→ Requires multi-tenant setup, new collector instance, separate discussion

### "Why is it slow?"
→ 1GB droplet is minimal, consider upgrading to 2GB if issues persist

---

## DO NOT DO THESE THINGS

1. **DO NOT** enable debug=True in production
2. **DO NOT** run commands that consume lots of memory (like loading all data at once)
3. **DO NOT** delete the swap file
4. **DO NOT** waste time on UptimeRobot - it's a paid service disguised as free
5. **DO NOT** try to run interactive commands (git rebase -i, vim, nano) via web console
6. **DO NOT** assume systemctl status influxdb will work - it's Docker, not systemd
