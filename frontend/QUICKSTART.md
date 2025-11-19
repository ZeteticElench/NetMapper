# Network Infrastructure Dashboard - Quick Start Guide

## 🚀 Quick Start (5 minutes)

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Start Development Server

```bash
npm start
```

The app will automatically open at [http://localhost:3000](http://localhost:3000)

### 3. Explore the Dashboard

#### Hierarchy View (Default)
- **Zoom in**: Click on any circle (Data Center, Rack, or Device)
- **View details**: Click on the smallest circles (Interfaces)
- **Zoom out**: Click on the background
- **Tooltip**: Hover over any circle

#### Topology View
- **Switch view**: Click "🌐 Topology View" in the header
- **Context menu**: Right-click any interface node
  - ⚙️ Config - View configuration
  - 🔍 Trace - Trace network route
  - 💻 SSH - SSH connection
- **Details**: Double-click any interface
- **Navigate**: Use Fit and Reset buttons

#### Generate New Data
- Click **Regenerate** button to create a new random network topology

---

## 📋 What You Get Out of the Box

### ✅ Fully Functional Features

1. **Two Visualization Modes**
   - D3.js Zoomable Circle Packing (Hierarchy View)
   - Cytoscape.js Compound Nodes (Topology View)

2. **Interactive Elements**
   - Click-to-zoom on hierarchy
   - Right-click context menu on topology
   - Hover tooltips
   - Connection highlighting

3. **Status Modal**
   - Device/Interface details
   - Configuration viewer
   - SSH and Trace actions

4. **Real-time Statistics**
   - Device counts
   - Interface status breakdown
   - Color-coded status indicators

5. **Sample Data Generator**
   - Realistic network hierarchies
   - Random but coherent topology
   - Status indicators (up/down/warning)

### 📦 Tech Stack

- React 18.2
- D3.js 7.8
- Cytoscape.js 3.28
  - cytoscape-fcose (layout)
  - cytoscape-cxtmenu (context menu)
- Tailwind CSS 3.3

---

## 🎨 Visual Reference

### Hierarchy View Appearance
```
┌─────────────────────────────────────────┐
│  [Large blue circle = Data Center]     │
│    └─ [Medium circles = Racks]         │
│       └─ [Smaller circles = Devices]   │
│          └─ [Tiny circles = Interfaces]│
│             Colors:                     │
│             🟢 Green = Up               │
│             🟡 Yellow = Warning         │
│             🔴 Red = Down               │
└─────────────────────────────────────────┘
```

### Topology View Appearance
```
┌────────────────────────────────────────────┐
│  ┌─ Data Center (blue box) ──────────┐   │
│  │  ┌─ Rack (lighter blue box) ────┐ │   │
│  │  │  ┌─ Device (lightest box) ─┐ │ │   │
│  │  │  │  • Interface nodes       │ │ │   │
│  │  │  │    (colored dots)        │ │ │   │
│  │  │  └──────────────────────────┘ │ │   │
│  │  └─────────────────────────────── │   │
│  └────────────────────────────────────┘   │
│  Lines = Network connections               │
└────────────────────────────────────────────┘
```

---

## 🔧 Customization

### Change Network Size

Edit `src/App.js` line 21:
```javascript
const data = generateNetworkData(3); // 3 data centers instead of 2
```

### Modify Data Generator

Edit `src/utils/DataGenerator.js`:
```javascript
// Line 155: Adjust devices per rack
const deviceCount = 2 + Math.floor(Math.random() * 3); // 2-4 devices

// Line 140: Adjust interfaces per device
const interfaceCount = 4 + Math.floor(Math.random() * 5); // 4-8 interfaces

// Line 170: Adjust racks per data center
const rackCount = 2 + Math.floor(Math.random() * 2); // 2-3 racks
```

### Adjust Colors

Edit `tailwind.config.js`:
```javascript
colors: {
  'network-up': '#10b981',    // Change green
  'network-down': '#ef4444',  // Change red
  'network-warning': '#f59e0b', // Change yellow
}
```

### Tune Topology Layout

Edit `src/components/TopologyGraph.js` line 109+:
```javascript
layout: {
  name: 'fcose',
  nodeRepulsion: 8000,     // ⬆️ Increase for more spacing
  idealEdgeLength: 100,    // ⬆️ Increase for longer edges
  gravity: 0.25,           // ⬇️ Decrease for more spread
}
```

---

## 🔗 Integration with NetMapper Backend

This frontend is designed to work with the NetMapper Python backend (parent directory).

### Step 1: Add API Endpoint to NetMapper

Create `netmapper/api.py`:
```python
from flask import Flask, jsonify
from .neo4j_manager import Neo4jManager

app = Flask(__name__)

@app.route('/api/network-topology')
def get_topology():
    # Query Neo4j and format for frontend
    neo4j = Neo4jManager(...)

    hierarchy = neo4j.get_hierarchy_data()
    topology = neo4j.get_topology_data()

    return jsonify({
        'hierarchy': hierarchy,
        'topology': topology
    })

if __name__ == '__main__':
    app.run(port=5000)
```

### Step 2: Update Frontend to Use API

Edit `src/App.js`:
```javascript
useEffect(() => {
  // Replace generateNetworkData() with API call
  fetch('http://localhost:5000/api/network-topology')
    .then(res => res.json())
    .then(data => {
      setNetworkData(data);
      calculateStats(data);
    })
    .catch(error => {
      console.error('Error fetching network data:', error);
      // Fallback to generated data
      const data = generateNetworkData(2);
      setNetworkData(data);
    });
}, []);
```

### Step 3: Enable CORS (if needed)

```bash
pip install flask-cors
```

```python
from flask_cors import CORS
app = Flask(__name__)
CORS(app)
```

### Expected API Response Format

```json
{
  "hierarchy": {
    "name": "Network Infrastructure",
    "type": "root",
    "children": [
      {
        "id": "dc-0",
        "name": "DC-1",
        "type": "datacenter",
        "status": "up",
        "children": [
          {
            "id": "dc-0-rack-0",
            "name": "Rack-A",
            "type": "rack",
            "status": "up",
            "children": [
              {
                "id": "dc-0-rack-0-dev-0",
                "name": "switch-1-0-0",
                "type": "device",
                "deviceType": "switch",
                "status": "up",
                "ip": "10.0.1.1",
                "model": "Catalyst 3850",
                "children": [
                  {
                    "id": "dc-0-rack-0-dev-0-int-0",
                    "name": "GigabitEthernet0/0/1",
                    "type": "interface",
                    "status": "up",
                    "speed": "1G",
                    "ip": "10.0.1.2",
                    "vlan": 10,
                    "config": "interface GigabitEthernet0/0/1\n description Port 1\n..."
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  },
  "topology": {
    "nodes": [
      {
        "data": {
          "id": "dc-0",
          "label": "DC-1",
          "type": "datacenter",
          "status": "up"
        }
      },
      {
        "data": {
          "id": "dc-0-rack-0",
          "label": "Rack-A",
          "type": "rack",
          "status": "up",
          "parent": "dc-0"
        }
      }
    ],
    "edges": [
      {
        "data": {
          "id": "conn-0",
          "source": "interface-1",
          "target": "interface-2",
          "type": "fiber",
          "status": "up"
        }
      }
    ]
  }
}
```

---

## 📚 Component Reference

### HierarchyChart.js
**Props:**
- `data` (object): Hierarchy data structure
- `onNodeClick` (function): Callback when leaf node clicked

**Features:**
- Zoomable circle packing
- Color-coded by status
- Smooth zoom transitions
- Tooltips on hover

### TopologyGraph.js
**Props:**
- `data` (object): Topology data with nodes and edges
- `onNodeClick` (function): Callback when node clicked

**Features:**
- Compound nodes (nested boxes)
- fcose layout algorithm
- Circular context menu
- Connection highlighting
- Zoom/pan controls

### StatusModal.js
**Props:**
- `isOpen` (boolean): Modal visibility
- `onClose` (function): Close callback
- `data` (object): Node data to display

**Features:**
- Device/Interface details
- Configuration code block
- SSH and Trace actions
- Responsive design

---

## 🐛 Troubleshooting

### Cytoscape Graph Not Rendering
**Problem**: Blank white space instead of graph
**Solution**:
```javascript
// Ensure container has height
<div style={{ height: '600px' }}>
  <TopologyGraph ... />
</div>
```

### Context Menu Not Appearing
**Problem**: Right-click doesn't show menu
**Solution**:
- Ensure you're right-clicking on interface nodes (small circles)
- On Mac: Control+Click
- Check console for cxtmenu errors

### D3 Circles Overlapping
**Problem**: Circles not properly spaced
**Solution**: Adjust pack padding in `HierarchyChart.js`:
```javascript
const pack = d3.pack()
  .size([width, height])
  .padding(5); // Increase from 3 to 5
```

### Performance Issues
**Problem**: Slow rendering with large networks
**Solution**:
- Reduce data center count
- Implement pagination
- Filter by data center
```javascript
// In DataGenerator.js
const data = generateNetworkData(1); // Just 1 DC for testing
```

---

## 🎯 Next Steps

1. **Connect to Real Data**: Integrate with NetMapper backend API
2. **Add Filtering**: Filter by data center, rack, or device type
3. **Real-time Updates**: WebSocket connection for live status
4. **Search**: Add search bar to find devices/interfaces
5. **Export**: Export visualizations as PNG/SVG
6. **Themes**: Add dark mode support

---

## 📖 Additional Resources

- [D3.js Documentation](https://d3js.org/)
- [Cytoscape.js Documentation](https://js.cytoscape.org/)
- [React Documentation](https://react.dev/)
- [Tailwind CSS Documentation](https://tailwindcss.com/)

## 💡 Tips

1. **Use Chrome DevTools**: Inspect elements to understand the structure
2. **Console Logging**: Add console.logs to see data flow
3. **Component Hierarchy**: Use React DevTools to debug state
4. **Performance**: Use React Profiler for optimization

---

Enjoy your Network Infrastructure Dashboard! 🎉
