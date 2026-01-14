# Crash Recovery Guide - BMS Analytics Platform

**Purpose**: Step-by-step recovery procedures when things go wrong. Written for Claude to follow in future sessions. User should not need to debug - just run the fixes.

**Last Updated**: 14 January 2026

---

## QUICK RECOVERY (Try This First)

For most issues, this single command fixes everything:

```bash
ssh root@167.172.54.56 "bash /opt/bms-analytics/recovery.sh"
```

Expected output:
```
=== BMS Analytics Recovery ===
Swap: OK
InfluxDB: OK
Restarting services...

=== Status ===
Collector: RUNNING
Dashboard: RUNNING
Filter: RUNNING

Recovery complete. Check https://cloud.birdlab.tech/
```

If this works → Done. Check https://cloud.birdlab.tech/

If SSH fails or hangs → Go to "Server Unresponsive" section below.

---

## Issue: 502 Bad Gateway

**Symptom**: Browser shows "502 Bad Gateway nginx/1.24.0 (Ubuntu)"

**Cause**: Dashboard service crashed (usually OOM - out of memory)

**Fix**:
```bash
ssh root@167.172.54.56 "bash /opt/bms-analytics/recovery.sh"
```

**If that doesn't work**, manually restart:
```bash
ssh root@167.172.54.56 "systemctl restart bms-dashboard"
```

**Check if it's running**:
```bash
ssh root@167.172.54.56 "systemctl status bms-dashboard"
```

Look for "Active: active (running)". If it says "activating (auto-restart)" it's crash-looping - check logs:
```bash
ssh root@167.172.54.56 "journalctl -u bms-dashboard -n 50 --no-pager"
```

---

## Issue: Dashboard Loads But Graph is Blank

**Symptom**: Page loads, header shows "LIVE BMS Time-Series", but graph area is empty/dark

**Possible causes**:
1. InfluxDB not running
2. Collector not running (no new data)
3. No data in database for selected time range

**Diagnostic steps**:

### Check InfluxDB:
```bash
ssh root@167.172.54.56 "docker ps | grep influx"
```
Should show influxdb container. If missing:
```bash
ssh root@167.172.54.56 "cd /opt/bms-analytics && docker-compose up -d"
```

### Check Collector:
```bash
ssh root@167.172.54.56 "systemctl status bms-collector"
```
Should show "active (running)" and recent log entries showing "Wrote XXX data points". If not running:
```bash
ssh root@167.172.54.56 "systemctl restart bms-collector"
```

### Check if data exists:
```bash
ssh root@167.172.54.56 "docker exec influxdb influx query 'from(bucket:\"bms_data\") |> range(start: -1h) |> count()' --org birdlab --token bms-super-secret-token-change-in-production"
```
Should return count data. If empty, wait 5 minutes for collector to gather data.

### Try different time range:
In browser, click "1h" or "3h" buttons to show recent data only.

---

## Issue: Server Unresponsive (SSH Hangs/Timeouts)

**Symptom**: SSH command hangs, doesn't connect, or DigitalOcean console times out

**Cause**: Server is memory-starved and thrashing, or kernel panic

**Fix - Power Cycle via DigitalOcean Dashboard**:

1. Go to https://cloud.digitalocean.com
2. Log in
3. Click on droplet: **ubuntu-s-1vcpu-1gb-lon1-01**
4. Click **Power** (top right area)
5. Click **Turn off** or **Power off**
6. **WAIT** - this can take 3-5 minutes when server is stuck. Be patient.
7. Once status shows "Off", click **Turn on**
8. Wait 1-2 minutes for boot
9. Run recovery script:
```bash
ssh root@167.172.54.56 "bash /opt/bms-analytics/recovery.sh"
```

**IMPORTANT**: Do not repeatedly click power buttons. Wait for each action to complete.

---

## Issue: OOM Killer Terminated Services

**Symptom**: Logs show "A process of this unit has been killed by the OOM killer"

**Cause**: Ran out of memory. Usually because:
- Debug mode was on (doubles memory)
- Swap not enabled
- Too many services running

**Fix**:

### 1. Ensure swap is active:
```bash
ssh root@167.172.54.56 "swapon --show"
```
Should show 2GB swap. If missing:
```bash
ssh root@167.172.54.56 "swapon /swapfile || (fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile)"
```

### 2. Ensure debug mode is OFF:
```bash
ssh root@167.172.54.56 "grep 'debug=True' /opt/bms-analytics/*.py"
```
If any results, fix:
```bash
ssh root@167.172.54.56 "sed -i 's/debug=True/debug=False/g' /opt/bms-analytics/*.py && systemctl restart bms-dashboard bms-filter"
```

