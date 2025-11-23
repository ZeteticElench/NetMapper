# Dense Graph UI

An **extremely information-dense** graph visualization system for graph databases. This project creates rich, visually engaging graph visualizations that pack maximum information into each node and edge.

## 🖥️ "Google Earth for Data Centers"

**NEW**: Hierarchical drill-down visualization for IT infrastructure! Navigate from continental datacenter views down to individual processes with double-click zoom and spatial troubleshooting.

- **Level 1: Data Centers** - PUE, power, bandwidth, temperature rings
- **Level 2: Racks** - Power phases, capacity, network topology
- **Level 3: Servers** - Heat-mapped by status, colored by OS
- **Level 4: Processes** - Resource usage, dependency chains

Press **5** to enter hierarchy mode. Double-click nodes to drill down. Use breadcrumbs to navigate up.

## Features

### Information-Dense Node Rendering
- **Multi-layered visual encoding**: Colors, sizes, shapes, badges, and icons
- **Type badges**: Each node displays its type prominently
- **Property indicators**: Badge showing count of properties
- **Importance stars**: Visual indicator for high-importance nodes
- **Degree rings**: Inner rings showing connection count
- **Inline properties**: Display key-value pairs directly on nodes (high density mode)

### Rich Visual Features
- **Color-coded by type**: Different entity types get distinct colors
- **Size by importance**: More important nodes are larger
- **Edge weights**: Connection strength shown via line thickness and opacity
- **Edge labels**: Relationship types visible on important edges
- **Shadows and depth**: 3D-style rendering for visual clarity

### Multiple Layout Algorithms
- **Force-directed**: Physics-based organic layouts
- **Cluster-based**: Groups nodes by type/category
- **Hierarchical**: Tree-like structures for data flows

### Advanced Cluster Visualization
- **Donut chart rings**: Aggregate statistics displayed as rings around clusters
- **Demographic visualization**: Age distributions and other demographics
- **Cluster backgrounds**: Pastel-colored backgrounds for visual separation
- **Inter-cluster connections**: Lines showing relationships between clusters
- **Statistical overlays**: Property distributions shown inline

### Interactive Exploration
- **Pan & Zoom**: Smooth mouse/touch controls
- **Rich tooltips**: Hover to see all node properties
- **Keyboard shortcuts**: Quick access to layouts and features
- **Responsive**: Works on desktop and mobile

### Hierarchical Data Center Visualization
- **Multi-level drill-down**: Data Centers → Racks → Servers → Processes
- **Heat-map status coloring**: Green (healthy), Orange (warning), Red (critical)
- **Operational metrics rings**: PUE, power phases, resource usage per level
- **Spatial troubleshooting**: Visual patterns reveal network failures, resource exhaustion
- **OS-specific coloring**: Blue (Linux), Orange (Windows), Purple (ESXi)
- **Breadcrumb navigation**: Easy navigation with up/home buttons
- **Dependency visualization**: See API calls, database connections geometrically
- **"Noisy neighbor" detection**: Visually identify resource-hogging processes

### Neo4j Integration
- **Direct database connection**: Connect to Neo4j bolt protocol
- **Cypher query support**: Execute custom queries
- **Auto-clustering**: Automatic cluster detection from node labels
- **Real-time loading**: Load graphs on-demand from your database

## Installation

```bash
npm install
```

## Development

```bash
npm run dev
```

