# Domain and Authentication Setup Guide

This guide documents how to set up `cloud.birdlab.tech` with subdomain routing and magic link authentication.

## Current Setup (As of 2026-01-12)

**Access URLs:**
- Dashboard: http://167.172.54.56
- Filter Interface: http://167.172.54.56:8051
- No authentication required

## Desired Setup

**Access URLs:**
- Dashboard: https://cloud.birdlab.tech/sackville/dashboard/
- Filter Interface: https://cloud.birdlab.tech/sackville/filter/
- Magic link authentication (email-based, no passwords)

---

## Phase 1: Domain Setup (1 hour)

### Step 1: DNS Configuration

Point domain to DigitalOcean droplet:

```
Type: A Record
Host: cloud.birdlab.tech (or cloud)
Value: 167.172.54.56
TTL: 3600
```

**Test DNS:**
```bash
nslookup cloud.birdlab.tech
# Should return 167.172.54.56
```

### Step 2: SSL Certificate (Let's Encrypt)

Install certbot on the droplet:

```bash
ssh digitalocean
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d cloud.birdlab.tech
```

Follow prompts:
- Enter email for renewal notices
- Agree to terms
- Choose to redirect HTTP to HTTPS (option 2)

**Auto-renewal:**
```bash
# Test renewal
sudo certbot renew --dry-run

# Renewal is automated via systemd timer
systemctl list-timers | grep certbot
```

### Step 3: Nginx Configuration

Update nginx config for subdomain routing:

```bash
sudo nano /etc/nginx/sites-available/bms-analytics
```

Replace contents with:

```nginx
server {
    listen 80;
    server_name cloud.birdlab.tech;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name cloud.birdlab.tech;

    # SSL certificates (managed by certbot)
    ssl_certificate /etc/letsencrypt/live/cloud.birdlab.tech/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/cloud.birdlab.tech/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Sackville dashboard (main visualization)
    location /sackville/dashboard/ {
        proxy_pass http://localhost:8050/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Script-Name /sackville/dashboard;
    }

    # Sackville filter interface
    location /sackville/filter/ {
        proxy_pass http://localhost:8051/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Script-Name /sackville/filter;
    }

    # Root redirects to Sackville dashboard
    location = / {
        return 301 /sackville/dashboard/;
    }

    # Future: Other buildings can be added here
    # location /otherbuildling/dashboard/ { ... }
}
```

Test and reload:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

### Step 4: Update Dash Apps for Subpath

Update both dashboard apps to recognize they're served from subpaths.

**For dashboard (live_timeseries_simple.py):**
```python
app = dash.Dash(
    __name__,
    url_base_pathname='/sackville/dashboard/',
    requests_pathname_prefix='/sackville/dashboard/'
)
```

**For filter (filter_points.py):**
```python
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    url_base_pathname='/sackville/filter/',
    requests_pathname_prefix='/sackville/filter/'
)
```

Then restart services:
```bash
sudo systemctl restart bms-dashboard bms-filter
```

---

## Phase 2: Magic Link Authentication (2-3 hours)

### Option A: Flask-Login + SendGrid (Recommended)

**Architecture:**
- Flask-Login for session management
- SendGrid for email delivery
- Redis for magic link token storage
- Nginx auth_request for protecting routes

### Step 1: Install Dependencies

```bash
ssh digitalocean
cd /opt/bms-analytics
source venv/bin/activate
pip install flask-login redis sendgrid
```

Install Redis:
```bash
sudo apt install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### Step 2: Create Authentication Service

Create `auth_service.py`:

```python
"""
Magic Link Authentication Service
Handles email-based authentication without passwords
"""

from flask import Flask, request, redirect, session, render_template_string
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
import redis
import secrets
import time
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

app = Flask(__name__)
app.secret_key = 'CHANGE-THIS-TO-RANDOM-SECRET'  # Generate with: secrets.token_hex(32)

# Redis for storing magic links
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# SendGrid API key (get from https://sendgrid.com)
SENDGRID_API_KEY = 'YOUR_SENDGRID_API_KEY'
FROM_EMAIL = 'noreply@birdlab.tech'

# Authorized users (can be moved to database later)
AUTHORIZED_USERS = {
    'dan@birdlab.tech': {'name': 'Dan', 'role': 'admin'},
    'user@company.com': {'name': 'User', 'role': 'viewer'}
}

