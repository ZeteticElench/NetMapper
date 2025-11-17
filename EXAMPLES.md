# NetMapper Usage Examples

## Example Neo4j Queries

### Basic Topology Queries

#### 1. List All Discovered Devices

```cypher
MATCH (d:NetworkDevice)
RETURN d.hostname AS Hostname,
       d.mgmt_ip AS ManagementIP,
       d.platform AS Platform,
       d.software_version AS Version
ORDER BY d.hostname
```

#### 2. Find All Physical Cable Connections

```cypher
MATCH (d1:NetworkDevice)-[:HAS_PORT]->(p1:Port)-[:CABLE_END_A]->(c:Cable)<-[:CABLE_END_B]-(p2:Port)<-[:HAS_PORT]-(d2:NetworkDevice)
RETURN d1.hostname AS Device1,
       p1.name AS Port1,
       c.id AS CableID,
       p2.name AS Port2,
       d2.hostname AS Device2
ORDER BY d1.hostname, p1.name
```

#### 3. View CDP Neighbor Topology

```cypher
MATCH (d1:NetworkDevice)-[:HAS]->(i1:Interface)-[:CDP_NEIGHBOR]->(i2:Interface)<-[:HAS]-(d2:NetworkDevice)
RETURN d1.hostname AS LocalDevice,
       i1.name AS LocalInterface,
       d2.hostname AS RemoteDevice,
       i2.name AS RemoteInterface
ORDER BY d1.hostname, i1.name
```

### STP Queries

#### 4. Find STP Root Bridges for All VLANs

```cypher
MATCH (d:NetworkDevice)-[:HAS_STP]->(s:STPInstance {is_root: true})
RETURN d.hostname AS RootBridge,
       s.vlan_id AS VLAN,
       s.bridge_address AS BridgeMAC,
       s.bridge_priority AS Priority
ORDER BY s.vlan_id
```

#### 5. Show STP Topology for Specific VLAN

```cypher
MATCH (d:NetworkDevice)-[:HAS_STP]->(s:STPInstance {vlan_id: 1})-[r:STP_INTERFACE]->(i:Interface)
RETURN d.hostname AS Device,
       i.name AS Interface,
       r.role AS Role,
       r.state AS State,
       r.cost AS Cost
ORDER BY d.hostname, i.name
```

#### 6. Find Blocked STP Ports

```cypher
MATCH (d:NetworkDevice)-[:HAS_STP]->(s:STPInstance)-[r:STP_INTERFACE {state: 'blocking'}]->(i:Interface)
RETURN d.hostname AS Device,
       s.vlan_id AS VLAN,
       i.name AS BlockedInterface,
       r.role AS Role
ORDER BY s.vlan_id, d.hostname
```

### VLAN Queries

#### 7. List VLANs by Device

```cypher
MATCH (d:NetworkDevice)-[:HAS_VLAN]->(v:VLAN)
RETURN d.hostname AS Device,
       v.vlan_id AS VLAN,
       v.name AS VLANName,
       v.status AS Status,
       size(v.ports) AS PortCount
ORDER BY d.hostname, v.vlan_id
```

#### 8. Find Devices with Specific VLAN

```cypher
MATCH (d:NetworkDevice)-[:HAS_VLAN]->(v:VLAN {vlan_id: 100})
RETURN d.hostname AS Device,
       v.name AS VLANName,
       v.ports AS Ports
ORDER BY d.hostname
```

### Interface Queries

#### 9. Find Interfaces with IP Addresses

```cypher
MATCH (d:NetworkDevice)-[:HAS]->(i:Interface)
WHERE i.ip_address IS NOT NULL
RETURN d.hostname AS Device,
       i.name AS Interface,
       i.ip_address AS IPAddress,
       i.subnet_mask AS SubnetMask,
       i.status AS Status
ORDER BY d.hostname, i.name
```

#### 10. Find Down Interfaces

