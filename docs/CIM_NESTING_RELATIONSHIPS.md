# DMTF CIM-Based Nesting Relationships

## Overview

NetMapper now supports DMTF Common Information Model (CIM) based nesting relationships to model hierarchical infrastructure. This feature enables precise representation of physical containment, composition, and logical hierarchies in network infrastructure.

**CIM Schema Version:** 2.55.0
**Specification:** [DMTF CIM Schema](https://www.dmtf.org/standards/cim)

## Relationship Types

### 1. CIM_CONTAINER - Physical Containment

**Use Case:** For items that can be physically moved or relocated.

**CIM Mapping:** `CIM_Container`, `CIM_PackagedComponent`

**Examples:**
- Rack contains Server
- Chassis contains Blade Server
- Rack contains Network Switch
- Data Center contains Rack

**Characteristics:**
- Child can exist independently (Aggregation)
- `is_weak = False`
- Has `location_within_container` property
- Has `removal_conditions` property

**Example:**
```python
from netmapper.models import (
    CIMNestingRelationship,
    CIMRelationshipType,
    RemovalConditions
)

# Rack contains server at position U42
rack_server_rel = CIMNestingRelationship(
    parent_id="rack-01",
    child_id="server-01",
    relationship_type=CIMRelationshipType.CONTAINER,
    location_within_container="U42-U44",
    removal_conditions=RemovalConditions.REMOVABLE_WHEN_OFF,
    is_weak=False
)

manager.create_cim_nesting_relationship(rack_server_rel)
```

### 2. CIM_COMPONENT - Composition (Integral Subcomponents)

**Use Case:** For subcomponents that are integral parts, rarely moved independently.

**CIM Mapping:** `CIM_ConcreteComponent`, `CIM_SystemDevice` (with Composition qualifier)

**Examples:**
- Server has Power Supply Unit (PSU)
- Server has Network Interface Card (NIC)
- Switch has Line Card
- Switch has Supervisor Module
- Chassis has Fan Module

**Characteristics:**
- Child cannot exist independently (Composition)
- `is_weak = True`
- Has `location_within_container` property (slot/bay)
- Has `removal_conditions` property

**Example:**
```python
# Server contains PSU as integral component
server_psu_rel = CIMNestingRelationship(
    parent_id="server-01",
    child_id="psu-01",
    relationship_type=CIMRelationshipType.COMPONENT,
    location_within_container="PSU Bay 1",
    removal_conditions=RemovalConditions.REMOVABLE_WHEN_OFF,
    is_weak=True,  # PSU cannot exist without server
    properties={"wattage": 750, "redundant": True}
)

manager.create_cim_nesting_relationship(server_psu_rel)
```

### 3. CIM_MEMBER_OF_COLLECTION - Logical Hierarchy

**Use Case:** For logical groupings and collections.

**CIM Mapping:** `CIM_MemberOfCollection`

**Examples:**
- Device Group contains Switch
- VLAN contains Interfaces
- Routing Domain contains Routers
- High Availability Pair contains Devices
- Cluster contains Nodes

**Characteristics:**
- Logical relationship (not physical)
- `is_weak = False` (member can exist independently)
- No `location_within_container` or `removal_conditions`
- Can have custom properties for collection metadata

**Example:**
```python
# Add switch to core switches collection
collection_member_rel = CIMNestingRelationship(
    parent_id="collection-core-switches",
    child_id="switch-01",
    relationship_type=CIMRelationshipType.MEMBER_OF_COLLECTION,
    is_weak=False,
    properties={
        "role": "core",
        "redundancy_group": "1",
        "priority": "primary"
    }
)

manager.create_cim_nesting_relationship(collection_member_rel)
```

## CIM Properties

### RemovalConditions

Indicates whether a physical component can be removed and under what conditions.

**Values:**
- `Unknown` - Removal conditions are not known
- `Not Applicable` - Item is not removable
- `Removable when off` - Can be removed when powered off
- `Removable when on or off` - Hot-swappable

**CIM Mapping:** `CIM_PhysicalComponent.RemovalConditions`

### is_weak (Composition vs Aggregation)

Indicates whether the relationship is a composition or aggregation.

- `is_weak = True` - **Composition**: Child cannot exist without parent
  - Example: PSU in server, line card in switch
  - Strong lifecycle dependency

- `is_weak = False` - **Aggregation**: Child can exist independently
  - Example: Server in rack, switch in rack
  - Loose coupling

### location_within_container

Free-form string describing the position within the parent.

**Examples:**
- `"U42-U44"` - Rack units
- `"Slot 2"` - Chassis slot
- `"PSU Bay 1"` - Power supply bay
- `"Row A, Position 3"` - Data center position

**CIM Mapping:** `CIM_Container.LocationWithinContainer`

## API Reference

### Creating Relationships

#### Synchronous
```python
from netmapper.neo4j_manager import Neo4jManager

manager = Neo4jManager(uri, username, password)
manager.create_cim_nesting_relationship(relationship)
```

#### Asynchronous
```python
from netmapper.async_neo4j import AsyncNeo4jManager

manager = AsyncNeo4jManager(uri, username, password)
await manager.connect()
await manager.create_cim_nesting_relationship(relationship)
```

### Querying Relationships

#### Get All Children
```python
# Get all children regardless of relationship type
children = manager.get_cim_children("rack-01")

for child in children:
    print(f"Child: {child['id']}")
    print(f"Relationship: {child['relationship']}")
```

#### Filter by Relationship Type
```python
# Get only movable items (CONTAINER relationships)
movable = manager.get_cim_children(
    "rack-01",
    CIMRelationshipType.CONTAINER
)

# Get only integral components (COMPONENT relationships)
components = manager.get_cim_children(
    "server-01",
    CIMRelationshipType.COMPONENT
)

# Get only logical members (MEMBER_OF_COLLECTION)
members = manager.get_cim_children(
    "collection-core-switches",
    CIMRelationshipType.MEMBER_OF_COLLECTION
)
```

#### Get Complete Hierarchy
```python
# Get full hierarchy tree from root node
hierarchy = manager.get_cim_hierarchy("datacenter-01", max_depth=10)

# Returns nested dictionary structure:
# {
#   "id": "datacenter-01",
#   "children": {
#     "rack-01": {
#       "id": "rack-01",
#       "labels": ["Rack"],
#       "properties": {...},
#       "relationship": {...},
#       "children": {...}
#     }
#   }
# }
```

## Neo4j Cypher Queries

### Query by Relationship Type

```cypher
-- All CIM relationships
MATCH (parent)-[r]->(child)
WHERE r.relationship_type IS NOT NULL
RETURN parent, r, child

-- Physical containment only
MATCH (parent)-[r:CIM_CONTAINER]->(child)
RETURN parent, r, child

-- Integral components only
MATCH (parent)-[r:CIM_COMPONENT]->(child)
WHERE r.is_weak = true
RETURN parent, r, child

-- Logical collections only
MATCH (parent)-[r:CIM_MEMBER_OF_COLLECTION]->(child)
RETURN parent, r, child
```

### Find Removable Components

```cypher
-- Find all hot-swappable components
MATCH (parent)-[r]->(child)
WHERE r.removal_conditions = 'Removable when on or off'
RETURN parent.id, child.id, r.location_within_container
```

### Get Hierarchy Path

```cypher
-- Get path from datacenter to specific component
MATCH path = (dc {id: 'datacenter-01'})-[r*]->(component {id: 'psu-01'})
WHERE ALL(rel IN relationships(path) WHERE rel.relationship_type IS NOT NULL)
RETURN path
```

## Design Patterns

### Pattern 1: Data Center Infrastructure

```
Datacenter
├── [CIM_CONTAINER] Rack (movable, when off)
│   ├── [CIM_CONTAINER] Server (movable, when off)
│   │   ├── [CIM_COMPONENT] PSU (integral, when off)
│   │   ├── [CIM_COMPONENT] NIC (integral, hot-swap)
│   │   └── [CIM_COMPONENT] Disk (integral, hot-swap)
│   └── [CIM_CONTAINER] Switch (movable, when off)
│       ├── [CIM_COMPONENT] Line Card (integral, when off)
│       └── [CIM_COMPONENT] Supervisor (integral, when off)
└── [CIM_CONTAINER] Rack (movable, when off)
```

### Pattern 2: Modular Chassis

```
Chassis
├── [CIM_COMPONENT] Blade Server (Slot 1, when off)
│   ├── [CIM_COMPONENT] CPU (integral, not removable)
│   └── [CIM_COMPONENT] Memory (integral, when off)
├── [CIM_COMPONENT] Blade Server (Slot 2, when off)
├── [CIM_COMPONENT] Fan Module (hot-swap)
└── [CIM_COMPONENT] Power Module (hot-swap)
```

### Pattern 3: Logical Collections

```
Core-Switches Collection
├── [CIM_MEMBER_OF_COLLECTION] Switch-01
└── [CIM_MEMBER_OF_COLLECTION] Switch-02

HA-Pair Collection
├── [CIM_MEMBER_OF_COLLECTION] Firewall-01 (role: primary)
└── [CIM_MEMBER_OF_COLLECTION] Firewall-02 (role: secondary)
```

## Use Cases

### 1. Inventory Management

Track physical location and composition:
```python
# Find all servers in a specific rack
servers = manager.get_cim_children("rack-01", CIMRelationshipType.CONTAINER)

# Find all PSUs that need replacement
query = """
MATCH (server)-[r:CIM_COMPONENT]->(psu)
WHERE r.component_type = 'power_supply'
  AND psu.health_status = 'degraded'
RETURN server.id, psu.id, r.location_within_container
"""
```

### 2. Capacity Planning

Calculate rack capacity:
```python
# Get all items in rack and their U positions
rack_items = manager.get_cim_children("rack-01", CIMRelationshipType.CONTAINER)

# Calculate used rack units
used_units = sum(
    parse_rack_units(item['relationship']['location_within_container'])
    for item in rack_items
)
```

### 3. Impact Analysis

Find what depends on a component:
```cypher
-- What depends on this PSU?
MATCH path = (component {id: 'psu-01'})<-[r:CIM_COMPONENT*]-(parent)
RETURN path

-- What's in this rack if we need to power it down?
MATCH (rack {id: 'rack-01'})-[r:CIM_CONTAINER*]->(item)
RETURN item.id, labels(item)
```

### 4. Maintenance Planning

Identify hot-swappable vs. cold-swappable:
```python
# Find components that require downtime
components = manager.get_cim_children("server-01", CIMRelationshipType.COMPONENT)

for comp in components:
    removal = comp['relationship'].get('removal_conditions')
    if removal == RemovalConditions.REMOVABLE_WHEN_OFF.value:
        print(f"{comp['id']} requires downtime for maintenance")
```

## Best Practices

### 1. Choose the Right Relationship Type

- **Use CONTAINER** when the child can be physically relocated (server in rack)
- **Use COMPONENT** when the child is an integral part (PSU in server)
- **Use MEMBER_OF_COLLECTION** for logical groupings (HA pairs, clusters)

### 2. Set is_weak Correctly

- Set `is_weak=True` for composition (child dies with parent)
- Set `is_weak=False` for aggregation (child can exist independently)

### 3. Provide Location Information

Always include `location_within_container` for physical relationships:
```python
location_within_container="U42-U44"  # Good
location_within_container="Slot 2"   # Good
location_within_container="Unknown"  # Bad
```

### 4. Use Custom Properties

Extend relationships with domain-specific metadata:
```python
properties={
    "power_watts": 750,
    "redundant": True,
    "part_number": "ABC-123",
    "serial_number": "SN123456"
}
```

### 5. Model Hierarchies Correctly

Physical and logical hierarchies are separate:
```python
# Physical: Server in Rack
CIMRelationshipType.CONTAINER

# Logical: Server in Cluster
CIMRelationshipType.MEMBER_OF_COLLECTION

# Both can exist simultaneously!
```

## Migration from Existing Relationships

If you have existing custom containment relationships:

```python
# Old approach
query = "MATCH (rack)-[:CONTAINS]->(server) RETURN rack, server"

# New CIM approach
children = manager.get_cim_children("rack-01", CIMRelationshipType.CONTAINER)

# Migration script
old_rels = session.run("MATCH (p)-[:CONTAINS]->(c) RETURN p.id, c.id")
for record in old_rels:
    rel = CIMNestingRelationship(
        parent_id=record['p.id'],
        child_id=record['c.id'],
        relationship_type=CIMRelationshipType.CONTAINER,
        is_weak=False
    )
    manager.create_cim_nesting_relationship(rel)
```

## References

- [DMTF CIM Schema v2.55.0](https://www.dmtf.org/standards/cim)
- [CIM_Component Class](https://www.dmtf.org/sites/default/files/cim/cim_schema_v2550/CIM_Component.html)
- [CIM_Container Class](https://www.dmtf.org/sites/default/files/cim/cim_schema_v2550/CIM_Container.html)
- [CIM_MemberOfCollection Class](https://www.dmtf.org/sites/default/files/cim/cim_schema_v2550/CIM_MemberOfCollection.html)

## Example Scripts

See `examples/cim_nesting_example.py` for a complete working example demonstrating:
- Creating physical containment hierarchies
- Modeling integral components
- Defining logical collections
- Querying hierarchies

Run the example:
```bash
cd NetMapper
python examples/cim_nesting_example.py
```
