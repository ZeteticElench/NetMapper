# NetMapper Quick Start Guide

Get started with NetMapper in 5 minutes!

## Prerequisites

1. **Python 3.9+** installed
2. **Neo4j** database running
3. **Network access** to at least one Cisco device

## Step 1: Install Dependencies

```bash
cd NetMapper
pip install -r requirements.txt
```

## Step 2: Configure Neo4j

1. Start Neo4j:
```bash
# If using Docker
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/netmapper123 \
  neo4j:latest

# Or start your local Neo4j service
```

2. Verify Neo4j is running at http://localhost:7474

## Step 3: Create Configuration

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml`:

```yaml
start_device:
  hostname: "switch01"
  ip: "192.168.1.1"
  username: "admin"
  password: "cisco"
  os: "ios"

neo4j:
  uri: "bolt://localhost:7687"
  username: "neo4j"
  password: "netmapper123"

discovery:
  max_depth: null
  discover_cdp: true
  discover_lldp: true
  discover_stp: true
  discover_vlans: true
```

## Step 4: Run Discovery

```bash
python -m netmapper.main -v
```

## Step 5: Explore Your Network

Open Neo4j Browser at http://localhost:7474 and run:

```cypher
// View all devices
MATCH (d:NetworkDevice)
RETURN d

// View physical connections
MATCH (d1:NetworkDevice)-[:HAS_PORT]->(p1:Port)-[:CABLE_END_A]->(c:Cable)<-[:CABLE_END_B]-(p2:Port)<-[:HAS_PORT]-(d2:NetworkDevice)
RETURN d1, p1, c, p2, d2

// View CDP neighbor relationships
MATCH (d1:NetworkDevice)-[:HAS]->(i1:Interface)-[:CDP_NEIGHBOR]->(i2:Interface)<-[:HAS]-(d2:NetworkDevice)
RETURN d1, i1, i2, d2

// View STP root bridges
MATCH (d:NetworkDevice)-[:HAS_STP]->(s:STPInstance {is_root: true})
RETURN d.hostname AS device, s.vlan_id AS vlan, s.bridge_address
```

## Understanding the Output

NetMapper will output:

```
2025-11-17 10:30:00 - netmapper.discovery - INFO - Starting network discovery
2025-11-17 10:30:00 - netmapper.discovery - INFO - Found 0 existing devices in database
2025-11-17 10:30:00 - netmapper.discovery - INFO - Processing device switch01 (1)
2025-11-17 10:30:00 - netmapper.collector - INFO - Connecting to device switch01 (192.168.1.1)
2025-11-17 10:30:05 - netmapper.collector - INFO - Collecting device info from switch01
2025-11-17 10:30:10 - netmapper.collector - INFO - Collecting CDP neighbors from switch01
2025-11-17 10:30:15 - netmapper.discovery - INFO - Added CDP neighbor to queue: switch02
2025-11-17 10:30:15 - netmapper.discovery - INFO - Successfully discovered switch01
...
```

## What Gets Discovered

For each device, NetMapper collects:

- ✅ Device information (hostname, platform, version)
- ✅ Physical ports (status, speed, duplex)
- ✅ Logical interfaces (IP addresses)
- ✅ CDP neighbors with cable IDs
- ✅ LLDP neighbors
- ✅ VLAN configuration
- ✅ STP topology per VLAN

## Example Network Visualization

After discovery, you can visualize your network in Neo4j Browser:

1. Click "Database" icon (cylinder) in the left panel
2. Click on "NetworkDevice" node label
3. The graph will display all discovered devices
4. Click any device to see its connections

## Common Issues

### "Connection refused" to device
- Check IP address and network connectivity
- Verify SSH is enabled on device
- Test manually: `ssh admin@192.168.1.1`

### "Authentication failed"
- Verify username/password in config.yaml
- Check if enable password is required

### "Neo4j connection failed"
- Verify Neo4j is running: http://localhost:7474
- Check Neo4j credentials in config.yaml

### "No neighbors discovered"
- Enable CDP on devices: `cdp run`
- Enable LLDP on devices: `lldp run`
- Check that neighbors have management IPs

## Next Steps

- **Explore Data**: Use Cypher queries to analyze your network
- **Visualize**: Create custom visualizations in Neo4j Browser
- **Export**: Export data for documentation or other tools
- **Re-run**: Run discovery again to update topology changes
- **Customize**: Modify collection parameters in config.yaml

## Advanced Usage

### Limit Discovery Depth

```yaml
discovery:
  max_depth: 2  # Only discover 2 hops from start device
```

### Disable Specific Protocols

```yaml
discovery:
  discover_cdp: true
  discover_lldp: false  # Skip LLDP discovery
  discover_stp: true
  discover_vlans: true
```

### Different OS Types

```yaml
start_device:
  os: "iosxe"  # For Catalyst 9000 series
  # or "nxos" for Nexus
  # or "iosxr" for ASR/NCS
```

## Need Help?

- Check README.md for detailed documentation
- Enable verbose mode: `-v` flag
- Review logs for specific errors
- Verify device connectivity manually first