```cypher
MATCH (d:NetworkDevice)-[:HAS_PORT]->(p:Port {status: 'down'})
RETURN d.hostname AS Device,
       p.name AS Port,
       p.description AS Description
ORDER BY d.hostname, p.name
```

### Path Finding

#### 11. Find Shortest Path Between Two Devices

```cypher
MATCH path = shortestPath(
  (d1:NetworkDevice {hostname: 'switch01'})-[:HAS|CDP_NEIGHBOR|HAS_PORT|CABLE_END_A|CABLE_END_B*]-(d2:NetworkDevice {hostname: 'switch05'})
)
RETURN path
```

#### 12. Find All Paths Between Two Devices

```cypher
MATCH path = (d1:NetworkDevice {hostname: 'switch01'})-[:HAS|CDP_NEIGHBOR*1..10]-(d2:NetworkDevice {hostname: 'switch05'})
RETURN path
LIMIT 10
```

### Network Analytics

#### 13. Count Devices by Platform

```cypher
MATCH (d:NetworkDevice)
RETURN d.platform AS Platform,
       count(d) AS DeviceCount
ORDER BY DeviceCount DESC
```

#### 14. Find Most Connected Devices

```cypher
MATCH (d:NetworkDevice)-[:HAS]->()-[:CDP_NEIGHBOR]->()
RETURN d.hostname AS Device,
       count(*) AS NeighborCount
ORDER BY NeighborCount DESC
LIMIT 10
```

#### 15. Find Devices with No Neighbors

```cypher
MATCH (d:NetworkDevice)
WHERE NOT (d)-[:HAS]->()-[:CDP_NEIGHBOR]->()
RETURN d.hostname AS Device,
       d.mgmt_ip AS ManagementIP,
       d.platform AS Platform
```

### Cable and Port Queries

#### 16. Find All Cables with Their Endpoints

```cypher
MATCH (c:Cable)<-[:CABLE_END_B]-(p2:Port)<-[:HAS_PORT]-(d2:NetworkDevice),
      (c)<-[:CABLE_END_A]-(p1:Port)<-[:HAS_PORT]-(d1:NetworkDevice)
RETURN c.id AS CableID,
       d1.hostname + ':' + p1.name AS EndpointA,
       d2.hostname + ':' + p2.name AS EndpointB,
       c.type AS CableType
ORDER BY c.id
```

#### 17. Find High-Speed Ports

```cypher
MATCH (d:NetworkDevice)-[:HAS_PORT]->(p:Port)
WHERE p.speed CONTAINS '10G' OR p.speed CONTAINS '40G' OR p.speed CONTAINS '100G'
RETURN d.hostname AS Device,
       p.name AS Port,
       p.speed AS Speed,
       p.status AS Status
ORDER BY p.speed DESC, d.hostname
```

### Visualization Queries

#### 18. Full Network Topology (use with caution on large networks)

```cypher
MATCH (d:NetworkDevice)-[r:HAS|HAS_PORT|CDP_NEIGHBOR|CABLE_END_A|CABLE_END_B*1..2]-(n)
RETURN d, r, n
LIMIT 100
```

#### 19. Single Device with All Connections

```cypher
MATCH (d:NetworkDevice {hostname: 'switch01'})-[r]-(n)
RETURN d, r, n
```

#### 20. STP Topology Visualization for VLAN

```cypher
MATCH (d:NetworkDevice)-[:HAS_STP]->(s:STPInstance {vlan_id: 1})-[r:STP_INTERFACE]->(i:Interface)
MATCH (d)-[:HAS]->(i)
RETURN d, s, r, i
```

## Python API Examples

### Example 1: Basic Discovery

```python
from netmapper.models import DiscoveryConfig, DeviceCredentials
from netmapper.discovery import NetworkDiscovery
import logging

logging.basicConfig(level=logging.INFO)

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
    discover_cdp=True,
    discover_lldp=True,
    discover_stp=True,
    discover_vlans=True
)

discovery = NetworkDiscovery(config)
try:
    discovery.run()
except Exception as e:
    print(f"Discovery failed: {e}")
finally:
    discovery.close()
```

