# Multi-Tenant Architecture & Security Design
**For: Commercial BMS Analytics Platform**

---

## Overview

Building a **secure multi-tenant platform** where each client can only access their own building(s) data.

**Key Requirements:**
1. ✅ Data isolation (Client A cannot see Client B's data)
2. ✅ White-label capable (custom branding per client)
3. ✅ Scalable (add buildings without infrastructure changes)
4. ✅ Domain flexibility (birdlab.tech or client-branded)
5. ✅ Commercial-grade security

---

## Architecture Design

### Database Layer: InfluxDB with Tenant Tagging

```python
# Every data point includes tenant/building tags
from influxdb_client import Point

point = Point("bms_data") \
    .tag("tenant_id", "bmsi")              # Company/client ID
    .tag("building_id", "bmsi_hq_london")  # Specific building
    .tag("point_type", "temperature")      # Sensor type
    .field("value", 21.5) \
    .time(datetime.utcnow())
```

**Key Principle:** EVERY query MUST filter by `tenant_id`

**Why This Works:**
- InfluxDB tags are indexed (fast filtering)
- Impossible to accidentally query across tenants (enforced at API level)
- Single database can handle hundreds of tenants
- Each tenant can have multiple buildings

---

## Security Implementation

### Layer 1: Authentication (Who are you?)

**JWT Token-Based Auth:**

```python
# auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta

SECRET_KEY = "your-secret-key-from-env"  # Store in environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

security = HTTPBearer()

def create_access_token(tenant_id: str, buildings: list[str]):
    """Create JWT token for a tenant"""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": tenant_id,           # Subject = tenant ID
        "buildings": buildings,      # Buildings they can access
        "exp": expire               # Expiration
    }

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and extract tenant info"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        tenant_id: str = payload.get("sub")
        buildings: list = payload.get("buildings", [])

        if tenant_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        return {"tenant_id": tenant_id, "buildings": buildings}

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### Layer 2: Authorization (What can you access?)

**Query Filtering Middleware:**

```python
# api/main.py
from fastapi import FastAPI, Depends
from influxdb_client import InfluxDBClient
from auth import verify_token

app = FastAPI()

def get_bms_data(
    building_id: str,
    start: datetime,
    end: datetime,
    auth: dict = Depends(verify_token)  # Verify token first
):
    """Get BMS data - ONLY for authorized buildings"""

    tenant_id = auth["tenant_id"]
    authorized_buildings = auth["buildings"]

    # CRITICAL: Verify requested building belongs to this tenant
    if building_id not in authorized_buildings:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied to building {building_id}"
        )

    # Query InfluxDB with tenant_id filter (defense in depth)
    query = f'''
    from(bucket: "bms_data")
        |> range(start: {start.isoformat()}Z, stop: {end.isoformat()}Z)
        |> filter(fn: (r) => r.tenant_id == "{tenant_id}")
        |> filter(fn: (r) => r.building_id == "{building_id}")
    '''

    client = InfluxDBClient(...)
    result = client.query_api().query_data_frame(query)

    return result.to_dict(orient='records')

@app.get("/api/buildings/{building_id}/data")
async def get_building_data(
    building_id: str,
    start: datetime,
    end: datetime,
    auth: dict = Depends(verify_token)
):
    """Public API endpoint - secured by JWT"""
    return get_bms_data(building_id, start, end, auth)
```

**Key Security Principles:**
1. ✅ Token verification on EVERY request
2. ✅ Double-check: token buildings + query filter
3. ✅ No raw SQL/queries from client
4. ✅ All queries filtered by tenant_id at database level

---

## Domain & White-Labeling Strategy

### Option 1: Subdomain Routing (birdlab.tech)

**Use Case:** You own/manage the platform

**Structure:**
```
birdlab.tech                    → Marketing site / main portal
dashboard.birdlab.tech          → Master admin dashboard (you)
bmsi.birdlab.tech              → BMSI client dashboard
lasmercedes.birdlab.tech       → Las Mercedes dashboard
client3.birdlab.tech           → Another client
```

**Implementation:**

```nginx
# nginx configuration
server {
    server_name bmsi.birdlab.tech;

    location / {
        proxy_pass http://localhost:8050;
        proxy_set_header X-Tenant-ID "bmsi";  # Pass tenant to app
    }
}

