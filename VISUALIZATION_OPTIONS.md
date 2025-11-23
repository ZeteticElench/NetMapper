# Network Visualization Options

NetMapper provides **two powerful visualization frontends** for exploring your network topology:

## 📊 Option 1: React Dashboard (Recommended for Most Users)

**Location**: `frontend/`

### Best For
- **Network engineers** who need familiar hierarchical views
- **Quick exploration** of network topology
- **Status monitoring** of devices and interfaces
- **Standard network operations** (SSH, trace route, config viewing)

### Technology
- React 18 + TypeScript
- D3.js for hierarchy visualization
- Cytoscape.js for topology graphs
- Tailwind CSS

### Features
✅ **Two visualization modes**:
   - Circle Packing (zoomable hierarchy)
   - Network Topology (compound nodes with connections)

✅ **Interactive elements**:
   - Click to zoom in/out through hierarchy
   - Right-click context menus
   - Status modal with device details
   - SSH and trace actions

✅ **Real-time statistics**:
   - Device counts
   - Interface status breakdown
   - Color-coded health indicators

### Quick Start
```bash
cd frontend
npm install
npm start
# Open http://localhost:3000
```

### When to Use
- You want a familiar, dashboard-style interface
- You need standard network operations (SSH, config, trace)
- You're comfortable with React-based web apps
- You want easy integration with REST APIs

---

## 🎨 Option 2: GraphUI (Advanced Dense Visualization)

**Location**: `frontend-graphui/`

### Best For
- **Deep network analysis** requiring maximum information density
- **Data center operators** managing physical infrastructure
- **Advanced users** who need hierarchical drill-down
- **Pattern recognition** in complex topologies

### Technology
- TypeScript + Vite
- Canvas-based rendering (high performance)
- D3 force layouts
- Direct Neo4j bolt connection

### Features
✅ **Extremely information-dense rendering**:
   - Multi-layered visual encoding
   - Inline property display
   - Degree rings, badges, and indicators
   - Type-based color coding

✅ **"Google Earth for Data Centers"**:
   - 4-level drill-down: DC → Rack → Server → Process
   - Heat-mapped status visualization
   - Operational metrics rings (PUE, power, bandwidth)
   - Spatial troubleshooting

✅ **Direct Neo4j integration**:
   - Bolt protocol connection
   - Real-time Cypher queries
   - Auto-clustering by node labels

✅ **Multiple layout algorithms**:
   - Force-directed
   - Cluster-based
   - Hierarchical

### Quick Start
```bash
cd frontend-graphui
npm install
npm run dev
# Open http://localhost:5173
```

Press **5** to enter Data Center hierarchy mode, then double-click nodes to drill down.

### When to Use
- You need maximum information density
- You're managing physical data center infrastructure
- You want direct Neo4j query capabilities
- You need hierarchical drill-down (DC → Rack → Server → Process)
- You want to identify spatial patterns and dependencies

---

## 🔄 Comparison

| Feature | React Dashboard | GraphUI |
|---------|----------------|---------|
| **Framework** | React + D3 + Cytoscape | TypeScript + Canvas |
| **Rendering** | DOM + SVG | Canvas (faster) |
| **Information Density** | Medium | Ultra-high |
| **Neo4j Integration** | Via REST API | Direct bolt connection |
| **Hierarchy Levels** | 4 (DC/Rack/Device/Interface) | 4 (DC/Rack/Server/Process) |
| **Drill-down** | Click to zoom | Double-click drill-down |
| **Context Menus** | Right-click (Cytoscape) | Keyboard shortcuts |
| **Status Modal** | ✅ Yes | ❌ Tooltips only |
| **SSH Integration** | ✅ Yes | ❌ No |
| **Real-time Stats** | ✅ Dashboard | ❌ No dashboard |
| **Layout Algorithms** | 2 (fcose, pack) | 3 (force, cluster, hierarchical) |
| **Performance** | Good (100s of nodes) | Excellent (1000s of nodes) |
| **Learning Curve** | Easy | Moderate |
| **Mobile Support** | ✅ Responsive | ⚠️ Desktop-optimized |
| **Customization** | React components | TypeScript classes |

---

## 🎯 Recommendation

### Use **React Dashboard** if you:
- Are new to network visualization
- Need standard operations (SSH, config, trace)
- Want a polished, dashboard-style UI
- Prefer familiar web interfaces
- Need mobile/tablet support

### Use **GraphUI** if you:
- Manage physical data center infrastructure
- Need to analyze complex dependency chains
- Want maximum information in minimal space
- Prefer direct database queries
- Need advanced pattern recognition
- Are comfortable with keyboard-driven interfaces

---

## 🔗 Running Both

You can run both frontends simultaneously:

```bash
# Terminal 1: React Dashboard
cd frontend
npm start
# Open http://localhost:3000

# Terminal 2: GraphUI
cd frontend-graphui
npm run dev
# Open http://localhost:5173
```

Both can connect to the same Neo4j database and visualize the same network data.

---

## 📡 Integration with NetMapper

### React Dashboard Integration
The React dashboard expects a REST API endpoint:

```python
# Add to netmapper/api.py
from flask import Flask, jsonify

@app.route('/api/network-topology')
def get_topology():
    return jsonify({
        'hierarchy': {...},
        'topology': {'nodes': [...], 'edges': [...]}
    })
```

See `frontend/README.md` for complete API specification.

### GraphUI Integration
GraphUI connects directly to Neo4j bolt protocol:

1. Start NetMapper discovery to populate Neo4j
2. Run GraphUI: `cd frontend-graphui && npm run dev`
3. In the Neo4j panel (top-right):
   - Enter bolt URI: `bolt://localhost:7687`
   - Enter credentials
   - Click "Connect"
   - Click "Load Graph" or execute custom Cypher queries

GraphUI will automatically cluster nodes by label and apply layouts.

---

## 🎨 Screenshots

### React Dashboard - Hierarchy View
Zoomable circle packing with color-coded status:
- Data Centers (large blue circles)
- Racks (medium circles)
- Devices (smaller circles)
- Interfaces (tiny colored dots: green=up, red=down, yellow=warning)

### React Dashboard - Topology View
Compound nodes with network connections:
- Nested boxes for DC/Rack/Device
- Interface nodes with connection lines
- Right-click context menus
- Zoom/pan controls

### GraphUI - Data Center Mode
Ultra-dense visualization with metrics rings:
- Level 1: Data centers with PUE/power/bandwidth rings
- Level 2: Racks with power phase and capacity indicators
- Level 3: Servers heat-mapped by resource usage
- Level 4: Processes with dependency chains

---

## 🚀 Next Steps

1. **Choose your visualization** based on your use case
2. **Install dependencies** for your chosen frontend(s)
3. **Run NetMapper discovery** to populate Neo4j
4. **Start the frontend** and connect to your data
5. **Explore your network topology**!

For detailed documentation:
- React Dashboard: See `frontend/README.md` and `frontend/QUICKSTART.md`
- GraphUI: See `frontend-graphui/README.md`