Open your browser to the URL shown (typically http://localhost:5173)

## Build

```bash
npm run build
```

## Using with Neo4j

### Setup

1. Start your Neo4j database (local or remote)
2. Run the development server: `npm run dev`
3. In the Neo4j panel (top-right):
   - Enter your bolt URI (e.g., `bolt://localhost:7687`)
   - Enter username (default: `neo4j`)
   - Enter password
   - Click **Connect**

### Loading Data

Once connected, you can:
- **Load Graph**: Load a limited number of nodes and relationships
- **Custom Query**: Execute your own Cypher queries (coming soon)

The visualization will automatically:
- Group nodes by label into clusters
- Calculate node importance from degree
- Apply force-directed layout
- Generate cluster statistics if demographic data is present

### Example Cypher Queries

Load from the connector manually in browser console:

```javascript
// Load all Person nodes and their relationships
const result = await app.neo4j.loadByLabel('Person', 50);

// Load neighborhood around a specific node
const result = await app.neo4j.loadNeighborhood('123', 2);

// Custom query
const result = await app.neo4j.executeQuery(`
  MATCH (p:Person)-[r:KNOWS]-(f:Person)
  RETURN p, r, f
  LIMIT 100
`);
```

## Keyboard Shortcuts

- **R** - Reset view to center
- **L** - Apply force-directed layout
- **C** - Apply cluster layout (groups by type)
- **H** - Apply hierarchical layout
- **1** - Load sample graph (small, curated)
- **2** - Load medium graph (50 nodes)
- **3** - Load large graph (100 nodes)
- **4** - Load clustered graph with demographics
- **5** - 🖥️ Load Data Center Hierarchy Mode
- **T** - Toggle cluster backgrounds
- **G** - Toggle cluster rings/donut charts
- **↑ Arrow** - Navigate up one level (hierarchy mode)

## Mouse Controls

- **Scroll Wheel** - Zoom in/out
- **Click & Drag** - Pan around the graph
- **Hover** - Show detailed node information
- **Double-Click** - Drill down into node hierarchy (Data Center → Rack → Server → Process)

## Configuration

Adjust these controls in the UI:

- **Node Size**: Scale all nodes up or down
- **Info Density**:
  - Level 1: Basic (type badges only)
  - Level 2: Medium (property counts, edge labels)
  - Level 3: Ultra-dense (inline properties visible)

## Architecture

- **TypeScript**: Type-safe development
- **Canvas Rendering**: High-performance 2D graphics
- **Custom Layout Engine**: Multiple graph layout algorithms
- **Modular Design**: Easy to extend and customize

## Data Center Hierarchy Mode

### Overview

The hierarchical visualization mode transforms abstract infrastructure data into a spatial, navigable environment. Instead of lists and dashboards, you see your entire datacenter topology laid out geometrically.

### How It Works

1. **Press 5** to load data center mode
2. **Double-click any node** to zoom into its contents
3. **Use breadcrumb buttons** (top-center) to navigate back up
4. **Press ↑ arrow** to go up one level

### The Four Levels

#### Level 1: Data Centers
**What you see**: Geographic data center locations (US-East-1, US-West-2, EU-Central-1)

**Ring metrics**:
- PUE (Power Usage Effectiveness) - <1.3 is healthy
- Total power consumption (kW)
- Network bandwidth (Gbps)
- Temperature (°C)

**Status colors**:
- 🟢 Green: All systems normal
- 🟠 Orange: Warning (high temp, power approaching limits)
- 🔴 Red: Critical issues

**Use cases**:
- Identify which datacenter is most efficient (lowest PUE)
- See inter-datacenter WAN latency
- Spot cooling problems before they become critical

#### Level 2: Racks
**What you see**: Physical rack units within the selected datacenter

**Ring metrics**:
- Power Phase A vs Phase B loading
- Used vs. total rack units (42U standard)
- Network switch port utilization

**Status**: Racks turn orange if power draw exceeds 22kW (approaching circuit limits)

**Use cases**:
- Balance power across feeds A and B
- Find empty rack space for new servers
- Visualize spine-leaf network topology
- Identify racks with switch capacity issues

#### Level 3: Servers
**What you see**: Individual physical/virtual servers in the rack

**Heat-map coloring** (by CPU/RAM usage):
- 🟢 <65%: Healthy
- 🟠 65-80%: Warning
- 🔴 >80%: Critical

**OS-specific colors**:
- 🔵 Blue: Linux
- 🟠 Orange: Windows
- 🟣 Purple: ESXi/VMware
- 💗 Pink: FreeBSD
- 💠 Cyan: Containers

**Metrics displayed**:
- CPU cores & usage %
- RAM capacity & usage %
- Disk IOPS
- Network throughput (Mbps)

**Edge patterns**:
- Thick lines = high traffic between servers
- Shows "east-west" traffic within rack
- Reveals unexpected dependencies

**Use cases**:
- Identify servers approaching resource limits
- See which servers talk to each other
- Plan VM migrations by viewing dependencies
- Spot the "noisy neighbor" - one VM hogging resources

#### Level 4: Processes
**What you see**: Running processes, containers, or services

**Metrics**:
- Memory consumption (MB)
- CPU percentage
- Thread count
- Active connections

**Edges**: API calls, database queries, inter-process communication

**Use cases**:
- Trace dependency chains (web server → API → database)
- Find processes consuming excessive resources
- Identify security issues (unexpected connections)
- Debug microservice communication problems

### Spatial Troubleshooting Examples

**Example 1: Network Failure**
```
Symptom: A rack (Level 2) has no edges connecting it to other racks
Diagnosis: Top-of-rack switch failure
Action: Visual pattern immediately shows the problem
```

**Example 2: Power Imbalance**
```
Symptom: Rack ring shows Feed A at 23kW, Feed B at 8kW
Diagnosis: Poor power distribution across dual feeds
Action: Rebalance servers to equalize power phases
```

**Example 3: Noisy Neighbor**
```
Symptom: At Level 3, one huge red node crowds out others
Diagnosis: Single VM consuming 90% CPU
Action: Immediately visible without parsing logs
```

**Example 4: Dependency Discovery**
```
Symptom: Web server (Level 4) has edge to HR database
Diagnosis: Unexpected data access - possible security issue
Action: Geometric view reveals "shouldn't happen" connections
```

### Why This Is Revolutionary

Traditional dashboards show:
- Lists of servers
- Tables of metrics
- Line charts over time

Hierarchical visualization shows:
- **Topology** - How things connect
- **Blast radius** - What fails when you take something down
- **Spatial patterns** - Issues visible geometrically
- **Context** - Where in the infrastructure you are

It's the difference between reading street addresses and looking at a map.

## Project Structure

```
src/
  ├── types.ts              # TypeScript interfaces
  ├── renderer.ts           # Canvas rendering engine
  ├── layout.ts             # Graph layout algorithms
  ├── interactions.ts       # Mouse/touch event handling
  ├── data.ts               # Sample data generation
  ├── hierarchy-types.ts    # Hierarchy type definitions
  ├── hierarchy-controller.ts  # Drill-down state management
  ├── datacenter-data.ts    # IT infrastructure data generator
  ├── cluster-data.ts       # Demographic cluster data
  ├── cluster-renderer.ts   # Cluster & ring visualization
  └── main.ts               # Application entry point
```

## Customization

### Adding Your Own Data

Replace the sample data in `src/data.ts` or load from your graph database:

```typescript
import { GraphData } from './types';

const myGraphData: GraphData = {
  nodes: [
    {
      id: 'node1',
      label: 'My Node',
      type: 'CustomType',
      properties: {
        key1: 'value1',
        key2: 'value2'
      },
      x: 0,
      y: 0
    }
  ],
  edges: [
    {
      source: 'node1',
      target: 'node2',
      type: 'RELATIONSHIP',
      weight: 1.5
    }
  ]
};
```

### Customizing Colors

Edit the `typeColors` map in `src/renderer.ts`:

```typescript
private typeColors: Map<string, string> = new Map([
  ['YourType', '#yourcolor'],
  // ...
]);
```

## Performance

- Handles 100+ nodes smoothly on modern hardware
- Canvas-based rendering for efficiency
- Optimized layout algorithms
- FPS counter for monitoring performance

## License

MIT