server {
    server_name lasmercedes.birdlab.tech;

    location / {
        proxy_pass http://localhost:8050;
        proxy_set_header X-Tenant-ID "lasmercedes";
    }
}
```

```python
# In Dash app - detect tenant from subdomain
from dash import Dash
from flask import request

app = Dash(__name__)

@app.server.before_request
def detect_tenant():
    """Extract tenant from subdomain or header"""

    # Option 1: From nginx header
    tenant_id = request.headers.get('X-Tenant-ID')

    # Option 2: From subdomain
    if not tenant_id:
        host = request.host  # e.g., "bmsi.birdlab.tech"
        tenant_id = host.split('.')[0]  # Extract "bmsi"

    # Store in request context for use in callbacks
    request.tenant_id = tenant_id
```

**Pros:**
- ✅ Easy to manage (one SSL cert for *.birdlab.tech)
- ✅ Brandable URLs (looks professional)
- ✅ You control everything
- ✅ Easy to add new clients (just add subdomain)

**Cons:**
- ⚠️ Still says "birdlab.tech" (not fully white-label)
- ⚠️ Requires wildcard DNS setup

---

### Option 2: Custom Client Domains (White-Label)

**Use Case:** Client wants their own branding (e.g., cloud.bmsi.co.uk)

**Structure:**
```
birdlab.tech               → Your main platform
cloud.bmsi.co.uk           → BMSI's branded dashboard
data.bmsi.co.uk            → Alternative BMSI domain
bms.lasmercedes.com        → Las Mercedes dashboard
```

**How It Works:**

1. **Client configures DNS** (CNAME record):
   ```
   cloud.bmsi.co.uk  →  CNAME  →  bmsi.birdlab.tech
   ```

2. **Your nginx handles routing:**
   ```nginx
   server {
       server_name cloud.bmsi.co.uk bmsi.birdlab.tech;

       ssl_certificate /etc/letsencrypt/live/cloud.bmsi.co.uk/fullchain.pem;

       location / {
           proxy_pass http://localhost:8050;
           proxy_set_header X-Tenant-ID "bmsi";
       }
   }
   ```

3. **Dashboard shows client branding:**
   ```python
   # Tenant config
   TENANT_CONFIG = {
       "bmsi": {
           "name": "BMSI Building Analytics",
           "logo": "/static/logos/bmsi.png",
           "primary_color": "#003366",
           "domain": "cloud.bmsi.co.uk"
       },
       "lasmercedes": {
           "name": "Las Mercedes BMS Dashboard",
           "logo": "/static/logos/lasmercedes.png",
           "primary_color": "#00aaff",
           "domain": "bms.lasmercedes.com"
       }
   }

   # In Dash layout
   tenant = request.tenant_id
   config = TENANT_CONFIG[tenant]

   app.layout = html.Div([
       html.Img(src=config["logo"]),
       html.H1(config["name"], style={'color': config["primary_color"]}),
       # ... rest of dashboard
   ])
   ```

**Pros:**
- ✅ **Fully white-labeled** (client's domain, not yours)
- ✅ Professional for enterprise clients
- ✅ Can sell as "your own branded platform"
- ✅ Clients feel they own the solution

**Cons:**
- ⚠️ Requires client to configure DNS
- ⚠️ Need separate SSL cert per domain (free with Let's Encrypt)
- ⚠️ Slight admin overhead per client

**Process to Add Client Domain:**

```bash
# When BMSI wants cloud.bmsi.co.uk:

# 1. They add CNAME in their DNS:
#    cloud.bmsi.co.uk → bmsi.birdlab.tech

