# PythonAnywhere Deployment Guide
**Live BMS Dashboard - Cloud Deployment**

---

## Prerequisites Checklist

### 1. PythonAnywhere Account
- [ ] Create free account at https://www.pythonanywhere.com/registration/register/beginner/
- [ ] Note your username: `_____________`
- [ ] Free tier includes:
  - 1 web app at `<username>.pythonanywhere.com`
  - 512MB disk space
  - SSH access
  - Python 3.8+

### 2. Network Access to BMS
**CRITICAL:** Your BMS is at `https://192.168.11.128/rest` (local network)

PythonAnywhere servers are in the cloud and **cannot** directly access local network addresses.

**Options:**

#### Option A: VPN Access (Recommended for Security)
- Does your organization have a VPN?
- Can PythonAnywhere connect through it?
- May require IT department approval

#### Option B: Expose BMS via Public IP
- Configure router port forwarding: `192.168.11.128:443` → Public IP
- **Security risk** - requires proper firewall rules
- Would give you a URL like: `https://your-public-ip/rest`

#### Option C: Reverse Proxy/Tunnel
- Use service like:
  - **Tailscale** (recommended) - secure mesh VPN
  - **Cloudflare Tunnel** - secure tunnel without port forwarding
  - **ngrok** - quick tunnel for testing
- Provides secure access without exposing BMS directly

#### Option D: On-Premise Deployment
- Run dashboard on a server within the same network as BMS
- Could be:
  - Raspberry Pi / mini PC
  - Dan's office computer
  - Local server
- Access via local network or VPN

### 3. Required Files for Deployment
```
- live_timeseries_simple.py (main dashboard)
- live_api_client.py (BMS API client)
- requirements.txt (Python dependencies)
```

### 4. BMS Configuration
- **URL:** `https://192.168.11.128/rest` (needs to be accessible from cloud)
- **Token:** `6r1lkFI2qDKrghg0YaeHMZF1Pbtbloji`
- **SSL Certificate:** Self-signed (needs verification disabled)

---

## Deployment Steps (Once Network Access is Resolved)

### Step 1: Create PythonAnywhere Account
```bash
# Sign up at:
https://www.pythonanywhere.com/registration/register/beginner/
```

### Step 2: SSH into PythonAnywhere
```bash
# From your local machine:
ssh <your-username>@ssh.pythonanywhere.com
```

### Step 3: Upload Files
**Option A: Via Git (Recommended)**
```bash
# Clone your repository
git clone https://github.com/birdlab-tech/building-analytics.git
cd building-analytics
```

**Option B: Via SCP**
```bash
# From local machine:
scp live_timeseries_simple.py <username>@ssh.pythonanywhere.com:~/
scp live_api_client.py <username>@ssh.pythonanywhere.com:~/
scp requirements.txt <username>@ssh.pythonanywhere.com:~/
```

### Step 4: Install Dependencies
```bash
# On PythonAnywhere SSH session:
pip install --user -r requirements.txt
```

### Step 5: Configure Web App
1. Go to Web tab: https://www.pythonanywhere.com/user/<username>/webapps/
2. Click "Add a new web app"
3. Choose "Flask" framework
4. Python version: 3.10
5. Configure WSGI file (see below)

### Step 6: Create WSGI Configuration
**File:** `/var/www/<username>_pythonanywhere_com_wsgi.py`

```python
import sys
import os

# Add your project directory to the sys.path
project_home = '/home/<username>/building-analytics'
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# Import the Dash app
from live_timeseries_simple import app

# Flask server is the underlying server for Dash
application = app.server
```

### Step 7: Update BMS URL in Code
If using tunnel/public IP, update `live_timeseries_simple.py`:
```python
BMS_CONFIG = {
    'url': 'https://<new-accessible-url>/rest',  # UPDATE THIS
    'token': '6r1lkFI2qDKrghg0YaeHMZF1Pbtbloji'
}
```

### Step 8: Reload Web App
```bash
# Via web interface:
# Go to Web tab → Click "Reload" button

# OR via API:
curl -X POST \
  https://www.pythonanywhere.com/api/v0/user/<username>/webapps/<domain>/reload/ \
  -H "Authorization: Token <your-api-token>"
```

