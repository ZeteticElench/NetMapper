## Infrahub Integration

NetMapper integrates with [Infrahub](https://github.com/opsmill/infrahub), the open-source Infrastructure Resource Manager, providing standardized data models and enabling seamless export of discovered network topology to Infrahub-compatible formats.

### Overview

Infrahub is a modern infrastructure management platform built on a graph database, similar to NetBox but with GraphQL API, real-time collaboration, and version control. NetMapper's Infrahub integration allows you to:

- **Export discovered topology** to Infrahub-compatible YAML/JSON
- **Map NetMapper models** to Infrahub's standardized schema
- **Align CIM relationships** with Infrahub's Component/Attribute semantics
- **Integrate with Infrahub's workflow** for infrastructure source of truth

### Architecture

```
NetMapper Discovery
        ↓
    Neo4j Graph
        ↓
  Infrahub Adapter
        ↓
Infrahub Models (Pydantic)
        ↓
  Export (YAML/JSON)
        ↓
Infrahub Import/API
```

### Infrahub Model Mapping

NetMapper maps its discovery data to Infrahub's base models from `models/base/`:

| NetMapper Model | Infrahub Model | Namespace | Description |
|----------------|----------------|-----------|-------------|
| `NetworkDevice` | `InfraDevice` | `Infra` | Network devices (routers, switches, firewalls) |
| `Interface` | `InfraInterface` | `Infra` | Network interfaces (physical/logical) |
| `VLANInfo` | `InfraVLAN` | `Infra` | VLAN configuration |
| `IPAddress` | `IpamIPAddress` | `Ipam` | IP address assignments |
| Custom | `LocationSite` | `Location` | Physical sites/locations |
| Custom | `LocationRack` | `Location` | Equipment racks |

### Infrahub Models Supported

#### 1. InfraDevice

**Source**: `models/base/dcim.yml` → `InfraDevice`

**Attributes**:
- `name` (unique): Device hostname
- `type`: Device type (router, switch, firewall, device)
- `status`: Operational status (active, provisioning, maintenance, drained)
- `role`: Network role (core, edge, spine, leaf, cpe, firewall)
- `platform`: Platform/OS (from NetMapper)
- `model`: Hardware model
- `serial_number`: Serial number
- `software_version`: OS version
- `primary_address`: Management IP

**Relationships**:
- `site` → `LocationSite`
- `interfaces` → `InfraInterface` (Component)
- `asn` → `InfraAutonomousSystem`
- `tags` → `BuiltinTag`

**Example**:
```yaml
devices:
  - name: core-router-01
    type: router
    status: active
    role: core
    platform: cisco_iosxe
    model: ISR4451
    serial_number: ABC123456
    software_version: 17.3.4
    primary_address: 10.0.0.1
    site: DefaultSite
```

#### 2. InfraInterface

**Source**: `models/base/dcim.yml` → `InfraInterface` (Generic)

**Attributes**:
- `name`: Interface name
- `description`: Interface description
- `speed`: Speed in Mbps
- `mtu`: MTU (default: 1500)
- `enabled`: Admin status
- `status`: Operational status (active, provisioning, maintenance, drained)
- `role`: Interface role (backbone, upstream, peering, server, loopback, management, uplink, etc.)

**Relationships**:
- `device` → `InfraDevice` (required)
- `ip_addresses` → List of IP addresses

**Example**:
```yaml
interfaces:
  - name: GigabitEthernet0/0
    device: core-router-01
    description: Uplink to Core
    speed: 1000
    mtu: 1500
    enabled: true
    status: active
    role: uplink
    ip_addresses:
      - 10.1.1.1/30
```

#### 3. InfraVLAN

**Source**: `models/base/ipam.yml` → `InfraVLAN`

**Attributes**:
- `name`: VLAN name (unique)
- `vlan_id`: VLAN ID (1-4094)
- `description`: VLAN description
- `status`: Status (active, provisioning, maintenance, drained)
- `role`: VLAN role (server, management, user)

**Relationships**:
- `site` → `LocationSite`
- `gateway` → `InfraInterfaceL3`

**Example**:
```yaml
vlans:
  - name: VLAN100_Servers
    vlan_id: 100
    description: Server VLAN
    status: active
    role: server
```

#### 4. IpamIPAddress

**Source**: `models/base/ipam.yml` → `IpamIPAddress`

**Attributes**:
- `address`: IP address with CIDR prefix (e.g., `192.168.1.1/24`)

**Relationships**:
- `interface` → `InfraInterfaceL3`

**Example**:
```yaml
ip_addresses:
  - address: 10.1.1.1/30
    interface: core-router-01:GigabitEthernet0/0
  - address: 192.168.1.1/24
    interface: access-switch-01:Vlan1
```

#### 5. LocationSite

**Source**: `models/base/location.yml` → `LocationSite`

**Attributes**:
- `name`: Site name (unique)
- `description`: Site description
- `city`: City location
- `address`: Physical address
- `contact`: Contact information

**Relationships**:
- `devices` → `InfraDevice` (Component)
- `vlans` → `InfraVLAN` (Component)
- `parent` → `LocationCountry`

**Example**:
```yaml
sites:
  - name: Datacenter-NYC
    description: New York City Datacenter
    city: New York
    address: 123 Main St, New York, NY 10001
    contact: ops@example.com
```

### Device Type Inference

NetMapper infers Infrahub device types from platform strings:

| NetMapper Platform | Infrahub Type |
|-------------------|---------------|
| `cisco_ios` | `router` |
| `cisco_iosxe` | `router` |
| `cisco_nxos` | `switch` |
| `cisco_iosxr` | `router` |
| `cisco_asa` | `firewall` |
| `juniper_junos` | `router` |
| `arista_eos` | `switch` |
| Contains "switch" | `switch` |
| Contains "router" | `router` |
| Contains "firewall"/"asa" | `firewall` |
| Default | `device` |

### Device Role Inference

Roles are inferred from hostname patterns:

| Hostname Pattern | Infrahub Role |
|-----------------|---------------|
| Contains "core" | `core` |
| Contains "edge" | `edge` |
| Contains "spine" | `spine` |
| Contains "leaf" | `leaf` |
| Contains "fw"/"firewall" | `firewall` |

### Interface Role Inference

| Interface Name Pattern | Infrahub Role |
|-----------------------|---------------|
| "loopback"/"lo" | `loopback` |
| "management"/"mgmt" | `management` |
| "uplink" | `uplink` |

### Infrahub-CIM Alignment

Infrahub's relationship kinds align well with DMTF CIM semantics:

| Infrahub Relationship | CIM Relationship | Semantics |
|----------------------|------------------|-----------|
| `kind: Component` | `CIM_COMPONENT` | Composition (integral parts) |
| `kind: Attribute` | `CIM_CONTAINER` | Aggregation (associations) |
| Hierarchical locations | `CIM_CONTAINER` | Physical containment |

**Example Alignment**:

```python
# Infrahub: Device -[Component]-> Interface
# Maps to: CIM_COMPONENT (interface is integral to device)

rel = CIMNestingRelationship(
    parent_id="router-01",
    child_id="router-01:GigabitEthernet0/0",
    relationship_type=CIMRelationshipType.COMPONENT,
    is_weak=True,  # Composition
    properties={"infrahub_kind": "Component"}
)

# Infrahub: Rack -[Attribute]-> Device
# Maps to: CIM_CONTAINER (device can be moved)

rel = CIMNestingRelationship(
    parent_id="rack-01",
    child_id="router-01",
    relationship_type=CIMRelationshipType.CONTAINER,
    location_within_container="U42-U44",
    is_weak=False,  # Aggregation
    properties={"infrahub_kind": "Attribute"}
)
```

## Usage

### CLI Tool

NetMapper provides a CLI tool to export topology to Infrahub format:

```bash
# Export to YAML
./netmapper-infrahub-export --format yaml --output topology.yml

# Export to JSON
./netmapper-infrahub-export --format json --output topology.json

# Export both formats
./netmapper-infrahub-export --format both --output-dir ./exports/

# With custom Neo4j connection
./netmapper-infrahub-export \
    --neo4j-uri bolt://neo4j-server:7687 \
    --neo4j-user admin \
    --neo4j-password secret123 \
    --format yaml \
    --output infrahub_topology.yml
```

### Python API

```python
from netmapper.infrahub_adapter import InfrahubAdapter

# Create adapter
adapter = InfrahubAdapter(
    "bolt://localhost:7687",
    "neo4j",
    "password"
)

# Convert topology
topology = adapter.convert_topology()

# Access converted models
print(f"Devices: {len(topology.devices)}")
print(f"Interfaces: {len(topology.interfaces)}")
print(f"VLANs: {len(topology.vlans)}")

# Export to YAML
adapter.export_to_yaml(topology, "infrahub_topology.yml")

# Export to JSON
adapter.export_to_json(topology, "infrahub_topology.json")

adapter.close()
```

### Example Script

```bash
python examples/infrahub_export_example.py
```

Output:
```
=== Conversion Summary ===
Devices:      15
Interfaces:   120
VLANs:        25
IP Addresses: 45
Sites:        1
Timestamp:    2024-11-23T10:30:00

Exported to: netmapper_infrahub_topology.yml
```

### Infrahub-CIM Bridge

Convert between Infrahub relationships and CIM:

```python
from netmapper.infrahub_cim_bridge import InfrahubCIMBridge

# Convert Infrahub Component to CIM_COMPONENT
cim_rel = InfrahubCIMBridge.infrahub_to_cim_relationship(
    parent_type="InfraDevice",
    child_type="InfraInterface",
    parent_id="router-01",
    child_id="router-01:GigabitEthernet0/0",
    location="GigabitEthernet0/0",
    infrahub_kind="Component"
)

print(f"CIM Type: {cim_rel.relationship_type}")
print(f"Is Composition: {cim_rel.is_weak}")
# Output:
# CIM Type: CIMRelationshipType.COMPONENT
# Is Composition: True

# Generate Infrahub YAML with CIM annotations
InfrahubCIMBridge.generate_infrahub_yaml_with_cim_annotations(
    relationships=[cim_rel],
    output_file="infrahub_with_cim.yml"
)
```

## Importing to Infrahub

Once exported, import data into Infrahub using:

### 1. GraphQL API

```graphql
mutation CreateDevice {
  InfraDeviceCreate(
    data: {
      name: { value: "core-router-01" }
      type: { value: "router" }
      status: { value: "active" }
      role: { value: "core" }
      platform: { value: "cisco_iosxe" }
      model: { value: "ISR4451" }
    }
  ) {
    object {
      id
      name { value }
    }
  }
}
```

### 2. Infrahub Python SDK

```python
from infrahub_sdk import InfrahubClient

client = InfrahubClient()

# Create device
device = await client.create(
    kind="InfraDevice",
    name="core-router-01",
    type="router",
    status="active",
    role="core"
)

# Create interface
interface = await client.create(
    kind="InfraInterface",
    name="GigabitEthernet0/0",
    device=device,
    status="active"
)
```

### 3. Bulk Import

Use Infrahub's bulk import utilities to load the exported YAML/JSON files.

## Example Workflows

### Workflow 1: Discovery → Export → Infrahub

```bash
# 1. Run NetMapper discovery
python -m netmapper.cli discover \
    --host router-01 \
    --ip 10.0.0.1 \
    --username admin \
    --password secret

# 2. Export to Infrahub format
./netmapper-infrahub-export \
    --format yaml \
    --output topology.yml

# 3. Import to Infrahub
infrahub-cli import topology.yml
```

### Workflow 2: Continuous Sync

```python
# scheduled_sync.py
from netmapper.infrahub_adapter import InfrahubAdapter
from infrahub_sdk import InfrahubClient

# Convert NetMapper data
adapter = InfrahubAdapter("bolt://localhost:7687", "neo4j", "password")
topology = adapter.convert_topology()
adapter.close()

# Sync to Infrahub
client = InfrahubClient()
for device in topology.devices:
    await client.upsert(
        kind="InfraDevice",
        name=device.name,
        **device.dict(exclude={"name"})
    )
```

## Benefits

### 1. Standardized Models
- Industry-standard Infrahub schema
- Consistent with NetBox and other IPAM tools
- GraphQL schema validation

### 2. Enhanced Collaboration
- Infrahub's real-time collaboration features
- Version control for infrastructure data
- Branch-based workflows

### 3. Integration Ecosystem
- Connect with Infrahub's integrations
- Leverage Infrahub's API and SDK
- Build on Infrahub's community resources

### 4. CIM Semantic Alignment
- Infrahub Component = CIM_COMPONENT
- Infrahub Attribute = CIM_CONTAINER
- Unified infrastructure modeling

## Reference

### Infrahub Resources
- **Repository**: https://github.com/opsmill/infrahub
- **Documentation**: https://docs.infrahub.app
- **Models**: https://github.com/opsmill/infrahub/tree/stable/models/
- **Schema**: https://schema.infrahub.app

### NetMapper Infrahub Files
- `netmapper/infrahub_models.py` - Pydantic models
- `netmapper/infrahub_adapter.py` - Conversion adapter
- `netmapper/infrahub_cim_bridge.py` - CIM alignment bridge
- `netmapper-infrahub-export` - CLI export tool
- `examples/infrahub_export_example.py` - Example script

## Troubleshooting

### Export Issues

**Problem**: Empty export file

**Solution**: Verify Neo4j has discovery data:
```cypher
MATCH (d:NetworkDevice) RETURN count(d)
```

**Problem**: Type errors during conversion

**Solution**: Check NetMapper platform strings match expected values

### Infrahub Import Issues

**Problem**: Schema validation errors

**Solution**: Ensure exported YAML matches Infrahub schema version. Check required fields are present.

**Problem**: Duplicate key errors

**Solution**: Use upsert operations instead of create. Ensure uniqueness constraints are met.

## Future Enhancements

- [ ] Direct Infrahub API integration (no export file needed)
- [ ] Bidirectional sync (Infrahub → NetMapper)
- [ ] Infrahub GraphQL query support in NetMapper GUI
- [ ] Real-time topology updates to Infrahub
- [ ] Support for Infrahub's Git workflow features
- [ ] Custom Infrahub schema extension mappings

## License

Same as NetMapper core project.
