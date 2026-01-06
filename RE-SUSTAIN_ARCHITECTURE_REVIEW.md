# re:sustain AWS Architecture Review
**For: Independent Building Analytics Platform Design**
**Date: January 2026**
**Purpose: Understand what to learn from and what to avoid**

---

## Executive Summary

re:sustain has built a comprehensive AWS-based platform for building analytics. Their architecture is **enterprise-grade but complex and expensive**. For your independent PhD research platform, you can achieve similar functionality with **simpler, more flexible tools** while maintaining clear IP boundaries.

**Key Insight:** The Grafana → Plotly/Claude Code shift you're proposing is exactly the right move for research flexibility.

---

## 1. DATA FLOW ARCHITECTURE

### re:sustain's Current Flow

```
Building BMS
    ↓
[re:mote Box] (Teltonika RUT router + ZeroTier VPN)
    ↓
[AWS VPN Gateway]
    ↓
[S3 Raw Storage] → [DynamoDB] ← [AppSync GraphQL API]
    ↓                    ↓              ↓
[Athena Queries]   [Definitions]   [Portal/Grafana]
                       ↓
              [Digital Twin Engine]
```

### Key Components Breakdown

#### **1. Edge Hardware: re:mote Box**
- **Hardware:** Teltonika RUT955/RUT956 industrial router
- **Connectivity:** 4G SIM (Jola), WiFi, or Ethernet (with failover)
- **VPN:** ZeroTier for secure tunneling
- **Purpose:** Acts as gateway between BMS network and cloud

**What They Do Well:**
- Redundant connectivity (SIM failover is smart)
- ZeroTier makes remote access simple
- Industrial-grade hardware = reliability

**What to Learn:**
- You need secure remote access to BMS data
- Your friend can handle BMS APIs, but you'll need a similar "bridge" solution
- Could be simpler: Raspberry Pi + Tailscale/ZeroTier + Python

---

#### **2. Data Storage Layer**

**S3 (Raw Data Lake)**
- BMS data stored as JSON/Parquet in S3 buckets
- Organized by: `customer → installation_id → year → month → day → hour`
- Used for long-term storage and Athena queries

**DynamoDB (Operational Database)**
- NoSQL key-value store
- **Tables:**
  - `bms_data` - Real-time sensor values
  - `bms_definitions` - Metadata about what each point represents
  - `digital_twin_definitions` - Simulation model mappings
  - `customer_data` - Building metadata

**Partition Key Strategy:**
- Primary: `installation_id`
- Sort Key: `timestamp` (for time-series queries)

**What They Do Well:**
- DynamoDB handles high-velocity writes (thousands of points/second)
- S3 is dirt cheap for historical data
- Athena lets them run SQL on S3 without loading into DB

**What to Avoid:**
- **Vendor lock-in:** DynamoDB only works on AWS
- **Complexity:** Need to manage dual storage (hot DynamoDB + cold S3)
- **Cost:** DynamoDB gets expensive at scale (pay per read/write)

**Your Alternative:**
```python
# Simple Python-based time-series stack
InfluxDB or TimescaleDB (PostgreSQL extension)
    ↓
Single database for both real-time + historical
    ↓
Pandas DataFrames → Plotly dashboards
```

**Why This Works Better for You:**
- InfluxDB designed for time-series (BMS = time-series)
- Runs locally or on cheap VPS
- Direct Pandas integration = Claude Code can help with analysis
- No AWS bills during development

---

#### **3. API Layer: AWS AppSync (GraphQL)**

**What re:sustain Exposes:**
```graphql
# Get BMS data
getBmsData(
  installation_id: ID!
  date_from: AWSDate!
  date_to: AWSDate!
  definitions: [String]!
): BMSData

# Get latest readings (real-time)
getLatestReadings(
  installation_id: ID!
  resustain_definitions: [String]!
): BMSReadingData

# Get digital twin data
getDigitalTwinData(
  project_id: ID!
  date_from: AWSDate!
  date_to: AWSDate!
): DigitalTwinData
```

**What They Do Well:**
- GraphQL = clients request exactly what they need (efficient)
- Separate APIs for OIDC (portal) vs API Key (internal)
- Strongly typed schema

**What to Avoid:**
- AWS AppSync = vendor lock-in
- Need AWS expertise to configure
- Overkill for research/prototyping

**Your Alternative:**
```python
# FastAPI or Flask + SQLAlchemy
from fastapi import FastAPI
import pandas as pd

app = FastAPI()

@app.get("/bms/{installation_id}")
async def get_bms_data(
    installation_id: str,
    start: datetime,
    end: datetime,
    points: list[str] = None
):
    # Query InfluxDB
    df = client.query_data(installation_id, start, end, points)
    return df.to_dict(orient='records')

@app.get("/live/{installation_id}")
async def get_live_data(installation_id: str):
    # WebSocket for real-time streaming
    return StreamingResponse(...)
```

