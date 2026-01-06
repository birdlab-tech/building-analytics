# Independent Building Analytics Platform

**Your PhD Research Platform - No AWS, No re:sustain Dependencies, Full Control**

## Overview

This is your independent platform for building analytics research. It's designed to:

1. **Protect Your IP** - Completely separate from re:sustain's AWS infrastructure
2. **Enable Research** - Python-based, flexible, Claude Code-assisted
3. **Save Money** - 80-95% cheaper than AWS alternatives
4. **Maximize Flexibility** - Plotly > Grafana for research and analysis

## Quick Start (No Installation Required!)

### Try It Now: Instant Visualization

```bash
# Just run this - no database needed!
python quick_viz_example.py
```

This will generate 4 interactive HTML dashboards from your BMS data:
- `01_system_overview.html` - System distribution
- `02_boiler_dashboard.html` - Boiler performance
- `03_temperature_distribution.html` - Temperature analysis
- `04_ahu_analysis.html` - AHU efficiency

**Open them in your browser** - zoom, pan, hover, export!

## What You Have Here

### Sample Data

- `2024-07-22T16_25_52.json` - Real BMS data snapshot (375 points)
  - Boiler system (flow temps, pumps, valves)
  - AHUs (heating/cooling valves, air flow)
  - Temperature sensors across building
  - Control signals and statuses

### Code Examples

#### `quick_viz_example.py` - Start Here! ⭐

No database required. Directly analyzes JSON and creates Plotly visualizations.

**What it demonstrates:**
- Loading BMS data from JSON
- Automatic point categorization (preview of your PhD work!)
- Multi-panel dashboards with Plotly
- Inefficiency detection (simultaneous heating/cooling)
- Faulty sensor identification

**Run it:**
```bash
python quick_viz_example.py
```

#### `generate_fake_timeseries.py` + `visualize_timeseries.py` - Grafana-Style Demo ⭐

Perfect for demonstrating to Dan! Creates realistic time-series data and Grafana-style line graphs.

**What it demonstrates:**
- Fake data generation (3 temperature sensors, 15min intervals, 1 week)
- Realistic daily patterns (occupied/unoccupied periods)
- Grafana-style dark theme with smooth line graphs
- Multiple visualization types (overlay, stacked panels, pattern analysis)
- Interactive features (zoom, pan, export)

**Run it:**
```bash
python generate_fake_timeseries.py  # Creates fake_timeseries_data.json
python visualize_timeseries.py       # Creates 4 interactive HTML dashboards
```

**Generated dashboards:**
- `timeseries_01_all_zones.html` - All 3 zones overlaid
- `timeseries_02_separate_panels.html` - Stacked panels per zone
- `timeseries_03_weekly_patterns.html` - Hourly patterns by day
- `timeseries_04_monday_detail.html` - Single day with occupied hours highlighted

#### `example_ingestion.py` - Full Platform

Complete example with InfluxDB time-series database.

**What it demonstrates:**
- Parsing BMS point labels (`L11_O11_S1_Boiler...`)
- Categorical identification (boiler, AHU, valve, etc.)
- Writing to InfluxDB with rich metadata
- Querying by system type
- Real-time dashboards

**Requires:** InfluxDB running (see below)

#### `docker-compose.yml` - Infrastructure

One command to start your entire stack:

```bash
docker-compose up -d
```

This gives you:
- InfluxDB 2.7 (time-series database) on `localhost:8086`
- Grafana (optional, but Plotly is better!) on `localhost:3000`

## Full Setup (When You're Ready)

### 1. Install Prerequisites

```bash
# Python packages
pip install influxdb-client pandas plotly

# Docker (for InfluxDB)
# Download from: https://www.docker.com/products/docker-desktop
```

### 2. Start Database

```bash
docker-compose up -d
```

### 3. Configure InfluxDB

1. Open http://localhost:8086
2. Login: `admin` / `password123`
3. Go to **Data → API Tokens**
4. Copy your token
5. Update `example_ingestion.py`:

```python
INFLUX_CONFIG = {
    'token': 'paste-your-token-here',
    # ...
}
```

### 4. Ingest Data

```bash
python example_ingestion.py
```

### 5. Analyze & Visualize

