# NetMapper

A strongly-typed Python network topology discovery tool using PyATS and Neo4j. NetMapper automatically discovers network devices using CDP/LLDP, collects interface, VLAN, and STP data, and builds a comprehensive topology map in Neo4j. Additionally implements the **Bejerano et al. 2003 algorithm** for Layer 2 physical topology discovery using MAC address forwarding tables.

## Features

- **Adaptive Parallel Discovery (15-30x faster)**: Self-tuning async architecture
  - **Adaptive worker scaling**: Automatically adjusts from 5-100+ workers based on queue depth
  - **Batched Neo4j writes**: Dynamic batch sizing (10-500 operations) for 10-100x faster database writes
  - **"Waiting is infinitely parallelizable"**: Async coroutines use ~5 KB each, RAM is the only limit
  - **Self-optimizing**: No manual tuning required, scales up when busy, down when idle
  - Backwards compatible fixed-worker and sequential modes available
- **Automated Discovery**: Queue-based network traversal starting from a single device
- **Multiple Discovery Protocols**: CDP and LLDP support
- **Bejerano Layer 2 Topology Discovery**: Physical topology inference from MAC tables
  - Discovers switch-to-switch connections via SNMP or PyATS
  - Detects uncooperative elements (hubs, unmanaged switches)
  - Independent verification of CDP/LLDP topology
- **Comprehensive Data Collection**:
  - Device information (hostname, platform, version, etc.)
  - Physical ports (status, speed, duplex)
  - Logical interfaces (IP addresses, VLANs)
  - VLAN configuration
  - STP topology per VLAN
  - MAC address forwarding tables
- **Smart Cable Tracking**: Automatic generation of unique 4-character alphanumeric cable IDs
- **Loop Prevention**: Tracks visited devices to prevent infinite discovery loops
- **Strongly Typed**: Full type hints for better IDE support and code quality
- **Neo4j Graph Database**: Rich graph-based topology representation
- **🎨 Two Powerful Visualization Frontends**:
  - **Option 1: React Dashboard** (`frontend/`) - Recommended for most users
    - D3.js Hierarchy View: Zoomable circle packing
    - Cytoscape.js Topology View: Interactive network graph with compound nodes
    - Real-time status monitoring, SSH/trace actions, device details modal
  - **Option 2: GraphUI** (`frontend-graphui/`) - Advanced dense visualization
    - Canvas-based ultra-dense rendering (1000s of nodes)
    - "Google Earth for Data Centers" hierarchical drill-down
    - Direct Neo4j bolt connection with Cypher queries
    - Multiple layout algorithms and spatial troubleshooting
  - **See [VISUALIZATION_OPTIONS.md](VISUALIZATION_OPTIONS.md) for comparison and setup**

## Architecture

### Data Model

#### Layer 1 (Physical Topology)
```
(NetworkDevice)-[:HAS_PORT]->(Port)-[:CABLE_END_A]->(Cable)<-[:CABLE_END_B]-(Port)<-[:HAS_PORT]-(NetworkDevice)
```

#### Layer 2 (Logical Topology)
```
(NetworkDevice)-[:HAS]->(Interface)-[:CDP_NEIGHBOR]->(Interface)<-[:HAS]-(NetworkDevice)
(NetworkDevice)-[:HAS]->(Interface)-[:LLDP_NEIGHBOR]->(Interface)<-[:HAS]-(NetworkDevice)
```

#### STP Topology
```
(NetworkDevice)-[:HAS_STP]->(STPInstance)-[:STP_INTERFACE]->(Interface)
```

#### VLAN Information
```
(NetworkDevice)-[:HAS_VLAN]->(VLAN)
```

### Node Properties

**NetworkDevice**
- hostname (unique)
- mgmt_ip
- platform
- model
- serial_number
- software_version

**Port**
- name
- device_hostname
- status (up/down/admin-down)
- speed
- duplex
- description
- vlan

**Interface**
- name
- device_hostname
- ip_address
- subnet_mask
- status
- vlan
- description

**Cable**
- id (unique 4-char alphanumeric)
- type (copper/fiber/unknown)
- length (optional)

**STPInstance**
- device_hostname
- vlan_id
- bridge_priority
- bridge_address
- root_bridge_priority
- root_bridge_address
- root_port
- root_path_cost
- is_root

**VLAN**
- device_hostname
- vlan_id
- name
- status
- ports (list)

## Installation

### Prerequisites

- Python 3.9 or higher
- Neo4j database (4.x or 5.x)
- Network access to Cisco devices via SSH/Telnet
- PyATS/Genie libraries

### Install Dependencies

```bash
pip install -r requirements.txt
```

Or install in development mode:

```bash
pip install -e .
```

### Setup Neo4j

