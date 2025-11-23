# NetMapper GUI

Native desktop application for network topology discovery and visualization with DMTF CIM relationship management.

![NetMapper GUI](https://img.shields.io/badge/GUI-PySide6-green)
![Python](https://img.shields.io/badge/Python-3.8+-blue)

## Quick Start

### Installation

```bash
# Install GUI dependencies
pip install -r requirements-gui.txt

# Launch application
./netmapper-gui
```

### First Run

1. Click **Settings** in toolbar
2. Configure Neo4j connection:
   - URI: `bolt://localhost:7687`
   - Username: `neo4j`
   - Password: `your-password`
3. Click **Test Connection**
4. Click **OK** to save

## Features

### 🔍 Network Discovery
- Configure target device credentials (SSH/Telnet)
- Set discovery options (CDP, LLDP, STP, VLANs)
- Parallel discovery with adaptive workers
- Real-time progress monitoring
- Bejerano Layer 2 topology discovery

### 🎨 Topology Visualization
- Interactive network graph with drag-and-drop
- Multiple layout algorithms:
  - Circular
  - Force-Directed (spring embedding)
  - Hierarchical (level-based)
- Mouse wheel zoom, click-and-drag pan
- Color-coded relationships:
  - 🟢 Green: CDP/LLDP neighbors
  - 🟠 Orange: CIM relationships
  - ⚪ Gray: Other connections

### 🏗️ CIM Relationship Management
- Create DMTF CIM nesting relationships:
  - **CIM_CONTAINER**: Physical containment (racks → servers)
  - **CIM_COMPONENT**: Integral parts (server → PSU)
  - **CIM_MEMBER_OF_COLLECTION**: Logical groups
- View relationships in table format
- Browse complete hierarchy as tree
- Support for location, removal conditions, custom properties

### 🔎 Query Interface
- Execute Cypher queries against Neo4j
- Predefined templates:
  - All Devices
  - CIM Relationships
  - Containers & Components
  - Cables, VLANs, STP
- Custom query support
- Tabular results display

## Usage Examples

### Run Network Discovery

1. **Discovery** tab
2. Fill in device details:
   - Hostname: `core-switch-01`
   - IP: `192.168.1.1`
   - Username: `admin`
   - Password: `********`
   - OS: `ios`
3. Set options:
   - Max Depth: `5`
   - Enable all discovery protocols
4. Click **Start Discovery**
5. Monitor progress in log
6. Switch to **Topology** tab when complete

### Create CIM Hierarchy

**Example: Rack contains Server with PSU**

1. **CIM Relationships** tab

2. Add Server to Rack:
   ```
   Parent ID: rack-01
   Child ID: server-01
   Type: CIM_CONTAINER
   Location: U42-U44
   Removal: Removable when off
   Is Weak: No
   ```
   Click **Create Relationship**

3. Add PSU to Server:
   ```
   Parent ID: server-01
   Child ID: psu-01
   Type: CIM_COMPONENT
   Location: PSU Bay 1
   Removal: Removable when off
   Is Weak: Yes
   Custom Props: {"wattage": 750, "redundant": true}
   ```
   Click **Create Relationship**

4. Click **View Hierarchy Tree** to see:
   ```
   rack-01
   └── server-01 (U42-U44)
       └── psu-01 (PSU Bay 1)
   ```

### Query Topology

1. **Query** tab
2. Select template: "Device Connections"
3. Review generated query
4. Click **Execute Query**
5. View results in table

## Architecture

```
gui/
├── main_window.py           # Main application
├── discovery_tab.py         # Discovery configuration
├── topology_tab.py          # Network graph visualization
├── cim_relationships_tab.py # CIM hierarchy management
├── query_tab.py             # Cypher query interface
└── settings_dialog.py       # Configuration dialog
```

**Technology Stack**:
- **PySide6**: Qt6 Python bindings
- **QGraphicsView**: 2D graph rendering
- **Neo4j Driver**: Database connectivity
- **QThread**: Background tasks

## Keyboard Shortcuts

- **Ctrl+R**: Refresh current tab
- **Ctrl+Q**: Quit
- **Mouse Wheel**: Zoom (Topology tab)
- **Click+Drag**: Pan or move nodes

## Troubleshooting

### Cannot connect to Neo4j
1. Verify Neo4j is running: `systemctl status neo4j`
2. Check Settings → Neo4j connection parameters
3. Click "Test Connection" in Settings

### Discovery fails
1. Verify device credentials
2. Check network connectivity
3. Ensure PyATS is installed: `pip install pyats genie`

### Empty topology
1. Run discovery first (Discovery tab)
2. Click "Refresh Topology" button
3. Verify data exists:
   ```cypher
   MATCH (d:NetworkDevice) RETURN count(d)
   ```

### GUI won't start
1. Install dependencies: `pip install -r requirements-gui.txt`
2. Check Python version: `python --version` (3.8+ required)
3. Run directly: `python gui/main_window.py`

## Documentation

- **[GUI Guide](../docs/GUI_GUIDE.md)**: Complete user manual
- **[CIM Relationships](../docs/CIM_NESTING_RELATIONSHIPS.md)**: DMTF CIM documentation
- **[Main README](../README.md)**: NetMapper overview

## Screenshots

### Discovery Tab
Configure and run network discovery with real-time progress monitoring.

### Topology Tab
Interactive network graph with multiple layout algorithms and color-coded relationships.

### CIM Relationships Tab
Create and manage DMTF CIM hierarchies with physical and logical relationships.

### Query Tab
Execute Cypher queries with predefined templates or custom queries.

## Development

### Running from source
```bash
cd NetMapper
python -m gui.main_window
```

### Adding a new tab
```python
# 1. Create widget in gui/my_tab.py
from PySide6.QtWidgets import QWidget, QVBoxLayout

class MyTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # ... setup UI

    def refresh(self):
        # Refresh logic
        pass

    def update_neo4j_settings(self, uri, username, password):
        # Update connection settings
        pass

# 2. Register in main_window.py
self.my_tab = MyTab(self)
self.tabs.addTab(self.my_tab, "My Tab")
```

## License

Same as NetMapper core project.

## Support

- **Issues**: [GitHub Issues](https://github.com/ZeteticElench/NetMapper/issues)
- **Documentation**: `docs/GUI_GUIDE.md`
- **Examples**: See GUI Guide for complete workflows
