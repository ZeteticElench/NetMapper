# NetMapper GUI Guide

## Overview

NetMapper GUI is a PySide6-based graphical user interface for network topology discovery and visualization with DMTF CIM relationship management.

## Features

### 1. Network Discovery
- Configure target device credentials
- Set discovery options (CDP, LLDP, STP, VLANs)
- Parallel discovery with configurable workers
- Real-time progress monitoring
- Bejerano Layer 2 topology discovery

### 2. Topology Visualization
- Interactive network graph visualization
- Multiple layout algorithms:
  - **Circular**: Nodes arranged in a circle
  - **Force-Directed**: Spring-embedded layout
  - **Hierarchical**: Level-based layout
- Drag-and-drop node repositioning
- Mouse wheel zooming
- Pan with drag
- Color-coded relationship types:
  - Green: CDP/LLDP neighbor relationships
  - Orange: CIM relationships
  - Gray: Other relationships

### 3. CIM Relationship Management
- Create CIM nesting relationships:
  - **CIM_CONTAINER**: Physical containment (movable items)
  - **CIM_COMPONENT**: Composition (integral subcomponents)
  - **CIM_MEMBER_OF_COLLECTION**: Logical hierarchy
- View existing relationships in table
- Browse hierarchy as tree structure
- Support for:
  - Location within container
  - Removal conditions
  - Weak/strong relationships (composition vs aggregation)
  - Custom properties (JSON)

### 4. Query Interface
- Execute Cypher queries against Neo4j
- Predefined query templates:
  - All Devices
  - All CIM Relationships
  - CIM Containers
  - CIM Components
  - Device Connections
  - Cables
  - VLANs
  - STP Root Bridges
- Custom query support
- Tabular results display

## Installation

### Prerequisites

1. **Python 3.8+**
2. **Neo4j Database** (running and accessible)
3. **NetMapper Core** (see main README)

### Install GUI Dependencies

```bash
cd NetMapper
pip install -r requirements-gui.txt
```

This will install:
- PySide6 (Qt for Python)
- All NetMapper core dependencies

## Running the GUI

### Method 1: Launcher Script

```bash
cd NetMapper
./netmapper-gui
```

### Method 2: Python Module

```bash
cd NetMapper
python -m gui.main_window
```

### Method 3: Direct Execution

```bash
cd NetMapper
python gui/main_window.py
```

## Configuration

### First Time Setup

1. Launch the application
2. Click **Settings** in the toolbar
3. Configure Neo4j connection:
   - **URI**: `bolt://localhost:7687` (default)
   - **Username**: `neo4j` (default)
   - **Password**: Your Neo4j password
4. Click **Test Connection** to verify
5. Click **OK** to save

Settings are persisted between sessions.

## User Interface

### Main Window

The main window contains four tabs:

#### 1. Discovery Tab

**Purpose**: Configure and run network discovery

**Fields**:
- **Hostname**: Target device hostname
- **IP Address**: Management IP address
- **Username**: SSH/Telnet username
- **Password**: SSH/Telnet password
- **Enable Password**: Enable mode password (optional)
- **OS Type**: Device OS (ios, iosxe, nxos, iosxr, asa)

**Discovery Options**:
- **Max Depth**: Maximum discovery depth (default: 10)
- **Discover CDP**: Enable CDP neighbor discovery
- **Discover LLDP**: Enable LLDP neighbor discovery
- **Discover STP**: Enable Spanning Tree discovery
- **Discover VLANs**: Enable VLAN discovery
- **Enable Bejerano L2**: Enable Bejerano Layer 2 algorithm
- **Parallel Discovery**: Enable parallel worker threads
- **Max Workers**: Number of parallel workers (default: 10)

**Workflow**:
1. Fill in device credentials
2. Configure discovery options
3. Click **Start Discovery**
4. Monitor progress in log output
5. Switch to Topology tab to view results

#### 2. Topology Tab

**Purpose**: Visualize discovered network topology

**Controls**:
- **Refresh Topology**: Reload topology from database
- **Layout**: Select layout algorithm
  - Circular
  - Force-Directed
  - Hierarchical
- **Zoom**: Adjust zoom level (10% - 200%)

**Interaction**:
- **Pan**: Click and drag background
- **Zoom**: Mouse wheel
- **Move Node**: Click and drag node
- **Select Node**: Click node (highlights in selection color)

**Node Colors**:
- **Cyan/Teal**: Network devices
- **Green Edges**: CDP/LLDP relationships
- **Orange Edges**: CIM relationships