1. Install Neo4j (https://neo4j.com/download/)
2. Start Neo4j service
3. Set initial password via Neo4j Browser (http://localhost:7474)
4. Update `config.yaml` with Neo4j credentials

## Configuration

1. Copy the example configuration:

```bash
cp config.example.yaml config.yaml
```

2. Edit `config.yaml` with your settings:

```yaml
start_device:
  hostname: "your-core-switch"
  ip: "192.168.1.1"
  username: "admin"
  password: "your-password"
  os: "ios"  # or iosxe, nxos, iosxr

neo4j:
  uri: "bolt://localhost:7687"
  username: "neo4j"
  password: "your-neo4j-password"

discovery:
  max_depth: null  # null for unlimited, or set a number
  discover_cdp: true
  discover_lldp: true
  discover_stp: true
  discover_vlans: true

parallel:
  enable: true
  enable_adaptive_tuning: true  # Self-tuning workers
  min_workers: 5
  adaptive_max_workers: 100     # RAM is the only limit!
  enable_neo4j_batching: true   # 10-100x faster writes
```

## Usage

### Adaptive Discovery (Recommended - 15-30x faster)

The default mode uses adaptive worker tuning and batched Neo4j writes for optimal performance:

```bash
# Default: Adaptive mode (5-100 workers, self-tuning)
python -m netmapper.main_unified

# Verbose mode to see worker scaling in action
python -m netmapper.main_unified -v

# Conservative settings (for limited RAM)
# Edit config.yaml: adaptive_max_workers: 20
python -m netmapper.main_unified
```

**See [ADAPTIVE_TUNING.md](ADAPTIVE_TUNING.md) for detailed adaptive features guide.**
**See [PARALLEL_DISCOVERY.md](PARALLEL_DISCOVERY.md) for general parallelism concepts.**

### Fixed Worker Mode (10-50x faster)

```bash
# Disable adaptive tuning for fixed worker count
# Edit config.yaml: enable_adaptive_tuning: false
python -m netmapper.main_unified --workers 20
```

### Sequential Mode (Legacy)

```bash
# Force sequential mode
python -m netmapper.main_unified --sequential

# Or use the original entry point
python -m netmapper.main
```

### With Custom Config File

```bash
python -m netmapper.main_unified -c /path/to/config.yaml
```

### Using as a Python Module

```python
from netmapper.models import DiscoveryConfig, DeviceCredentials
from netmapper.discovery import NetworkDiscovery

# Create configuration
config = DiscoveryConfig(
    start_device=DeviceCredentials(
        hostname="switch01",
        ip="192.168.1.1",
        username="admin",
        password="cisco123",
        os="ios"
    ),
    neo4j_uri="bolt://localhost:7687",
    neo4j_username="neo4j",
    neo4j_password="password"
)

# Run discovery
discovery = NetworkDiscovery(config)
try:
    discovery.run()
finally:
    discovery.close()
```

### Hybrid Discovery (PyATS + Bejerano)

For complete topology discovery including Layer 2 physical topology:

```bash
# Run hybrid discovery with SNMP-based MAC collection
python -m netmapper.main_hybrid

# Run with PyATS-based MAC collection (no SNMP required)
# Edit config.yaml: mac_collection_method: "pyats"
python -m netmapper.main_hybrid
```

**See [BEJERANO_ALGORITHM.md](BEJERANO_ALGORITHM.md) for detailed documentation.**

## How It Works

1. **Initialization**: Connects to Neo4j and loads existing devices to prevent re-discovery
2. **Queue Setup**: Adds the starting device to the work queue
3. **Device Discovery Loop**:
   - Dequeue next device
   - Skip if already visited (critical for preventing infinite loops)
   - Connect via PyATS
   - Collect CDP/LLDP neighbors, interfaces, ports, VLANs, and STP data
   - Store in Neo4j with proper relationships
   - Generate unique cable IDs for each CDP neighbor pair
   - Add unvisited neighbors to queue
4. **Repeat**: Process continues until queue is empty or max depth reached

## Neo4j Queries

### Find All Devices

```cypher
MATCH (d:NetworkDevice)
RETURN d
```

### Find Cable Connections

```cypher
MATCH (d1:NetworkDevice)-[:HAS_PORT]->(p1:Port)-[:CABLE_END_A]->(c:Cable)<-[:CABLE_END_B]-(p2:Port)<-[:HAS_PORT]-(d2:NetworkDevice)
RETURN d1.hostname, p1.name, c.id, p2.name, d2.hostname
```

### Find CDP Neighbors

```cypher
MATCH (d1:NetworkDevice)-[:HAS]->(i1:Interface)-[:CDP_NEIGHBOR]->(i2:Interface)<-[:HAS]-(d2:NetworkDevice)
RETURN d1.hostname, i1.name, d2.hostname, i2.name
```

### Find STP Root Bridges

```cypher
MATCH (d:NetworkDevice)-[:HAS_STP]->(s:STPInstance {is_root: true})
RETURN d.hostname, s.vlan_id, s.bridge_address
```

### Find Devices by VLAN

```cypher
MATCH (d:NetworkDevice)-[:HAS_VLAN]->(v:VLAN {vlan_id: 10})
RETURN d.hostname, v.name, v.ports
```

### Find STP Topology for VLAN

```cypher
MATCH (d:NetworkDevice)-[:HAS_STP]->(s:STPInstance {vlan_id: 1})-[r:STP_INTERFACE]->(i:Interface)
RETURN d.hostname, i.name, r.role, r.state, r.cost
ORDER BY d.hostname, i.name
```

## Visualization Options

NetMapper provides **two powerful visualization frontends** to explore your network topology.

**📖 For detailed comparison and setup guide, see [VISUALIZATION_OPTIONS.md](VISUALIZATION_OPTIONS.md)**

### Option 1: React Dashboard (Recommended)

**Location**: `frontend/` | **Best for**: Most users, network operations

```bash
cd frontend
npm install
npm start
# Open http://localhost:3000
```

**Features**:
- 📊 **Hierarchy View**: D3.js zoomable circle packing
- 🌐 **Topology View**: Cytoscape.js network graph with compound nodes
- 💡 **Interactive**: View toggle, status modal, SSH/trace actions
- 📈 **Dashboard**: Real-time statistics and device details
- 🎯 **Easy Integration**: REST API for Neo4j data

See [frontend/README.md](frontend/README.md) and [frontend/QUICKSTART.md](frontend/QUICKSTART.md) for details.

### Option 2: GraphUI (Advanced)

**Location**: `frontend-graphui/` | **Best for**: Dense visualization, data center ops

```bash
cd frontend-graphui
npm install
npm run dev
# Open http://localhost:5173
# Press 5 for Data Center mode, double-click to drill down
```

**Features**:
- 🎨 **Ultra-dense rendering**: Maximum information in minimal space
- 🖥️ **"Google Earth for Data Centers"**: 4-level hierarchical drill-down
- ⚡ **Direct Neo4j**: Bolt protocol connection, real-time Cypher queries
- 📊 **Advanced layouts**: Force-directed, cluster-based, hierarchical
- 🔍 **Spatial troubleshooting**: Visual pattern recognition

See [frontend-graphui/README.md](frontend-graphui/README.md) for details.

### Which One Should I Use?

| Use Case | Recommended Frontend |
|----------|---------------------|
| Network operations (SSH, trace, config) | **React Dashboard** |
| Familiar dashboard interface | **React Dashboard** |
| Mobile/tablet access | **React Dashboard** |
| Data center infrastructure management | **GraphUI** |
| Deep dependency analysis | **GraphUI** |
| Maximum information density | **GraphUI** |
| Direct Neo4j queries | **GraphUI** |

**You can run both simultaneously** - they can connect to the same Neo4j database!

## Supported Platforms

NetMapper supports all platforms compatible with PyATS/Genie:

- Cisco IOS
- Cisco IOS-XE
- Cisco IOS-XR
- Cisco NX-OS
- And more (see PyATS documentation)

## Type Safety

NetMapper is fully type-hinted using Pydantic models for data validation:

- All network data is validated against Pydantic schemas
- IDE auto-completion and type checking support
- Runtime validation of configuration and collected data

## Logging

NetMapper provides detailed logging:

- INFO: High-level progress and status
- DEBUG: Detailed data collection and processing (use `-v` flag)
- WARNING: Non-critical issues (e.g., unsupported features)
- ERROR: Critical failures

## Troubleshooting

### Connection Failures

- Verify network connectivity to devices
- Check SSH/Telnet credentials
- Ensure proper enable password if required
- Verify device OS type in configuration

### Missing Neighbors

- Check if CDP/LLDP is enabled on devices
- Verify neighbor devices are reachable
- Check that neighbor IP addresses are collected

### Neo4j Errors

- Verify Neo4j is running
- Check connection credentials
- Ensure sufficient memory for large topologies

## Security Considerations

- Store `config.yaml` securely (contains passwords)
- Use enable secrets where appropriate
- Consider using SSH keys instead of passwords
- Limit network discovery scope with `max_depth`

## Performance

### Adaptive Mode (Default)
- **15-30x faster** than sequential discovery
- **1.5-2x faster** than fixed parallel mode
- Automatically scales workers (5-100+) based on queue depth
- Batched Neo4j writes (10-500 operations per batch)
- Memory: Async coroutines use ~5 KB each, 100 workers = ~500 KB overhead
- **Total RAM usage**: ~5-6 GB with 100 workers (includes PyATS objects)

### Discovery Speed
- **Network I/O is 95%+ of time**, not Python processing
- Each device: 15-30 seconds (mostly SSH and command execution)
- Small networks (<50 devices): 2-5 minutes
- Medium networks (50-200 devices): 5-15 minutes
- Large networks (200-500 devices): 10-30 minutes
- Very large networks (500-1000 devices): 20-60 minutes

### Tuning Guidelines
- **Default settings** (5-100 workers) work well for most networks
- **Limited RAM** (4 GB): Set `adaptive_max_workers: 50`
- **Lots of RAM** (16+ GB): Set `adaptive_max_workers: 200`
- **Slow switches**: System naturally throttles, no tuning needed

**See [ADAPTIVE_TUNING.md](ADAPTIVE_TUNING.md) for detailed performance benchmarks and tuning.**

## Contributing

Contributions are welcome! Please ensure:

- Code follows type hints conventions
- All functions have docstrings
- New features include appropriate logging

## License

This project is provided as-is for network automation purposes.

## Support

For issues and questions:
- Check logs with `-v` verbose mode
- Verify configuration settings
- Test connectivity manually before running discovery