**Advantages:**
- Full control
- Python ecosystem (Pandas, NumPy, SciPy)
- Easy to deploy (Docker)
- Claude Code can help write endpoints

---

#### **4. Visualization: Grafana (Current) vs Your Approach**

**What re:sustain Uses Grafana For:**
- HVAC engineers monitor live BMS data
- Pre-built dashboards for AHUs, chillers, boilers
- Alerting when values go out of range

**Why They're Stuck With It:**
- It works
- Engineers trained on it
- Changing tools = retraining + rebuild

**Your Better Approach: Plotly + Dash + Jupyter**

```python
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import cufflinks as cf

# Interactive time-series with Plotly
fig = make_subplots(
    rows=3, cols=1,
    shared_xaxes=True,
    subplot_titles=('Supply Air Temp', 'Static Pressure', 'Chiller Power')
)

# Add traces programmatically
for sensor in bms_data:
    fig.add_trace(
        go.Scatter(x=sensor.time, y=sensor.value, name=sensor.label),
        row=sensor.row, col=1
    )

fig.update_layout(height=800, showlegend=True)
fig.show()

# Can also use Cufflinks for quick viz
df.iplot(kind='scatter', x='timestamp', y=['temp', 'pressure'])
```

**Why This Is Better for Research:**
1. **Programmatic Control:** Claude Code can generate viz code on demand
2. **Flexibility:** Not locked into Grafana's dashboard paradigm
3. **Jupyter Integration:** Analysis + viz in same notebook
4. **Publication-Ready:** Plotly outputs look professional
5. **Interactivity:** Built-in zoom, pan, hover, export

**Example Use Case:**
```python
# Ask Claude: "Show me correlation between outside air temp
# and chiller power for January 2026"

# Claude generates:
df_jan = influx.query("""
  SELECT oat, chiller_power
  FROM bms_data
  WHERE time >= '2026-01-01' AND time < '2026-02-01'
""")

fig = px.scatter(df_jan, x='oat', y='chiller_power',
                 trendline='ols', title='OAT vs Chiller Power')
fig.show()

# Get correlation coefficient
correlation = df_jan.corr()['oat']['chiller_power']
print(f"Correlation: {correlation:.3f}")
```

**You can't do this with Grafana** - it's a monitoring tool, not an analysis environment.

---

## 2. DATA MODEL PATTERNS

### re:sustain's "Definitions" Concept

This is **the core innovation** of their platform:

```json
// Raw BMS Point Label (inconsistent, vendor-specific)
"AHU_01_SAT_SP"

// Gets mapped to re:sustain definition (standardized)
{
  "resustain_definition": "ahu_01.supply_air.temperature.setpoint",
  "installation_id": "91dd251f-...",
  "object_id": "12345",
  "unit": "°C",
  "type": "setpoint",
  "system": "ahu",
  "component": "supply_air",
  "measurement": "temperature"
}
```

**Why This Matters:**
- Every building uses different naming (AHU1_SAT vs SAT_AHU_01 vs SupplyAirTemp1)
- re:sustain normalizes to predictable schema
- Enables cross-building analytics

**This Aligns With Your PhD Research Proposal!**

From your proposal (page 9-10):
> "Categorical, Logical, Numerical, Nominal, Consequential" interrogation methods

You're planning to **automate this mapping** - re:sustain still does it manually.

**For Your Platform:**
```python
# Your research contribution: automated point identification
from building_informatics import BMSInterrogator

interrogator = BMSInterrogator()
niagara_bog = interrogator.parse_file("backup.bog")

# Categorical identification
ahus = interrogator.identify_ahus(niagara_bog)

# Logical interrogation (trifurcation - your method)
for ahu in ahus:
    supply_temp = interrogator.find_trifurcation(
        ahu, point_type="AI",
        setpoint_range=(15, 30),
        connected_to="heating_coil_valve"
    )

# Store in standardized format
standardized_points = {
    "ahu_01.supply_air.temperature.sensor": supply_temp,
    "ahu_01.supply_air.temperature.setpoint": setpoint,
    # ...
}
```

**IP Protection:** This automation is YOUR contribution, not re:sustain's.

---

## 3. WHAT TO LEARN FROM RE:SUSTAIN

### ✅ Good Ideas Worth Adopting

1. **Time-Series Partitioning**
   - Organize data by: building → year → month → day
   - Makes queries fast and storage scalable

2. **Separation of Real-Time vs Historical**
   - Hot path: last 24-48 hours in fast DB
   - Cold path: older data in cheaper storage

3. **Standardized Naming Convention**
   - `system.component.measurement.type`
   - Example: `ahu_01.supply_air.temperature.sensor`