#### 3. CIM Relationships Tab

**Purpose**: Create and manage CIM nesting relationships

**Create Relationship**:
1. Enter **Parent ID** (e.g., `rack-01`)
2. Enter **Child ID** (e.g., `server-01`)
3. Select **Relationship Type**:
   - `CIM_CONTAINER`: Physical containment
   - `CIM_COMPONENT`: Integral subcomponent
   - `CIM_MEMBER_OF_COLLECTION`: Logical membership
4. Enter **Location** (e.g., `U42`, `Slot 1`)
5. Select **Removal Conditions**:
   - Unknown
   - Not Applicable
   - Removable when off
   - Removable when on or off
6. Check **Is Weak** if child cannot exist without parent (composition)
7. Optionally add **Custom Properties** as JSON
8. Click **Create Relationship**

**Examples**:

**Example 1: Rack contains Server**
```
Parent ID: rack-01
Child ID: server-01
Type: CIM_CONTAINER
Location: U42-U44
Removal: Removable when off
Is Weak: No (server can exist independently)
```

**Example 2: Server has Power Supply**
```
Parent ID: server-01
Child ID: psu-01
Type: CIM_COMPONENT
Location: PSU Bay 1
Removal: Removable when off
Is Weak: Yes (PSU cannot exist without server)
Custom Props: {"wattage": 750, "redundant": true}
```

**Example 3: Device in Collection**
```
Parent ID: collection-core-switches
Child ID: switch-01
Type: CIM_MEMBER_OF_COLLECTION
Location: (leave empty)
Is Weak: No
Custom Props: {"role": "primary", "redundancy_group": "1"}
```

**View Hierarchy**:
- Click **View Hierarchy Tree** to see hierarchical tree view
- Expands all CIM relationships from root nodes
- Shows location within container for each node

#### 4. Query Tab

**Purpose**: Execute Cypher queries against Neo4j

**Usage**:
1. Select a **Query Template** or write custom query
2. Review/edit query in text editor
3. Click **Execute Query**
4. View results in table

**Query Templates**:

**All Devices**:
```cypher
MATCH (d:NetworkDevice)
RETURN d.hostname, d.platform, d.model, d.mgmt_ip
LIMIT 25
```

**All CIM Relationships**:
```cypher
MATCH (parent)-[r]->(child)
WHERE r.relationship_type IS NOT NULL
RETURN
    COALESCE(parent.id, parent.hostname) as parent,
    type(r) as relationship,
    COALESCE(child.id, child.hostname) as child,
    r.location_within_container as location
LIMIT 50
```

**Custom Queries**:
- Write any valid Cypher query
- Results displayed in table format
- Supports all Neo4j data types

## Workflow Examples

### Example 1: Complete Network Discovery

1. **Configure Target**:
   - Navigate to **Discovery** tab
   - Enter seed device credentials
   - Set max depth: 5
   - Enable all discovery options

2. **Run Discovery**:
   - Click **Start Discovery**
   - Monitor progress in log
   - Wait for completion

3. **View Topology**:
   - Switch to **Topology** tab
   - Click **Refresh Topology**
   - Select **Force-Directed** layout
   - Zoom and pan to explore

4. **Query Results**:
   - Switch to **Query** tab
   - Select "All Devices" template
   - Click **Execute Query**
   - Review device list

### Example 2: Build CIM Hierarchy

1. **Create Datacenter**:
   ```
   (Manually create parent node in Neo4j or use GUI to create relationships)
   ```

2. **Add Rack to Datacenter**:
   - **CIM Relationships** tab
   - Parent: `datacenter-dc1`
   - Child: `rack-01`
   - Type: `CIM_CONTAINER`
   - Location: `Row A, Position 1`

3. **Add Server to Rack**:
   - Parent: `rack-01`
   - Child: `server-01`
   - Type: `CIM_CONTAINER`
   - Location: `U42-U44`

4. **Add PSU to Server**:
   - Parent: `server-01`
   - Child: `psu-srv01-1`
   - Type: `CIM_COMPONENT`
   - Location: `PSU Bay 1`
   - Is Weak: **Yes**

5. **View Hierarchy**:
   - Click **View Hierarchy Tree**
   - See complete hierarchy:
     ```
     datacenter-dc1
     └── rack-01 (Row A, Position 1)
         └── server-01 (U42-U44)
             └── psu-srv01-1 (PSU Bay 1)
     ```

### Example 3: Query CIM Components