class User(UserMixin):
    def __init__(self, email):
        self.id = email
        self.email = email
        self.name = AUTHORIZED_USERS[email]['name']
        self.role = AUTHORIZED_USERS[email]['role']

@login_manager.user_loader
def load_user(email):
    if email in AUTHORIZED_USERS:
        return User(email)
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        # Check if authorized
        if email not in AUTHORIZED_USERS:
            return render_template_string(LOGIN_TEMPLATE,
                error="This email is not authorized to access the system.")

        # Generate magic link token
        token = secrets.token_urlsafe(32)

        # Store token in Redis (expires in 15 minutes)
        redis_client.setex(f'magic:{token}', 900, email)

        # Send magic link email
        magic_link = f"https://cloud.birdlab.tech/auth/verify?token={token}"

        message = Mail(
            from_email=FROM_EMAIL,
            to_emails=email,
            subject='Your login link for BMS Analytics',
            html_content=f'''
            <h2>Login to BMS Analytics</h2>
            <p>Click the link below to log in (expires in 15 minutes):</p>
            <p><a href="{magic_link}" style="display: inline-block; padding: 12px 24px;
               background-color: #007bff; color: white; text-decoration: none;
               border-radius: 4px;">Log In</a></p>
            <p>Or copy this link: {magic_link}</p>
            <p>If you didn't request this, you can safely ignore this email.</p>
            '''
        )

        try:
            sg = SendGridAPIClient(SENDGRID_API_KEY)
            sg.send(message)
            return render_template_string(LOGIN_TEMPLATE,
                success=f"Magic link sent to {email}. Check your inbox!")
        except Exception as e:
            return render_template_string(LOGIN_TEMPLATE,
                error=f"Failed to send email: {str(e)}")

    return render_template_string(LOGIN_TEMPLATE)

@app.route('/auth/verify')
def verify():
    token = request.args.get('token')

    if not token:
        return redirect('/login?error=invalid')

    # Get email from token
    email = redis_client.get(f'magic:{token}')

    if not email:
        return render_template_string(LOGIN_TEMPLATE,
            error="This link has expired or is invalid. Please request a new one.")

    # Delete token (one-time use)
    redis_client.delete(f'magic:{token}')

    # Log user in
    user = User(email)
    login_user(user, remember=True, duration=timedelta(days=30))

    # Redirect to dashboard
    return redirect('/sackville/dashboard/')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

@app.route('/auth/check')
def check_auth():
    """Endpoint for nginx auth_request"""
    from flask_login import current_user
    if current_user.is_authenticated:
        return '', 200
    return '', 401

LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>BMS Analytics - Login</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #1a1a1a;
            color: #e0e0e0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .login-box {
            background: #2d2d2d;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            max-width: 400px;
            width: 100%;
        }
        h1 {
            color: #00aaff;
            margin-top: 0;
        }
        input[type="email"] {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: 1px solid #444;
            border-radius: 4px;
            background: #1a1a1a;
            color: #e0e0e0;
            font-size: 16px;
        }
        button {
            width: 100%;
            padding: 12px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
        }
        button:hover {
            background: #0056b3;
        }
        .error {
            background: #f44336;
            color: white;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 15px;
        }
        .success {
            background: #4caf50;
            color: white;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 15px;
        }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>🔍 BMS Analytics</h1>
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        {% if success %}
        <div class="success">{{ success }}</div>
        {% endif %}
        <form method="POST">
            <p>Enter your email to receive a magic login link:</p>
            <input type="email" name="email" placeholder="your@email.com" required autofocus>
            <button type="submit">Send Magic Link</button>
        </form>
    </div>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8052)
