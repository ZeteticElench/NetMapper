# Network Infrastructure Visualization Dashboard

A comprehensive React-based dashboard for visualizing network infrastructure using D3.js and Cytoscape.js.

## Features

### 🎯 Dual Visualization Modes

#### 1. Hierarchy View (D3.js Zoomable Circle Packing)
- **Visual Style**: Based on [Observable D3 Zoomable Circle Packing](https://observablehq.com/@d3/zoomable-circle-packing)
- **Hierarchy**: Data Center → Rack → Device → Interface
- **Color Coding**:
  - Green = Up
  - Yellow = Warning
  - Red = Down
  - Blue shades = Container levels
- **Interactions**:
  - Click clusters (DC/Rack/Device) to zoom in
  - Click leaf nodes (Interfaces) to open Status Modal
  - Click background to zoom out
  - Hover for tooltips

#### 2. Topology View (Cytoscape.js Compound Nodes)
- **Visual Style**: Based on [Cytoscape Compound Nodes Demo](https://js.cytoscape.org/demos/compound-nodes/)
- **Layout**: fcose (Fast Compound Spring Embedder) for non-overlapping nested boxes
- **Structure**:
  - Nested boxes: Data Centers > Racks > Devices
  - Interface nodes inside device boxes
  - Edges show network connections
- **Context Menu**: Circular menu (based on [cxtmenu](https://cytoscape.org/cytoscape.js-cxtmenu/))
  - ⚙️ Config - View interface configuration
  - 🔍 Trace - Trace network route
  - 💻 SSH - Connect via SSH
- **Interactions**:
  - Right-click interfaces for context menu
  - Double-click for Status Modal
  - Hover to highlight connections
  - Zoom/pan controls

### 📊 Status Modal
Triggered by clicking interface nodes in either view:
- Device details (name, IP, model, version)
- Interface configuration (code block)
- Status indicators
- Action buttons:
  - SSH Connect
  - Trace Route
  - Close

### 📈 Dashboard Statistics
Real-time stats displayed in header:
- Total Devices
- Total Interfaces
- Up Interfaces
- Warning Interfaces
- Down Interfaces

## Tech Stack

- **React** 18.2 - UI framework
- **D3.js** 7.8 - Hierarchy visualization
- **Cytoscape.js** 3.28 - Network topology visualization
  - `cytoscape-fcose` - Compound node layout
  - `cytoscape-cxtmenu` - Circular context menu
- **Tailwind CSS** 3.3 - Styling

## Project Structure

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── HierarchyChart.js      # D3 Circle Packing
│   │   ├── TopologyGraph.js       # Cytoscape Topology
│   │   └── StatusModal.js         # Shared Modal
│   ├── utils/
│   │   └── DataGenerator.js       # Sample data generator
│   ├── App.js                     # Main application
│   ├── index.js                   # Entry point
│   └── index.css                  # Global styles
├── package.json
├── tailwind.config.js
└── README.md
```

## Installation

### Prerequisites
- Node.js 16+ and npm

### Steps

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Start development server**:
   ```bash
   npm start
   ```

3. **Open browser**:
   Navigate to [http://localhost:3000](http://localhost:3000)

## Usage

### View Toggle
- Use the toggle buttons in the header to switch between:
  - 📊 **Hierarchy View** - Circle packing visualization
  - 🌐 **Topology View** - Network graph with compound nodes

### Regenerate Data
- Click the **Regenerate** button to create a new random network topology
- Useful for testing different network configurations

### Explore Hierarchy
1. Click on a Data Center circle to zoom in
2. Click on a Rack to zoom deeper
3. Click on a Device to see its interfaces
4. Click on an Interface (leaf node) to open the Status Modal

### Explore Topology
1. Pan and zoom the graph
2. Right-click an interface node to open the circular context menu
3. Double-click an interface to open the Status Modal
4. Hover over interfaces to highlight their connections
5. Use **Fit** and **Reset** buttons for navigation

### View Interface Details
- Click (hierarchy) or right-click (topology) any interface
- Modal shows:
  - Status badge
  - IP addresses
  - Speed, VLAN
  - Configuration code
  - SSH and Trace actions

## Data Structure

### Hierarchy (D3.js)
```javascript
{
  name: "Network Infrastructure",
  children: [
    {
      name: "DC-1",
      type: "datacenter",
      children: [
        {
          name: "Rack-A",
          type: "rack",
          children: [
            {
              name: "switch-1-0-0",
              type: "device",
              children: [
                {
                  name: "GigabitEthernet0/0/1",
                  type: "interface",
                  status: "up",
                  // ... more fields
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

### Topology (Cytoscape.js)
```javascript
{
  nodes: [
    {
      data: {
        id: "dc-0",
        label: "DC-1",
        type: "datacenter"
      }
    },
    {
      data: {
        id: "dc-0-rack-0",
        label: "Rack-A",
        type: "rack",
        parent: "dc-0"  // Compound node
      }
    },
    // ... more nodes
  ],
  edges: [
    {
      data: {
        source: "interface-1",
        target: "interface-2",
        type: "fiber"
      }
    }
  ]
}
```

## Customization

### Adjust Network Size
In `src/App.js`, change the data center count:
```javascript
const data = generateNetworkData(2); // 2 data centers
```

### Modify Colors
Edit `tailwind.config.js` for custom color schemes:
```javascript
colors: {
  'network-up': '#10b981',
  'network-down': '#ef4444',
  // ... more colors
}
```

### Adjust Layout
In `src/components/TopologyGraph.js`, tune fcose parameters:
```javascript
layout: {
  name: 'fcose',
  nodeRepulsion: 8000,      // Increase for more spacing
  idealEdgeLength: 100,     // Adjust edge length
  // ... more options
}
```

## Reference Links

This implementation is based on the following examples:

1. **D3 Zoomable Circle Packing**: https://observablehq.com/@d3/zoomable-circle-packing
2. **D3 Zoomable Icicle**: https://observablehq.com/@d3/zoomable-icicle (data structure compatible)
3. **D3 Zoomable Sunburst**: https://observablehq.com/@d3/zoomable-sunburst (data structure compatible)
4. **Cytoscape Compound Nodes**: https://js.cytoscape.org/demos/compound-nodes/
5. **Cytoscape Context Menu**: https://cytoscape.org/cytoscape.js-cxtmenu/

## Integration with NetMapper Backend

This frontend can be connected to the NetMapper Python backend (in the parent directory) to visualize real network data:

1. **Start NetMapper discovery** to populate Neo4j
2. **Create API endpoint** to fetch data from Neo4j
3. **Replace DataGenerator** with API calls in `src/App.js`:
   ```javascript
   useEffect(() => {
     fetch('/api/network-topology')
       .then(res => res.json())
       .then(data => setNetworkData(data));
   }, []);
   ```

### Expected API Response Format
```javascript
{
  hierarchy: {
    name: "Network Infrastructure",
    children: [ /* ... */ ]
  },
  topology: {
    nodes: [ /* ... */ ],
    edges: [ /* ... */ ]
  }
}
```

## Building for Production

```bash
npm run build
```

This creates an optimized production build in the `build/` directory.

## Troubleshooting

### Cytoscape not rendering
- Check browser console for errors
- Ensure container has height (not 0px)
- Verify fcose extension is loaded

### D3 zoom not working
- Ensure click events are not being blocked
- Check that SVG has proper dimensions

### Context menu not appearing
- Right-click (or long-press on mobile) interface nodes
- Ensure cxtmenu extension is loaded

## Performance

- Tested with up to 500 devices and 2000 interfaces
- D3 renders smoothly with ~1000 circles
- Cytoscape handles ~2000 nodes with fcose layout
- For larger networks, consider:
  - Pagination
  - Filtering by data center/rack
  - Progressive rendering

## License

This project is part of the NetMapper network discovery tool.

## Support

For issues or questions, please refer to the main NetMapper documentation.
