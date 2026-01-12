# Quick Domain Setup - cloud.birdlab.tech

Get professional URLs for Dan's demo: no authentication, just clean links!

## URLs After Setup
- **Dashboard**: https://cloud.birdlab.tech/
- **Filter**: https://cloud.birdlab.tech/filter/

## Step 1: Update DNS (5 minutes)

Go to your domain registrar (wherever birdlab.tech is hosted) and add:

```
Type: A Record
Host: cloud (or cloud.birdlab.tech depending on UI)
Value: 167.172.54.56
TTL: 3600
```

Wait a few minutes for DNS to propagate, then test:
```bash
nslookup cloud.birdlab.tech
# Should return: 167.172.54.56
```

## Step 2: Run Setup Script (5-10 minutes)

SSH to the server and run the automated setup:

```bash
ssh digitalocean
cd /opt/bms-analytics
git pull
sudo bash setup-domain.sh
```

The script will:
1. ✅ Check DNS is pointing correctly
2. ✅ Install/verify certbot is installed
3. ✅ Configure nginx with the new routes
4. ✅ Get SSL certificate from Let's Encrypt (free)
5. ✅ Restart all services

## Step 3: Test!

Open in browser:
- https://cloud.birdlab.tech/ → should show dashboard
- https://cloud.birdlab.tech/filter/ → should show filter interface
- http://cloud.birdlab.tech/ → should auto-redirect to HTTPS

## What This Setup Does

- ✅ Professional URLs (no IP addresses, no port numbers)
- ✅ HTTPS with valid SSL certificate
- ✅ Automatic HTTP → HTTPS redirect
- ✅ No authentication (can add later with DOMAIN_AND_AUTH_SETUP.md)
- ✅ Works on any device/network

## What Stays the Same

- Direct access still works:
  - http://167.172.54.56:8050 → dashboard
  - http://167.172.54.56:8051 → filter
- All existing functionality unchanged
- No data loss, no downtime

## Troubleshooting

**DNS not propagating?**
```bash
# Check current DNS
dig +short cloud.birdlab.tech

# If it doesn't show 167.172.54.56, wait a bit longer
# DNS can take 5-60 minutes to propagate worldwide
```

**Certificate error?**
The setup script handles this automatically, but if you see SSL errors:
```bash
sudo certbot certificates
sudo certbot renew --force-renewal
sudo systemctl reload nginx
```

**Can't access the site?**
```bash
# Check nginx is running
sudo systemctl status nginx

# Check logs
sudo tail -f /var/log/nginx/error.log

# Verify firewall allows HTTPS
sudo ufw status | grep 443
sudo ufw allow 443/tcp
```

## Next Steps (Optional)

Want to add authentication and multi-tenancy later?
See **DOMAIN_AND_AUTH_SETUP.md** for:
- Magic link email authentication
- Role-based access control
- Multi-building support (/sackville/, /otherbuilding/, etc.)
- Audit logging

---

**Total time**: ~10-15 minutes
**Cost**: Free (Let's Encrypt SSL is free)
**Maintenance**: SSL auto-renews every 90 days