### Example 2: Limited Depth Discovery

```python
from netmapper.models import DiscoveryConfig, DeviceCredentials
from netmapper.discovery import NetworkDiscovery

config = DiscoveryConfig(
    start_device=DeviceCredentials(
        hostname="edge-sw01",
        ip="10.1.0.1",
        username="netadmin",
        password="secret",
        enable_password="enable_secret",
        os="iosxe"
    ),
    neo4j_uri="bolt://localhost:7687",
    neo4j_username="neo4j",
    neo4j_password="password",
    max_depth=3,  # Only discover 3 hops
    connection_timeout=60,
    command_timeout=60
)

discovery = NetworkDiscovery(config)
try:
    discovery.run()
    print(f"Discovered {discovery.devices_discovered} devices")
    print(f"Failed: {discovery.devices_failed} devices")
finally:
    discovery.close()
```

### Example 3: CDP-Only Discovery

```python
config = DiscoveryConfig(
    start_device=DeviceCredentials(
        hostname="datacenter-core",
        ip="172.16.0.1",
        username="ops",
        password="ops123",
        os="nxos"
    ),
    neo4j_uri="bolt://localhost:7687",
    neo4j_username="neo4j",
    neo4j_password="password",
    discover_cdp=True,
    discover_lldp=False,  # Skip LLDP
    discover_stp=True,
    discover_vlans=True
)
```

### Example 4: Query Neo4j from Python

```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "password")
)

with driver.session() as session:
    # Get all devices
    result = session.run(
        "MATCH (d:NetworkDevice) "
        "RETURN d.hostname AS hostname, d.platform AS platform"
    )

    for record in result:
        print(f"{record['hostname']}: {record['platform']}")

    # Get CDP neighbors for a device
    result = session.run(
        "MATCH (d1:NetworkDevice {hostname: $hostname})-[:HAS]->(i1:Interface)"
        "-[:CDP_NEIGHBOR]->(i2:Interface)<-[:HAS]-(d2:NetworkDevice) "
        "RETURN d2.hostname AS neighbor",
        hostname="switch01"
    )

    neighbors = [record['neighbor'] for record in result]
    print(f"Neighbors: {neighbors}")

driver.close()
```

## Common Workflows

### Workflow 1: Initial Discovery

1. Configure `config.yaml` with seed device
2. Run: `python -m netmapper.main -v`
3. Review logs for any errors
4. Open Neo4j Browser and visualize

### Workflow 2: Update Topology

1. Re-run discovery (it will update existing devices)
2. New devices will be added
3. Changed data will be updated

### Workflow 3: Export Topology

```python
from neo4j import GraphDatabase
import json

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

with driver.session() as session:
    result = session.run(
        "MATCH (d1:NetworkDevice)-[:HAS]->()-[:CDP_NEIGHBOR]->()<-[:HAS]-(d2:NetworkDevice) "
        "RETURN d1.hostname AS device1, d2.hostname AS device2"
    )

    topology = [dict(record) for record in result]

    with open('topology.json', 'w') as f:
        json.dump(topology, f, indent=2)

driver.close()
```

### Workflow 4: Generate Reports

```python
from neo4j import GraphDatabase
import csv

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

with driver.session() as session:
    # Device inventory report
    result = session.run(
        "MATCH (d:NetworkDevice) "
        "RETURN d.hostname, d.platform, d.software_version, d.mgmt_ip "
        "ORDER BY d.hostname"
    )

    with open('device_inventory.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Hostname', 'Platform', 'Version', 'Management IP'])
        for record in result:
            writer.writerow([
                record['d.hostname'],
                record['d.platform'],
                record['d.software_version'],
                record['d.mgmt_ip']
            ])

driver.close()
```