# 2. You run (I do this via SSH):
sudo certbot --nginx -d cloud.bmsi.co.uk

# 3. Update nginx config (automatic with certbot)
# 4. Restart nginx
sudo systemctl reload nginx

# Done! cloud.bmsi.co.uk now works with BMSI branding
```

---

### Option 3: Hybrid Approach (Recommended)

**What I Recommend for Your Business:**

1. **Start with subdomains** (birdlab.tech):
   - Quick to set up
   - Easy to onboard clients
   - Professional enough for most clients

2. **Offer custom domains as premium feature:**
   - Small clients: `clientname.birdlab.tech` (included)
   - Enterprise clients: `cloud.clientname.com` (+£5/month setup fee)

3. **Marketing benefits:**
   - "All plans include branded dashboard at yourcompany.birdlab.tech"
   - "Enterprise: Use your own domain (cloud.yourcompany.com)"

---

## Customer/Client Management

### Tenant Database Structure

```python
# Database schema (PostgreSQL)
CREATE TABLE tenants (
    tenant_id VARCHAR(50) PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    primary_domain VARCHAR(255) UNIQUE,  -- bmsi.birdlab.tech
    custom_domain VARCHAR(255),           -- cloud.bmsi.co.uk (optional)
    logo_url VARCHAR(255),
    primary_color VARCHAR(7),
    contact_email VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE buildings (
    building_id VARCHAR(100) PRIMARY KEY,
    tenant_id VARCHAR(50) REFERENCES tenants(tenant_id),
    building_name VARCHAR(255),
    address TEXT,
    zerotier_network_id VARCHAR(50),
    bms_api_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(50) REFERENCES tenants(tenant_id),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255),
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'viewer',  -- admin, viewer
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE access_logs (
    log_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    tenant_id VARCHAR(50),
    building_id VARCHAR(100),
    action VARCHAR(50),
    timestamp TIMESTAMP DEFAULT NOW()
);
```

### Admin Dashboard (For You)

```python
# admin_dashboard.py
from dash import Dash, html, dcc
import plotly.express as px

def admin_overview():
    """Master admin dashboard - see all tenants"""

    tenants = get_all_tenants()

    metrics = {
        "Total Tenants": len(tenants),
        "Total Buildings": sum(t.building_count for t in tenants),
        "Total Data Points": get_total_datapoints(),
        "Active Users": get_active_users_today()
    }

    return html.Div([
        html.H1("Platform Admin Dashboard"),

        # Metrics
        html.Div([
            html.Div([
                html.H3(f"{value:,}"),
                html.P(key)
            ]) for key, value in metrics.items()
        ]),

        # Tenant list
        html.H2("Tenants"),
        html.Table([
            html.Tr([
                html.Th("Company"),
                html.Th("Buildings"),
                html.Th("Domain"),
                html.Th("Status")
            ])
        ] + [
            html.Tr([
                html.Td(t.company_name),
                html.Td(t.building_count),
                html.Td(t.primary_domain),
                html.Td("Active" if t.active else "Inactive")
            ]) for t in tenants
        ])
    ])
```

---

## Security Best Practices

### 1. **Environment Variables** (Never hardcode secrets)

```bash
# .env file (NEVER commit to git)
DATABASE_URL=postgresql://user:pass@localhost/bms_analytics
INFLUXDB_TOKEN=your-token-here
JWT_SECRET_KEY=random-secure-key
ZEROTIER_API_TOKEN=your-zerotier-token
```

```python
# Load from environment
import os
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET_KEY")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
```

### 2. **HTTPS Only** (Let's Encrypt - free SSL)

```bash
# Automatic SSL for all domains
sudo certbot --nginx -d birdlab.tech -d *.birdlab.tech
```

### 3. **Rate Limiting** (Prevent abuse)

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/data")
@limiter.limit("100/hour")  # Max 100 requests per hour per IP
def get_data():
    pass
```

### 4. **Audit Logging** (Track access)

```python
def log_access(user_id, tenant_id, building_id, action):
    """Log every data access for audit trail"""
    conn.execute("""
        INSERT INTO access_logs (user_id, tenant_id, building_id, action)
        VALUES (%s, %s, %s, %s)
    """, (user_id, tenant_id, building_id, action))
```

### 5. **Data Encryption at Rest**

```bash
# InfluxDB encryption
docker run -v /encrypted-volume:/var/lib/influxdb2 influxdb:2.7
```

---

## Comparison: Your Setup vs re:sustain

| Feature | re:sustain (AWS) | Your Setup (VPS) | Winner |
|---------|------------------|------------------|--------|
| **Multi-Tenancy** | DynamoDB partition keys | InfluxDB tags + JWT | 🟰 Tie |
| **Security** | AWS IAM + AppSync | JWT + middleware | 🟰 Tie |
| **White-Labeling** | Separate Grafana orgs | Subdomain routing | ✅ **You** (easier) |
| **Custom Domains** | Complex (Route53 setup) | Simple (nginx CNAME) | ✅ **You** |
| **Cost** | £100-270/building/mo | £6/mo for all | ✅ **You** (95% cheaper) |
| **Flexibility** | AWS ecosystem only | Any tech stack | ✅ **You** |
| **Scaling** | Auto-scales (expensive) | Manual (cheaper) | ⚠️ Depends on size |

---

## Domain Strategy Recommendation

### For Your Business: **Start with birdlab.tech subdomains**

**Phase 1: Launch** (Months 1-6)
```
dashboard.birdlab.tech     → Your admin panel
bmsi.birdlab.tech         → BMSI client
lasmercedes.birdlab.tech  → Las Mercedes
```

**Pricing:**
- Base plan: Subdomain included
- Enterprise: Custom domain (+£10/month or one-time £50 setup)

**Phase 2: Scale** (Months 6-12)
```
bmsi.birdlab.tech         → Still works
cloud.bmsi.co.uk          → BMSI paid for custom domain
bms.lasmercedes.com       → Las Mercedes paid for custom domain
```

**Why This Works:**
1. ✅ Quick to launch (subdomains ready in minutes)
2. ✅ Professional enough for initial clients
3. ✅ Upsell opportunity (custom domains)
4. ✅ Your brand (birdlab.tech) gets visibility
5. ✅ Easy migration path (clients can upgrade later)

---

## Answer to Your Questions

### 1. "How does this compare with re:sustain?"

**Security:** Equivalent (JWT + tenant filtering = AWS IAM)
**Multi-Tenancy:** Equivalent (InfluxDB tags = DynamoDB partitions)
**Cost:** 95% cheaper (£6/mo vs £100-270/mo)
**Flexibility:** Superior (you control everything)

### 2. "Can I white-label with client logos?"

**YES!** Easy to do:
```python
TENANT_LOGOS = {
    "bmsi": "/static/bmsi-logo.png",
    "lasmercedes": "/static/lm-logo.png"
}

# In dashboard
html.Img(src=TENANT_LOGOS[tenant_id])
```

### 3. "Can clients use cloud.bmsi.co.uk?"

**YES!** Process:
1. BMSI adds CNAME: `cloud.bmsi.co.uk → bmsi.birdlab.tech`
2. You run: `certbot --nginx -d cloud.bmsi.co.uk`
3. Done! Their branded domain works

### 4. "Should I use birdlab.tech or client domains?"

**Both!**
- Start with subdomains (yourcompany.birdlab.tech)
- Offer custom domains as premium feature
- Builds your brand while allowing white-label

---

## Next Steps

Ready to proceed with setup? I'll implement:

1. ✅ JWT authentication system
2. ✅ Tenant-aware InfluxDB queries
3. ✅ Subdomain routing (nginx)
4. ✅ White-label dashboard templates
5. ✅ Admin panel for managing clients

**Let's start with birdlab.tech and add custom domains later as needed.**

Sound good?