4. **API-First Design**
   - Don't tie viz directly to database
   - API layer = flexibility to change backend

5. **Multi-Tenant from Day 1**
   - Even though you'll start with one building, structure for many
   - `installation_id` in every table/query

### ❌ What to Avoid (AWS Lock-In)

1. **DynamoDB** → Use PostgreSQL + TimescaleDB
2. **AppSync** → Use FastAPI (Python)
3. **Athena** → Use DuckDB (query Parquet files locally)
4. **Lambda** → Just run Python scripts/services
5. **CloudWatch** → Use Python logging + local monitoring

---

## 4. RECOMMENDED ARCHITECTURE FOR YOUR PLATFORM

### Minimal Viable Research Stack

```
BMS APIs (handled by your friend)
    ↓
[Python Ingestion Script]
    ↓
[InfluxDB 2.x] (time-series database)
    ↓
[FastAPI] (REST API)
    ↓
[Jupyter + Plotly] (analysis & viz)
    ↑
[Claude Code] (generate analysis code on demand)
```

### Technology Choices

| Component | re:sustain Uses | You Should Use | Why |
|-----------|----------------|----------------|-----|
| Edge Gateway | Teltonika RUT | RPi + Python | Cheaper, you control code |
| VPN | ZeroTier | Tailscale/ZeroTier | Same approach works |
| Time-Series DB | DynamoDB + S3 | InfluxDB/TimescaleDB | Purpose-built for this |
| API | AWS AppSync | FastAPI | Python-native, no AWS |
| Visualization | Grafana | Plotly/Dash | Programmatic control |
| Notebooks | N/A | Jupyter | Research documentation |
| Deployment | AWS Lambda | Docker + VPS | Cheaper, portable |

### Sample Code: Data Ingestion

```python
# bms_ingestion.py
from influxdb_client import InfluxDBClient, Point
from datetime import datetime
import requests

class BMSIngestor:
    def __init__(self, influx_url, token, org, bucket):
        self.client = InfluxDBClient(url=influx_url, token=token, org=org)
        self.write_api = self.client.write_api()
        self.bucket = bucket

    def ingest_point(self, installation_id, point_name, value, timestamp=None):
        """Write a BMS point value to InfluxDB"""
        point = Point("bms_data") \
            .tag("installation", installation_id) \
            .tag("point", point_name) \
            .field("value", float(value)) \
            .time(timestamp or datetime.utcnow())

        self.write_api.write(bucket=self.bucket, record=point)

    def fetch_from_bms_api(self, api_url, installation_id):
        """Fetch latest data from BMS API (your friend provides this)"""
        response = requests.get(f"{api_url}/installations/{installation_id}/points")
        data = response.json()

        for point in data['points']:
            self.ingest_point(
                installation_id=installation_id,
                point_name=point['name'],
                value=point['value'],
                timestamp=point['timestamp']
            )
```

### Sample Code: Analysis with Plotly

```python
# analysis.py
import plotly.express as px
from influxdb_client import InfluxDBClient
import pandas as pd

def analyze_ahu_performance(installation_id, start_date, end_date):
    """
    Analyze AHU performance over date range
    Claude Code can generate queries like this on demand
    """

    # Query InfluxDB
    query = f'''
    from(bucket: "bms_data")
        |> range(start: {start_date}, stop: {end_date})
        |> filter(fn: (r) => r.installation == "{installation_id}")
        |> filter(fn: (r) => r.point =~ /ahu_01.*/)
    '''

    client = InfluxDBClient(...)
    result = client.query_api().query_data_frame(query)

    # Convert to wide format for analysis
    df = result.pivot(index='_time', columns='point', values='_value')

    # Create multi-panel visualization
    fig = px.line(df,
                  y=['supply_air_temp', 'return_air_temp', 'outside_air_temp'],
                  title='AHU-01 Temperature Profile')
    fig.show()

    # Statistical analysis
    correlation = df.corr()
    return correlation
```

---

## 5. DEVELOPMENT ROADMAP

### Phase 1: Local Prototype (Weeks 1-4)

**Goal:** Get BMS data flowing to local database and visualized

1. Set up InfluxDB locally (Docker)
2. Create mock BMS data generator
3. Build ingestion script
4. Create first Plotly dashboard
5. Test with Claude Code for query generation

**No AWS needed yet - everything local**

### Phase 2: Single Building Integration (Weeks 5-8)

**Goal:** Connect to real BMS via your friend's APIs

1. Deploy Raspberry Pi at test building
2. Configure secure tunnel (Tailscale)
3. Ingest real data
4. Validate data quality
5. Build automated point identification (your PhD contribution)

### Phase 3: Analysis Tools (Weeks 9-12)

**Goal:** Reproduce re:sustain analytics independently

