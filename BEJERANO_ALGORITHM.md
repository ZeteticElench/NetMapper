# Bejerano Physical Topology Discovery Algorithm

## Overview

NetMapper implements the **Bejerano et al. 2003 Physical Topology Discovery Algorithm**, which discovers Layer 2 physical network topology using MAC address forwarding tables. This algorithm can identify switch-to-switch connections and even detect "uncooperative" network elements (hubs, unmanaged switches) that don't respond to SNMP or CLI commands.

**Reference:** Y. Bejerano, Y. Breitbart, M. Garofalakis, R. Rastogi, "Physical Topology Discovery for Large Multi-Subnet Networks," IEEE INFOCOM 2003, pp. 342-352.

## Key Features

- ✅ **Layer 2 Physical Topology**: Discovers actual switch-to-switch connections
- ✅ **Uncooperative Element Detection**: Identifies hubs and unmanaged switches
- ✅ **Dual Collection Methods**: Supports both SNMP and PyATS CLI parsing
- ✅ **Multi-VLAN Support**: Collects MAC tables across VLANs (Cisco)
- ✅ **Neo4j Integration**: Stores discovered topology in graph database

## How It Works

### Algorithm Overview

The Bejerano algorithm works by analyzing MAC address forwarding tables (AFTs) from network switches to infer physical connections:

1. **MAC Table Collection**: Gather MAC address forwarding tables from all switches
2. **Switch MAC Identification**: Extract each switch's own MAC address
3. **Connection Inference**: If switch A sees switch B's MAC on port P, then port P likely connects to switch B
4. **Bidirectional Verification**: Confirm connections by checking reverse port mappings
5. **Uncooperative Detection**: Identify inferred network elements (hubs) based on MAC distribution patterns

### Core Principle

**Key Insight**: When a switch forwards traffic, it learns the source MAC addresses of all devices reachable through each port. By examining which switch MACs appear on which ports, we can infer the physical topology without relying solely on CDP/LLDP.

### Advantages Over CDP/LLDP

| Feature | CDP/LLDP | Bejerano Algorithm |
|---------|----------|-------------------|
| Managed switches | ✅ Yes | ✅ Yes |
| Unmanaged switches | ❌ No | ✅ Yes (inferred) |
| Hubs | ❌ No | ✅ Yes (inferred) |
| Protocol required | ✅ Yes | ❌ No |
| Works with any vendor | ⚠️ Limited | ✅ Yes |

## Implementation in NetMapper

### MAC Address Collection Methods

NetMapper supports two methods for collecting MAC address forwarding tables:

#### 1. SNMP Bridge MIB (RFC 1493)

**How it works:**
- Queries `dot1dTpFdbTable` via SNMP
- Fast and efficient
- Requires SNMP access to switches
- For Cisco: Queries per-VLAN using community@vlan syntax

**Pros:**
- Faster than CLI parsing
- Less resource-intensive on switches
- Standard protocol (works across vendors)

**Cons:**
- Requires SNMP to be enabled
- May require per-VLAN community strings (Cisco)

**Configuration:**
```yaml
bejerano:
  enable: true
  mac_collection_method: "snmp"
  snmp_community: "public"
```

#### 2. PyATS CLI Parsing

**How it works:**
- Connects via SSH/Telnet (same as CDP/LLDP discovery)
- Executes `show mac address-table` commands
- Parses output using Genie parsers
- No additional protocols required

**Pros:**
- Works without SNMP
- Uses existing SSH connections
- Same credentials as PyATS discovery

**Cons:**
- Slower than SNMP
- More resource-intensive on switches
- Requires PyATS parser support for device OS

**Configuration:**
```yaml
bejerano:
  enable: true
  mac_collection_method: "pyats"
```

### Data Flow

```
┌─────────────────────┐
│  PyATS Discovery    │
│  (CDP/LLDP/STP)     │
└──────────┬──────────┘
           │ Discovers devices
           ▼
┌─────────────────────┐
│ MAC Table Collection│
│  (SNMP or PyATS)    │
└──────────┬──────────┘
           │ Collects forwarding tables
           ▼
┌─────────────────────┐
│ Bejerano Algorithm  │
│  (Topology Inference)│
└──────────┬──────────┘
           │ Infers connections
           ▼
┌─────────────────────┐
│   Neo4j Storage     │
│ (Graph Database)    │
└─────────────────────┘
```