The script automatically:
- Loads BMS JSON
- Categorizes points by system
- Writes to InfluxDB with metadata
- Detects inefficiencies
- Creates interactive dashboard (`boiler_dashboard.html`)

## Key Advantages Over re:sustain's Approach

| Aspect | re:sustain (AWS) | Your Platform (Independent) |
|--------|------------------|----------------------------|
| **Database** | DynamoDB + S3 | InfluxDB (purpose-built for time-series) |
| **API** | AWS AppSync (GraphQL) | FastAPI (Python-native) |
| **Visualization** | Grafana (rigid UI) | Plotly (programmatic, flexible) |
| **Cost/month** | £100-270 per building | £10-60 for ALL buildings |
| **Vendor Lock-in** | AWS only | Runs anywhere |
| **Claude Code Integration** | Limited | Full support |
| **Research Flexibility** | Commercial constraints | Full freedom |
| **IP Ownership** | Unclear | 100% yours |

## Your PhD Contribution: Automated Point Identification

### What re:sustain Does Manually

```python
# Manual mapping by BMS engineer
"L11_O11_S1_Boiler Common Flow Temp" → "boiler_01.flow.temperature.sensor"
```

### What Your Research Will Automate

From your proposal (Section A, page 9-10):

**Five Methods of Ontological Interrogation:**

1. **Categorical** - Point type (AI, AO, BI, BO, AV, BV)
2. **Logical** - Control chain analysis (trifurcation method)
3. **Numerical** - Value range validation (15-30°C = air, 50-90°C = LTHW)
4. **Nominal** - Label parsing (fallback only)
5. **Consequential** - Cause-effect testing

**Example Implementation:**

```python
from building_informatics import BMSInterrogator

# Parse Niagara .bog file
interrogator = BMSInterrogator()
niagara_bog = interrogator.parse_file("backup.bog")

# Categorical + Logical identification
ahus = interrogator.identify_ahus(niagara_bog)

for ahu in ahus:
    # Find supply air temperature via trifurcation
    supply_temp = interrogator.find_trifurcation(
        ahu,
        point_type="AI",
        setpoint_range=(15, 30),
        connected_to="heating_coil_valve"
    )

    # Numerical verification
    if supply_temp.min_value < 10 or supply_temp.max_value > 35:
        print(f"Warning: {supply_temp.label} has suspicious range")

# Auto-generate standardized names
standardized = {
    "ahu_01.supply_air.temperature.sensor": supply_temp,
    "ahu_01.supply_air.temperature.setpoint": setpoint,
    # ...
}
```

**This is YOUR novel contribution** - re:sustain doesn't have this automation.

## Data Format Documentation

### JSON Structure

```json
{
  "ObjectId": "d82eaf6003faf8893ce30c3392e19165",
  "InstallationId": "7c448d21-d839-457f-b773-4f522a2cdbf2",
  "At": "2024-07-22T16:25:52.000",
  "Value": "78.34",
  "Label": "L11_O11_S1_Boiler Common Flow Temp"
}
```

### Label Convention

Format: `L{Line}_O{Outstation}_D/S/I/K/W{Number}_{Description}`

**Examples:**
- `L11_O11_S1_Boiler Common Flow Temp` = Line 11, Outstation 11, Sensor 1
- `L11_O11_D1_Boiler Primary Pump 1` = Line 11, Outstation 11, Digital Output 1
- `L11_O12_D2_East AHU2 Htg Valve` = Line 11, Outstation 12, Digital Output 2

**Point Type Codes:**
- `S` = Sensor (analog input)
- `D` = Digital output
- `I` = Input (binary)
- `K` = Control signal
- `W` = Value/word

### Systems in Sample Data

From `2024-07-22T16_25_52.json`:

- **Boiler System** (67 points)
  - Flow temperatures (78-79°C)
  - Return temperatures (73°C)
  - Primary pumps (2x, currently Pump 1 ON)
  - Control valves (0-10V signals)

- **AHU Systems** (75 points)
  - AHU1, AHU2, AHU3
  - Heating valves (currently 0%)
  - Cooling valves (active: 19-40%)
  - Air flow monitoring