1. Digital twin data integration
2. Occupancy tracking (CO₂ method)
3. Automated reporting
4. Model calibration framework

### Phase 4: Scale & Polish (Months 4-6)

**Goal:** Production-ready for multiple buildings

1. Deploy to VPS (Hetzner/DigitalOcean)
2. Add authentication
3. Multi-tenant support
4. API documentation

---

## 6. COST COMPARISON

### re:sustain's AWS Costs (Estimated per building/month)

- DynamoDB: £50-150 (depending on traffic)
- S3: £5-10
- Athena queries: £10-30
- AppSync: £20-40
- Lambda: £10-20
- Data transfer: £10-20
- **Total: £105-270/month/building**

### Your Independent Platform (Estimated)

- Hetzner VPS (8GB RAM): £8/month
- InfluxDB Cloud (if needed): £0-50/month
- Domain + SSL: £2/month
- **Total: £10-60/month (for ALL buildings)**

**Savings: 80-95% reduction in infrastructure costs**

---

## 7. KEY ADVANTAGES OF YOUR APPROACH

### For PhD Research:

1. **Full Data Access:** No API rate limits
2. **Experimentation:** Can modify database schema freely
3. **Reproducibility:** Everything in code/Jupyter notebooks
4. **IP Protection:** Completely separate stack = clear boundaries
5. **Claude Code Integration:** Generate analysis code on demand

### For Commercial Potential:

1. **Lower OpEx:** Cheaper to run than re:sustain's AWS
2. **Portability:** Not locked to AWS, can run anywhere
3. **Transparency:** Clients can inspect all code
4. **Customization:** Easy to modify for specific building types

---

## 8. SAMPLE GITHUB REPO STRUCTURE

```
birdlab-tech/building-analytics/
├── README.md
├── docker-compose.yml          # InfluxDB + Grafana + API
├── requirements.txt
├── .env.example
│
├── ingestion/
│   ├── bms_connector.py       # Connect to BMS APIs
│   ├── niagara_parser.py      # Parse .bog files (your PhD work)
│   ├── trend_parser.py        # Parse .iq2 files
│   └── influx_writer.py       # Write to InfluxDB
│
├── api/
│   ├── main.py               # FastAPI app
│   ├── models.py             # Pydantic models
│   └── routes/
│       ├── bms.py
│       ├── buildings.py
│       └── analytics.py
│
├── analysis/
│   ├── notebooks/            # Jupyter notebooks
│   │   ├── 01_data_exploration.ipynb
│   │   ├── 02_ahu_analysis.ipynb
│   │   └── 03_occupancy_tracking.ipynb
│   │
│   └── scripts/
│       ├── point_identification.py    # Your categorical/logical methods
│       ├── dt_calibration.py         # Digital twin automation
│       └── reporting.py
│
├── visualization/
│   ├── dash_app.py           # Plotly Dash dashboard
│   └── templates/
│
└── tests/
    ├── test_ingestion.py
    └── test_api.py
```

---

## 9. QUESTIONS TO ASK YOUR BMS FRIEND

Since he's handling the BMS API layer, clarify:

1. **Data Format:** JSON? CSV? Real-time stream or polling?
2. **Authentication:** API keys? OAuth? VPN required?
3. **Update Frequency:** Every minute? Every 5 minutes?
4. **Historical Access:** Can you backfill data?
5. **Point Metadata:** Does he provide point descriptions or just values?
6. **BMS Platforms:** Which vendors? (Niagara, Trend, Schneider?)

---

## 10. NEXT STEPS (CONCRETE ACTIONS)

### This Week:

1. ✅ Set up local InfluxDB (Docker)
2. ✅ Create mock BMS data generator
3. ✅ Build first Plotly visualization
4. ✅ Create birdlab-tech/building-analytics repo

### This Month:

1. Meet with BMS friend - get sample API access
2. Test data ingestion from real BMS
3. Start point identification research (Niagara .bog parsing)
4. Document architectural decisions

### This Quarter:

1. Deploy prototype to single building
2. Validate against re:sustain's data
3. Begin PhD formal research

---

## CONCLUSION

**re:sustain has solved the hard commercial problems:**
- Reliable data collection
- Enterprise security
- Customer management
- Professional UI

**You don't need to replicate all of that.** You need:
- A research environment where you can innovate on **point identification** and **digital twin calibration**
- Clean IP separation from re:sustain
- Tools that let Claude Code assist you (Python > AWS)
- Publishable, reproducible research

**Your Plotly + Python approach is superior for research because:**
1. You can generate new analyses conversationally with Claude Code
2. Everything is version-controlled and reproducible
3. No vendor lock-in
4. Publication-ready visualizations
5. Jupyter notebooks = research documentation

**Start simple, iterate fast, and let the research drive the architecture - not the other way around.**