## Usage

### Basic Usage

```bash
# Run hybrid discovery with default (SNMP) method
python -m netmapper.main_hybrid

# Use PyATS for MAC collection
# Edit config.yaml: mac_collection_method: "pyats"
python -m netmapper.main_hybrid

# Disable Bejerano discovery
python -m netmapper.main_hybrid --no-bejerano
```

### Configuration

```yaml
# config.yaml
bejerano:
  enable: true
  snmp_community: "public"
  mac_collection_method: "snmp"  # or "pyats"
```

### Python API

```python
from netmapper.models import DiscoveryConfig, DeviceCredentials
from netmapper.hybrid_discovery import HybridNetworkDiscovery

config = DiscoveryConfig(
    start_device=DeviceCredentials(
        hostname="core-sw01",
        ip="10.0.0.1",
        username="admin",
        password="cisco",
        os="ios"
    ),
    neo4j_uri="bolt://localhost:7687",
    neo4j_username="neo4j",
    neo4j_password="password",
    enable_bejerano=True,
    mac_collection_method="pyats",  # or "snmp"
)

discovery = HybridNetworkDiscovery(
    config=config,
    mac_collection_method="pyats",
)

try:
    discovery.run()
finally:
    discovery.close()
```

## Neo4j Schema Extensions

The Bejerano algorithm adds the following to the Neo4j schema:

### New Relationships

#### SNMP_PHYSICAL_LINK

Represents physical connections discovered via Bejerano algorithm:

```cypher
(NetworkDevice)-[:SNMP_PHYSICAL_LINK {
  port_a: int,
  port_b: int,
  link_type: "switch-switch",
  discovery_method: "bejerano"
}]->(NetworkDevice)
```

### New Nodes

#### UncooperativeElement

Represents inferred hubs or unmanaged switches:

```cypher
(:UncooperativeElement {
  element_id: string,
  discovered_by: "bejerano",
  element_type: "hub_or_unmanaged_switch"
})
```

## Neo4j Queries

### View Bejerano-Discovered Links

```cypher
MATCH (d1:NetworkDevice)-[r:SNMP_PHYSICAL_LINK]->(d2:NetworkDevice)
RETURN d1.hostname AS Device1,
       r.port_a AS Port1,
       r.port_b AS Port2,
       d2.hostname AS Device2,
       r.discovery_method AS Method
ORDER BY Device1, Port1
```

### Compare CDP vs Bejerano Topology

```cypher
// CDP links
MATCH (d1:NetworkDevice)-[:HAS]->(i1:Interface)-[:CDP_NEIGHBOR]->(i2:Interface)<-[:HAS]-(d2:NetworkDevice)
RETURN d1.hostname AS Device1, i1.name AS Interface1,
       d2.hostname AS Device2, i2.name AS Interface2,
       'CDP' AS Method

UNION

// Bejerano links
MATCH (d1:NetworkDevice)-[r:SNMP_PHYSICAL_LINK]->(d2:NetworkDevice)
RETURN d1.hostname AS Device1, toString(r.port_a) AS Interface1,
       d2.hostname AS Device2, toString(r.port_b) AS Interface2,
       'Bejerano' AS Method
```

### Find Uncooperative Elements

```cypher
MATCH (u:UncooperativeElement)
RETURN u.element_id AS Element,
       u.element_type AS Type,
       u.discovered_by AS DiscoveredBy
```

### Find Discrepancies

```cypher
// Find links discovered by Bejerano but not CDP
MATCH (d1)-[r:SNMP_PHYSICAL_LINK]-(d2)
WHERE NOT EXISTS {
  MATCH (d1)-[:HAS]->()-[:CDP_NEIGHBOR]->()<-[:HAS]-(d2)
}
RETURN d1.hostname, d2.hostname, 'Missing from CDP' AS Status
```

## Uncooperative Element Detection

The algorithm identifies uncooperative elements using heuristics:

### Detection Criteria

1. **High MAC Count**: Port shows significantly more MAC addresses than average (>3x)
2. **Not Known Switch**: Port doesn't connect to a known managed switch
3. **Shared Medium**: Multiple switches see the same large set of MACs

### Example Scenario

```
           [Hub/Unmanaged Switch]
                    |
        ┌───────────┼───────────┐
        |           |           |
    [Switch A]  [Switch B]  [Switch C]
```

In this case:
- Each switch sees many MACs on one port
- Those MACs include the other switches' MACs
- The algorithm infers a hub or unmanaged switch

## Performance Considerations

### SNMP Method

- **Speed**: ~1-2 seconds per device
- **Network Load**: Minimal (small SNMP packets)
- **Switch Load**: Low (SNMP queries cached)
- **Best for**: Large networks, production environments

### PyATS Method

- **Speed**: ~5-10 seconds per device
- **Network Load**: Higher (full SSH session)
- **Switch Load**: Medium (CLI command execution)
- **Best for**: Networks without SNMP, testing

### Scaling

| Devices | SNMP Time | PyATS Time |
|---------|-----------|------------|
| 10 | ~20 sec | ~100 sec |
| 50 | ~100 sec | ~500 sec |
| 100 | ~200 sec | ~1000 sec |

## Troubleshooting

### No MAC Tables Collected (SNMP)

**Problem**: SNMP queries return no data

**Solutions:**
- Verify SNMP is enabled: `show snmp community`
- Check community string in config.yaml
- For Cisco VLANs: Ensure community@vlan syntax works
- Test SNMP manually: `snmpwalk -v2c -c public 192.168.1.1 .1.3.6.1.2.1.17.4.3`

### No MAC Tables Collected (PyATS)

**Problem**: PyATS can't parse MAC tables

**Solutions:**
- Verify command: `show mac address-table`
- Check PyATS parser support for your platform
- Test manually via SSH
- Enable debug logging: `-v` flag

### No Switch Connections Found

**Problem**: Algorithm doesn't find any links

**Possible causes:**
- Switches don't have MAC tables populated (no traffic)
- MAC address aging too fast
- Switches use different MAC formats
- Send some traffic to populate MAC tables

### False Positive Uncooperative Elements

**Problem**: Algorithm incorrectly identifies hubs

**Solutions:**
- Adjust detection threshold in `bejerano_algorithm.py`
- Current heuristic: `count > avg * 3 and count > 10`
- Tune based on your network characteristics

## Comparison with Other Methods

### vs. CDP/LLDP

**Advantages:**
- Discovers unmanaged devices
- Works across vendors
- Independent verification

**Disadvantages:**
- Requires traffic for MAC learning
- Less accurate interface names
- More complex implementation

### vs. SNMP Polling Alone

**Advantages:**
- Infers uncooperative elements
- Validates learned connections
- Works with PyATS fallback

**Disadvantages:**
- More processing required
- Dependent on MAC table population

## Best Practices

1. **Use Both Methods**: Run CDP/LLDP AND Bejerano for complete view
2. **Choose Collection Method**: Use SNMP for speed, PyATS for compatibility
3. **Generate Traffic**: Ping between devices to populate MAC tables
4. **Regular Discovery**: Run periodically as MAC tables age out
5. **Verify Results**: Compare Bejerano links with CDP/LLDP for validation

## References

1. Y. Bejerano, Y. Breitbart, M. Garofalakis, R. Rastogi, "Physical Topology Discovery for Large Multi-Subnet Networks," IEEE INFOCOM 2003.
2. RFC 1493 - Definitions of Managed Objects for Bridges (Bridge MIB)
3. RFC 4188 - Definitions of Managed Objects for Bridges (Updated Bridge MIB)

## Implementation Files

- `netmapper/bejerano_algorithm.py` - Core algorithm implementation
- `netmapper/snmp_collector.py` - SNMP Bridge MIB collector
- `netmapper/pyats_mac_collector.py` - PyATS CLI-based collector
- `netmapper/hybrid_discovery.py` - Integration with PyATS discovery
- `netmapper/main_hybrid.py` - CLI entry point