- **Perimeter Heating** (48+ points)
  - Zone valves (Base East/West, Ground E/W, 1E/1W, 2E/2W, etc.)
  - Currently all closed (0%)

- **Space Temperatures** (multiple zones)
  - Basement: 22-24°C
  - Ground floor: ~24°C

## Working with Claude Code

### Ask for Custom Analysis

**You:** "Show correlation between outside air temp and chiller power"

**Claude Code generates:**

```python
import plotly.express as px

# Query data
df = analyzer.query_system_data(installation_id, 'ahu')

# Find relevant columns
oat_col = [c for c in df.columns if 'Outside' in c and 'Temp' in c][0]
chiller_col = [c for c in df.columns if 'Chiller' in c and 'Power' in c][0]

# Create scatter plot with trendline
fig = px.scatter(
    df,
    x=oat_col,
    y=chiller_col,
    trendline='ols',
    title='Outside Air Temp vs Chiller Power'
)

# Show correlation
from scipy.stats import pearsonr
corr, p_value = pearsonr(df[oat_col], df[chiller_col])
print(f"Correlation: {corr:.3f} (p={p_value:.4f})")

fig.show()
```

**You can't do this with Grafana.** That's why Plotly is better for research.

## Next Steps

### Phase 1: Local Development (This Week)

- [x] Review re:sustain architecture
- [ ] Run `quick_viz_example.py` to see Plotly in action
- [ ] Start `docker-compose` and explore InfluxDB
- [ ] Run `example_ingestion.py` with sample data
- [ ] Ask Claude Code to generate a custom analysis

### Phase 2: BMS Integration (This Month)

- [ ] Meet with your BMS friend to understand his API
- [ ] Get sample live data stream
- [ ] Test ingestion from real BMS
- [ ] Deploy to Raspberry Pi for on-site collection

### Phase 3: Research Implementation (This Quarter)

- [ ] Parse Niagara .bog files (start with `bms_interrogator.py`)
- [ ] Implement categorical identification
- [ ] Implement trifurcation (logical analysis)
- [ ] Validate against re:sustain's manual mappings

### Phase 4: PhD Deliverables (Jun 2026 - 2029)

- [ ] Automated point identification system
- [ ] Digital twin calibration automation
- [ ] CO₂-based occupancy tracking
- [ ] Thermovolumetric optimization framework
- [ ] Publications in building physics journals

## Questions for Your BMS Friend

When you meet, ask:

1. **API Format:** REST? GraphQL? WebSocket for real-time?
2. **Authentication:** API keys? OAuth? VPN required?
3. **Data Format:** Same JSON structure as this sample?
4. **Update Frequency:** Real-time stream or polling (every 1min, 5min)?
5. **Historical Access:** Can you backfill data for calibration?
6. **BMS Platforms:** Which vendors does he work with? (Niagara, Trend, Schneider?)
7. **Point Metadata:** Does his API include point descriptions/units?

## Resources

### Documentation
- [InfluxDB 2.x Docs](https://docs.influxdata.com/influxdb/v2.7/)
- [Plotly Python](https://plotly.com/python/)
- [FastAPI](https://fastapi.tiangolo.com/)

### Your Research References
- `Research Proposal (Alex Amies).pdf` - Your PhD proposal
- `RE-SUSTAIN_ARCHITECTURE_REVIEW.md` - Detailed analysis of re:sustain's approach

### Related Files
- Email threads documenting your independence from re:sustain
- Board meeting notes confirming IP separation

## Cost Estimate

### Development Phase (Now - Jun 2026)
- **Infrastructure:** £0 (local Docker)
- **Tools:** £0 (all open-source)
- **Total:** £0/month

### Production Phase (Jun 2026+)
- **VPS** (Hetzner 8GB): £8/month
- **Domain + SSL:** £2/month
- **Backups:** Included
- **Total:** £10/month (for unlimited buildings!)

**vs re:sustain's £100-270/month/building on AWS**

## Support

This is YOUR independent platform for YOUR research. Claude Code (me!) can help you:

- Generate analysis scripts
- Debug ingestion issues
- Design custom visualizations
- Implement PhD research algorithms
- Prepare publication figures

Just ask! 🚀

---

**Built for research. Designed for independence. Optimized for discovery.**