1. **Query Tab**
2. Select "CIM Components" template
3. Query shows all integral components:
   ```
   Parent         | Child          | Location
   ---------------|----------------|----------
   server-01      | psu-srv01-1    | PSU Bay 1
   server-01      | psu-srv01-2    | PSU Bay 2
   switch-sw01    | linecard-01    | Slot 1
   ```

## Troubleshooting

### Connection Issues

**Problem**: Cannot connect to Neo4j

**Solutions**:
1. Verify Neo4j is running: `systemctl status neo4j`
2. Check URI in Settings: `bolt://localhost:7687`
3. Verify username/password
4. Test connection in Settings dialog

### Discovery Fails

**Problem**: Discovery does not start or fails

**Solutions**:
1. Verify device credentials are correct
2. Check network connectivity to target device
3. Ensure PyATS is installed: `pip install pyats genie`
4. Review log output for specific errors

### Empty Topology

**Problem**: Topology tab shows no devices

**Solutions**:
1. Run discovery first (Discovery tab)
2. Click **Refresh Topology** to reload
3. Verify data in Neo4j:
   ```cypher
   MATCH (d:NetworkDevice) RETURN count(d)
   ```

### GUI Not Starting

**Problem**: `netmapper-gui` command fails

**Solutions**:
1. Verify PySide6 is installed:
   ```bash
   pip install -r requirements-gui.txt
   ```
2. Check Python version: `python --version` (3.8+ required)
3. Run directly:
   ```bash
   python gui/main_window.py
   ```

## Keyboard Shortcuts

- **Ctrl+R**: Refresh current tab
- **Ctrl+Q**: Quit application
- **Mouse Wheel**: Zoom in/out (Topology tab)
- **Click+Drag**: Pan view or move node

## Performance Tips

1. **Large Networks**: Use query limits
   ```cypher
   MATCH (d:NetworkDevice) RETURN d LIMIT 100
   ```

2. **Slow Topology Rendering**: Reduce displayed nodes
   - Filter by device type
   - Use depth limits in discovery

3. **Parallel Discovery**: Adjust max workers based on CPU
   - More workers = faster discovery
   - Too many workers = resource contention
   - Recommended: 5-20 workers

## Advanced Features

### Custom CIM Properties

Add domain-specific metadata to relationships:

```json
{
    "power_watts": 750,
    "redundant": true,
    "part_number": "ABC-123",
    "serial_number": "SN123456",
    "vendor": "Cisco",
    "warranty_expiration": "2025-12-31"
}
```

### Export Topology

Use Query tab to export data:

```cypher
MATCH (d:NetworkDevice)
RETURN d.hostname as hostname,
       d.mgmt_ip as ip,
       d.platform as platform
```

Copy results from table to CSV.

### Batch Relationship Creation

For bulk CIM relationship creation, use the Neo4j manager directly:

```python
from netmapper.neo4j_manager import Neo4jManager
from netmapper.models import CIMNestingRelationship, CIMRelationshipType

manager = Neo4jManager("bolt://localhost:7687", "neo4j", "password")

# Create multiple relationships
for i in range(1, 11):
    rel = CIMNestingRelationship(
        parent_id=f"rack-{i}",
        child_id=f"server-{i}",
        relationship_type=CIMRelationshipType.CONTAINER,
        location_within_container=f"U{i*4}",
    )
    manager.create_cim_nesting_relationship(rel)
```

## Architecture

```
NetMapper GUI
├── main_window.py       # Main application window
├── discovery_tab.py     # Discovery configuration
├── topology_tab.py      # Network visualization
├── cim_relationships_tab.py  # CIM management
├── query_tab.py         # Cypher query interface
└── settings_dialog.py   # Application settings
```

**Technologies**:
- **PySide6**: Qt6 Python bindings for GUI
- **QGraphicsView**: 2D graph visualization
- **QSettings**: Persistent configuration
- **QThread**: Background task execution
- **Neo4j Python Driver**: Database connectivity

## Contributing

To extend the GUI:

1. Add new tabs by creating a new widget class
2. Register in `main_window.py`:
   ```python
   self.my_tab = MyCustomTab(self)
   self.tabs.addTab(self.my_tab, "My Tab")
   ```
3. Implement `refresh()` and `update_neo4j_settings()` methods
4. Update this documentation

## License

Same as NetMapper core project.

## Support

For issues, feature requests, or questions:
- GitHub Issues: https://github.com/ZeteticElench/NetMapper/issues
- Documentation: NetMapper/docs/