```

### Step 3: Create systemd Service

```bash
sudo nano /etc/systemd/system/bms-auth.service
```

Contents:
```ini
[Unit]
Description=BMS Auth Service
After=network.target redis-server.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/bms-analytics
Environment="PATH=/opt/bms-analytics/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/opt/bms-analytics/venv/bin/python auth_service.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable bms-auth
sudo systemctl start bms-auth
```

### Step 4: Update Nginx for Auth

Add to nginx config:

```nginx
server {
    listen 443 ssl http2;
    server_name cloud.birdlab.tech;

    # ... SSL config ...

    # Auth service
    location /login {
        proxy_pass http://localhost:8052/login;
        # ... proxy headers ...
    }

    location /auth/ {
        proxy_pass http://localhost:8052/auth/;
        # ... proxy headers ...
    }

    location /logout {
        proxy_pass http://localhost:8052/logout;
        # ... proxy headers ...
    }

    # Protected routes - require authentication
    location /sackville/ {
        auth_request /auth/check;
        error_page 401 = /login;

        # Pass through to appropriate service
        location /sackville/dashboard/ {
            proxy_pass http://localhost:8050/;
            # ... proxy headers ...
        }

        location /sackville/filter/ {
            proxy_pass http://localhost:8051/;
            # ... proxy headers ...
        }
    }
}
```

Reload nginx:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## Phase 3: Testing

### Test Domain:
```bash
curl https://cloud.birdlab.tech
# Should redirect to login
```

### Test Authentication Flow:
1. Visit https://cloud.birdlab.tech
2. Should redirect to login page
3. Enter email
4. Check inbox for magic link
5. Click link
6. Should be logged in and redirect to dashboard

### Test Authorization:
```bash
# Try unauthorized email
curl -X POST https://cloud.birdlab.tech/login \
  -d "email=notauthorized@example.com"
# Should get error message
```

---

## Alternative: Supabase Auth (Easier, Managed)

If you prefer not to manage auth yourself:

1. Create account at https://supabase.com
2. Create new project
3. Enable Email authentication
4. Install Supabase client:
   ```bash
   pip install supabase
   ```
5. Use Supabase auth in your apps
6. Configure allowed emails in Supabase dashboard

**Pros:**
- Fully managed (no Redis, SendGrid setup)
- Built-in email templates
- User management UI
- Rate limiting included

**Cons:**
- Dependency on external service
- Slight monthly cost for production use

---

## Security Considerations

1. **Rate Limiting**: Add nginx rate limiting for `/login` endpoint
   ```nginx
   limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

   location /login {
       limit_req zone=login burst=10 nodelay;
       # ...
   }
   ```

2. **HTTPS Only**: Enforce HTTPS everywhere
3. **Session Security**: Use secure, httponly cookies
4. **Token Expiry**: Magic links expire after 15 minutes
5. **One-time Use**: Tokens deleted after use
6. **Email Verification**: Only send to authorized emails

---

## Maintenance

### Add New User:
Edit `AUTHORIZED_USERS` dict in `auth_service.py`:
```python
AUTHORIZED_USERS = {
    'dan@birdlab.tech': {'name': 'Dan', 'role': 'admin'},
    'newuser@company.com': {'name': 'New User', 'role': 'viewer'}
}
```

Then restart service:
```bash
sudo systemctl restart bms-auth
```

### Check Logs:
```bash
# Auth service logs
sudo journalctl -u bms-auth -f

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

### Renew SSL:
Automatic via certbot, but to force renewal:
```bash
sudo certbot renew --force-renewal
sudo systemctl reload nginx
```

---

## Cost Estimate

- **Domain**: £10-15/year (if not already owned)
- **SSL Certificate**: Free (Let's Encrypt)
- **SendGrid**: Free tier (100 emails/day) or $15/month for more
- **Supabase** (if using): Free tier or $25/month for more features
- **Server**: Already paid for

**Total**: £10-15/year (domain only) if using free tiers

---

## Timeline

- **Phase 1 (Domain)**: 1 hour
- **Phase 2 (Auth)**: 2-3 hours
- **Phase 3 (Testing)**: 30 minutes
- **Total**: 3.5-4.5 hours

---

## Support Resources

- **Let's Encrypt**: https://letsencrypt.org/docs/
- **Nginx**: https://nginx.org/en/docs/
- **Flask-Login**: https://flask-login.readthedocs.io/
- **SendGrid**: https://docs.sendgrid.com/
- **Supabase**: https://supabase.com/docs/

---

## Future Enhancements

1. **Multi-tenancy**: Add building selection after login
2. **Role-based access**: Admin vs viewer permissions
3. **Audit logging**: Track who accessed what when
4. **2FA**: Optional two-factor authentication
5. **API access**: Token-based API authentication for integrations