### Step 9: Test Access
```bash
# Visit your dashboard:
https://<username>.pythonanywhere.com
```

---

## Troubleshooting

### Issue: "Connection refused" to BMS
**Problem:** PythonAnywhere cannot reach local network address
**Solution:** Implement one of the network access options above

### Issue: SSL Certificate Error
**Problem:** Self-signed certificate not trusted
**Solution:** Add to `live_api_client.py`:
```python
response = requests.post(url, json=payload, headers=headers, verify=False)
```

### Issue: Web app not reloading
**Problem:** Code changes not visible
**Solution:**
1. Check WSGI configuration
2. Click "Reload" button in Web tab
3. Check error logs in Files tab

### Issue: Import errors
**Problem:** Missing dependencies
**Solution:**
```bash
pip install --user dash plotly pandas requests urllib3
```

---

## Free Tier Limitations

**PythonAnywhere Free Tier:**
- ✅ 1 web app
- ✅ SSH access
- ✅ 512MB storage
- ✅ Python 3.8, 3.9, 3.10
- ❌ Custom domains (paid feature)
- ❌ Always-on tasks (paid feature)
- ⚠️ **CRITICAL:** Can only access whitelisted external sites

**Whitelist Check:**
- Free accounts can only make HTTP/HTTPS requests to whitelisted sites
- Your BMS IP (`192.168.11.128`) is NOT whitelisted
- **You need a paid account ($5/month) for unrestricted external access**
- **OR** use one of the network tunneling solutions

---

## Recommended Approach

### Phase 1: Test with Public Tunnel (Quick)
1. Install **Tailscale** or **ngrok** on the BMS network
2. Get public URL for BMS
3. Deploy to PythonAnywhere free tier
4. Test functionality

### Phase 2: Production Setup (Secure)
1. Upgrade PythonAnywhere to paid tier ($5/month) if needed
2. Set up proper VPN or Cloudflare Tunnel
3. Configure SSL certificates
4. Add authentication to dashboard

### Phase 3: Add Features
1. Permanent data storage (InfluxDB)
2. Label filtering interface
3. Custom domain
4. Alerts and notifications

---

## Cost Estimate

**Minimal Setup (Testing):**
- PythonAnywhere Free: $0/month
- ngrok Free: $0/month
- **Total: $0/month**

**Production Setup (Recommended):**
- PythonAnywhere Hacker: $5/month
- Tailscale Free: $0/month
- **Total: $5/month**

**Full Production:**
- PythonAnywhere Hacker: $5/month
- InfluxDB Cloud Free: $0/month (up to 30 days retention)
- Custom Domain: ~$12/year
- **Total: ~$6/month**

---

## Security Considerations

1. **BMS Token:** Currently hardcoded - consider environment variables
2. **HTTPS:** Ensure tunnel/proxy uses HTTPS
3. **Authentication:** Add password protection to dashboard
4. **Firewall:** Restrict access to BMS to known IPs
5. **VPN:** Recommended for production use

---

## Next Steps

**Immediate Action Required:**
1. Decide on network access method (VPN/Tunnel/Port Forward)
2. Create PythonAnywhere account
3. Test BMS accessibility from external network

**Once Network Access is Confirmed:**
1. I can help deploy via SSH using Claude Code
2. Configure web app
3. Test live data streaming
4. Share public URL

---

## Questions to Answer Before Deployment

1. **Network Access:**
   - Does Dan's organization have VPN?
   - Can we use a tunnel service?
   - Or should we do on-premise hosting?

2. **PythonAnywhere Account:**
   - Do you have an account already?
   - Are you willing to pay $5/month for unrestricted access?

3. **Authentication:**
   - Should dashboard be public or password-protected?
   - Who needs access?

4. **Domain:**
   - Happy with `<username>.pythonanywhere.com`?
   - Or want custom domain like `bms.resustain.tech`?

---

**Let me know the answers and we can proceed with deployment!**