### 3. Restart services:
```bash
ssh root@167.172.54.56 "bash /opt/bms-analytics/recovery.sh"
```

---

## Issue: Data Loss / Missing Historical Data

**Symptom**: Graph only shows recent data, historical data missing

**Possible causes**:
1. InfluxDB container was recreated (volume lost)
2. Time range selection in UI
3. Collector was down for extended period

**Diagnosis**:

### Check how much data exists:
```bash
ssh root@167.172.54.56 "docker exec influxdb influx query 'from(bucket:\"bms_data\") |> range(start: -7d) |> count()' --org birdlab --token bms-super-secret-token-change-in-production"
```

### Check collector uptime:
```bash
ssh root@167.172.54.56 "systemctl status bms-collector"
```
Look at "Active: active (running) since XXX" to see when it last started.

**Recovery**: Data that wasn't collected cannot be recovered. Ensure collector stays running for future data.

---

## Issue: Filter Interface Not Working

**Symptom**: https://cloud.birdlab.tech/filter/ returns 502 or doesn't load

**Fix**:
```bash
ssh root@167.172.54.56 "systemctl restart bms-filter && systemctl status bms-filter"
```

**Check filter config exists**:
```bash
ssh root@167.172.54.56 "ls -la /opt/bms-analytics/*.json"
```
Should show `label_filter_configs.json`. If missing, pull from git:
```bash
ssh root@167.172.54.56 "cd /opt/bms-analytics && git pull"
```

---

## Issue: SSL Certificate Problems

**Symptom**: Browser shows certificate warning or HTTPS doesn't work

**Fix** - Renew certificate:
```bash
ssh root@167.172.54.56 "certbot renew && systemctl reload nginx"
```

---

## Issue: Can't Connect to BMS API

**Symptom**: Collector logs show connection errors to 192.168.11.128

**Cause**: ZeroTier VPN not connected (server can't reach local BMS network)

**Fix**:
```bash
ssh root@167.172.54.56 "zerotier-cli status && zerotier-cli listnetworks"
```

Should show "ONLINE" and the network. If offline:
```bash
ssh root@167.172.54.56 "systemctl restart zerotier-one"
```

---

## Issue: Git Pull Fails

**Symptom**: "Your local changes would be overwritten by merge"

**Fix** - Discard local changes and pull:
```bash
ssh root@167.172.54.56 "cd /opt/bms-analytics && git checkout -- . && git pull"
```

---

## Issue: Services Don't Start After Reboot

**Symptom**: After server reboot, services are not running

**Cause**: Services may not be enabled for auto-start, or swap not mounting

**Fix**:
```bash
ssh root@167.172.54.56 "bash /opt/bms-analytics/recovery.sh"
```

**Ensure services are enabled for auto-start**:
```bash
ssh root@167.172.54.56 "systemctl enable bms-dashboard bms-filter bms-collector"
```

---

## Nuclear Option: Full Redeploy

If everything is broken and nothing works, redeploy from scratch:

```bash
ssh root@167.172.54.56 "cd /opt/bms-analytics && git fetch --all && git reset --hard origin/master && docker-compose down && docker-compose up -d && sleep 10 && systemctl restart bms-collector bms-dashboard bms-filter"
```

This will:
- Reset code to match GitHub exactly
- Restart InfluxDB
- Restart all services

**Warning**: This does NOT delete InfluxDB data (stored in Docker volume).

---

## Checklist After Any Recovery

After fixing an issue, verify everything is working:

1. [ ] https://cloud.birdlab.tech/ loads with graph
2. [ ] https://cloud.birdlab.tech/filter/ loads
3. [ ] Graph shows recent data points (within last 5-10 mins)
4. [ ] Run: `ssh root@167.172.54.56 "systemctl is-active bms-dashboard bms-filter bms-collector"`
   - All should say "active"
5. [ ] Run: `ssh root@167.172.54.56 "docker ps | grep influx"`
   - Should show influxdb container

---

## Emergency Contacts / Resources

- **DigitalOcean Dashboard**: https://cloud.digitalocean.com
- **GitHub Repo**: https://github.com/birdlab-tech/building-analytics
- **Server IP**: 167.172.54.56
- **Domain**: cloud.birdlab.tech

---

## Time Estimates for Recovery

| Issue | Expected Fix Time |
|-------|-------------------|
| 502 Bad Gateway (simple restart) | 30 seconds |
| OOM crash + swap fix | 2 minutes |
| Server unresponsive (power cycle) | 5-7 minutes |
| Full redeploy | 5 minutes |
| Debugging unknown issue | Variable - check logs first |
